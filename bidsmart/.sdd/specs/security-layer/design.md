# Security Layer — Design Document

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        HTTP Request                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  AuditMiddleware │  ← async fire-and-forget
                    │  (audit.py)     │     enqueue → batch → DB
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  App / Routers  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐    │    ┌─────────▼─────────┐
     │ EncryptedStorage │    │    │ Desensitizing     │
     │ Backend          │    │    │ Formatter         │
     │ (encryption.py)  │    │    │ (desensitize.py)  │
     └────────┬────────┘    │    └───────────────────┘
              │              │
     ┌────────▼────────┐    │
     │  KeyManager      │    │
     │  (keys.py)       │    │
     │  KEK ← env var   │    │
     │  DEK ← urandom   │    │
     └────────┬────────┘    │
              │              │
     ┌────────▼────────┐    │
     │  StorageBackend  │    │
     │  (Local FS)      │    │
     └─────────────────┘    │
                            │
                   ┌────────▼────────┐
                   │ Log Output       │
                   │ (desensitized)   │
                   └─────────────────┘
```

## 1. Encryption Format (`encryption.py`)

### Data Flow

```
Plaintext
    │
    ├── GET CURRENT DEK ──► KeyManager.get_current_dek() → (dek, version)
    │
    ├── ENCRYPT ──► encrypt_bytes(dek, plaintext)
    │                │
    │                ├── os.urandom(12) → nonce
    │                └── AESGCM(key).encrypt(nonce, plaintext, None)
    │                    → nonce || ciphertext_with_tag
    │
    └── PACK ENVELOPE ──► struct.pack("B", version) + encrypted_blob
                          → [1B version][12B nonce][ciphertext][16B tag]
```

### Envelope Format (on-disk)

```
Byte 0:       key_version (uint8) — identifies which DEK version
Bytes 1–12:   nonce (12 random bytes)
Bytes 13–N-16: ciphertext
Bytes N-15–N: GCM authentication tag (16 bytes)
```

Total overhead: 29 bytes per file (1 version + 12 nonce + 16 tag).

### Why AES-256-GCM?

- **Authenticated encryption**: detects tampering (GCM tag verification fails on corruption)
- **No padding**: GCM is a stream cipher mode, no PKCS padding needed
- **Hardware acceleration**: AES-NI on modern CPUs
- **Industry standard**: NIST SP 800-38D, TLS 1.3, AWS KMS

### Low-Level Primitives

```python
def encrypt_bytes(key: bytes, plaintext: bytes) -> bytes:
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext  # 12B nonce + (plaintext_len + 16B tag)

def decrypt_bytes(key: bytes, encrypted: bytes) -> bytes:
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
```

## 2. Key Manager (`keys.py`)

### KEK/DEK Model

```
BIDSMART_KEK (env var)
    │
    ▼
┌─────────────────┐
│   KeyManager     │  ← thread-safe singleton
│                  │
│  _kek: bytes     │  ← loaded once at init
│  _keys: dict     │  ← {version: DEK}
│  _current: int   │  ← active version
│  _lock: Lock     │  ← threading.Lock
└─────────────────┘
    │
    ├── generate_dek() → (dek, v1)      [if no keys exist]
    ├── rotate()       → (dek, vN+1)    [new current]
    ├── get_current_dek() → (dek, v)    [for encrypt]
    └── get_dek(v)     → dek            [for decrypt old files]
```

### Thread Safety

All public methods acquire `self._lock` via `with self._lock:` context manager.
This ensures safe operation in async FastAPI environments where multiple
coroutines may access the KeyManager concurrently from different threads.

### KEK Bootstrapping

Priority:
1. Constructor `kek=` parameter (for testing)
2. `BIDSMART_KEK` environment variable
3. Development fallback: `b"bidsmart-dev-kek-32bytes-here!"`

Production deployments MUST set `BIDSMART_KEK` to a strong random value (at
least 32 bytes of entropy).

### Key Rotation

`rotate()` is an atomic operation:
1. Increment version counter
2. Generate new DEK via `os.urandom(32)`
3. Store in `_keys` map
4. Update `_current_version`

Old keys are NEVER deleted — they remain in `_keys` indefinitely so
historical files remain decryptable. A future `purge_old_versions()`
method could be added for key lifecycle management.

## 3. Audit Middleware (`audit.py`)

### Async Fire-and-Forget Pattern

```
HTTP Request
    │
    ▼
┌───────────────────────────────────────────────────┐
│ AuditMiddleware.__call__                            │
│                                                     │
│  1. Record start_time                               │
│  2. Wrap send() to capture status_code              │
│  3. Call inner app                                  │
│  4. In finally block:                               │
│     a. Build audit_record dict                      │
│     b. audit_queue.put_nowait(record)  ← fire!      │
│     c. audit_logger.info("AUDIT", extra={...})      │
│                                                     │
│  Response already sent to client by this point!     │
└───────────────────────────────────────────────────┘
                    │
                    │ (async, background)
                    ▼
┌───────────────────────────────────────────────────┐
│ _process_audit_queue()  [background asyncio.Task]  │
│                                                     │
│  while _running:                                    │
│    1. await queue.get() with 1s timeout             │
│    2. Drain up to 50 more with get_nowait()        │
│    3. _persist_batch(batch) → AuditLog INSERT      │
└───────────────────────────────────────────────────┘
```

### Why Fire-and-Forget?

- **Zero response latency impact**: audit persistence doesn't block the HTTP response
- **Batching**: groups up to 50 records into a single DB transaction
- **Graceful degradation**: if queue is full (1000 records), drops and logs warning
- **Fallback**: if no DB factory, logs only (still useful for structured logging)

### Audit Record Schema

Each record maps to the `audit_logs` table:

| Field         | Source                          | Example                          |
|---------------|---------------------------------|----------------------------------|
| `user_id`     | `request.state.user_id`         | `42`                             |
| `action`      | constant                        | `"http.request"`                 |
| `resource_type` | constant                      | `"http"`                         |
| `resource_id` | `f"{method}:{path}"`            | `"POST:/api/documents/upload"`   |
| `details`     | JSON with method/path/query/status/duration | `{"method":"POST",...}` |
| `ip_address`  | X-Forwarded-For or client.host  | `"10.0.1.42"`                    |
| `result`      | status-based                    | `"success"` (2xx-3xx) / `"failure"` (4xx-5xx) |

### Lifecycle

- **Start**: first HTTP request starts the background worker (`asyncio.create_task`)
- **Shutdown**: `shutdown()` sets `_running=False`, cancels the worker task, awaits cleanup

## 4. Log Desensitization (`desensitize.py`)

### Pattern Categories

| Category            | Example Pattern                        | Replacement            |
|---------------------|----------------------------------------|------------------------|
| Bearer tokens       | `Bearer eyJ...`                        | `Bearer [REDACTED]`    |
| JWT strings         | `eyJ... .eyJ... .…`                    | `[REDACTED_JWT]`       |
| API keys            | `sk-abc123...`                         | `[REDACTED_API_KEY]`   |
| Password JSON       | `"password": "secret"`                 | `"password": "[REDACTED]"` |
| Access tokens       | `'access_token': '...'`                | `'access_token': '[REDACTED]'` |
| Refresh tokens      | `"refresh_token": "..."`               | `"refresh_token": "***"` |
| Query params        | `?token=eyJ...`                        | `?token=[REDACTED]`    |
| GitHub tokens       | `ghp_abcdef...`                        | `[REDACTED_GITHUB_TOKEN]` |
| Generic secrets     | `secret=...` / `private_key=...`       | `[REDACTED_SECRET]`    |

### Two-Function API

```python
desensitize(text: str | None) -> str
    # Regex-based redaction for log lines and string values

desensitize_dict(data: dict | None) -> dict
    # Recursive: checks known-sensitive keys, applies desensitize() to string values
    # Handles nested dicts, lists, tuples
```

### Formatter Integration

```python
class DesensitizingFormatter(logging.Formatter):
    def format(self, record):
        record.msg = desensitize(str(record.msg))
        return super().format(record)
```

Configured in logging setup to automatically protect all log output.

## 5. P1 Skeletons

### Request Signing (`signing.py`)

`SignatureMiddleware` — pass-through ASGI middleware. TODO markers describe
the full HMAC-SHA256 implementation plan:
- Shared secret per API client
- Canonical request: `method + path + body + timestamp + nonce`
- Header: `X-Signature: t=..., v1=...`
- Anti-replay: timestamp window (±5 min) + nonce cache
- Per-route configurability

### HTTPS Enforcement (`https.py`)

`HTTPSRedirectMiddleware` — pass-through ASGI middleware. TODO markers describe
the full implementation:
- Detect `scope["scheme"] == "http"`
- 301/308 redirect to HTTPS URL
- HSTS header on HTTPS responses
- Configurable exempt paths

## Technology Decisions

| Decision                | Rationale                                              |
|-------------------------|--------------------------------------------------------|
| `cryptography` library  | Industry-standard, well-audited, GCM support           |
| `struct.pack("B")`      | Minimal overhead (1 byte for version) vs JSON          |
| `asyncio.Queue`         | Native async, no external dependency for audit queue   |
| `threading.Lock`        | KeyManager accessed from async; lock is lightweight    |
| Regex desensitization   | Zero-dependency, fast, covers 95% of log leak cases    |
| P1 skeletons as pass-through | Enables incremental delivery without breaking app |

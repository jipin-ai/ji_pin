# Security Layer — Requirements (EARS Format)

## FR-1: File Encryption at Rest

**As a** platform operator
**When** any file is stored via the `StorageBackend`
**The system shall** encrypt it with AES-256-GCM before writing to disk,
using the `EncryptedStorageBackend` wrapper that prepends an envelope
format: `[1B key_version][12B nonce][ciphertext + 16B GCM tag]`.

**Acceptance criteria:**
- Files on disk are never in plaintext form
- Decryption on `get()` returns original plaintext byte-for-byte
- Wrong/missing DEK version raises `KeyError`
- Corrupted ciphertext raises a cryptography exception

## FR-2: KEK/DEK Hierarchical Key Management

**As a** security administrator
**When** the application starts
**The system shall** load the Key Encryption Key (KEK) from the `BIDSMART_KEK`
environment variable (with dev fallback), and generate Data Encryption Keys
(DEKs) via `os.urandom(32)` stored in a versioned key map.

**Acceptance criteria:**
- KEK loaded from env var, padded/truncated to 32 bytes if needed
- DEK generation produces cryptographically random 256-bit keys
- All DEK versions retained for backward compatibility
- `KeyManager` is thread-safe (`threading.Lock`)
- `get_current_dek()` raises `RuntimeError` if no DEK generated

## FR-3: Key Rotation

**As a** security administrator
**When** a key rotation is triggered
**The system shall** generate a new DEK, increment the version counter,
and make the new DEK the current key while retaining all previous versions
for decryption of existing files.

**Acceptance criteria:**
- `rotate()` generates a new 32-byte DEK with incremented version
- Old DEKs remain accessible via `get_dek(version)`
- New files are encrypted with the new current DEK
- Old files decrypt correctly with their versioned DEK
- Rotation is thread-safe

## FR-4: Request Audit Logging (Async Non-Blocking)

**As a** compliance officer
**When** any HTTP request is processed by the platform
**The system shall** record an audit event asynchronously (fire-and-forget)
containing: user_id, action (`http.request`), resource (`method:path`),
status code, duration, client IP, and result (success/failure).

**Acceptance criteria:**
- Audit events do not delay HTTP response (fire-and-forget via `asyncio.Queue`)
- Records batched (up to 50) and persisted to `audit_logs` table asynchronously
- Queue overflow (1000 records) logs warning and drops excess
- Audit logger emits structured log with `extra` dict
- Client IP respects `X-Forwarded-For` header
- `shutdown()` gracefully drains and cancels the background worker
- Falls back to log-only if no DB session factory is provided

## FR-5: Sensitive Data Desensitization in Logs

**As a** security engineer
**When** log output is produced
**The system shall** redact sensitive data including Bearer tokens, JWT strings,
API keys, passwords, access/refresh tokens, and GitHub tokens via regex-based
pattern matching.

**Acceptance criteria:**
- `desensitize(str)` replaces sensitive patterns with `[REDACTED]` markers
- Handles: Bearer tokens, `sk-*` keys, JWT strings, password JSON fields,
  `access_token`/`refresh_token` dict keys, query params, GitHub tokens
- `desensitize_dict(dict)` recursively redacts known sensitive keys and values
- `DesensitizingFormatter` wraps standard logging.Formatter for automatic redaction
- Null/None input handled gracefully
- Non-string input coerced to string before processing

## FR-6: P1 — Request Signing (Skeleton)

**As a** future API consumer
**When** HMAC-SHA256 signing is implemented
**The system will** validate X-Signature headers with canonical request format,
timestamp window (±5 min), and nonce cache for anti-replay.

**Status:** Skeleton — pass-through middleware only.

## FR-7: P1 — HTTPS Enforcement (Skeleton)

**As a** security administrator
**When** HTTPS enforcement is implemented
**The system will** redirect HTTP to HTTPS (301/308), add HSTS headers, and
support configurable exempt paths.

**Status:** Skeleton — pass-through middleware only.

## Non-Functional Requirements

| ID    | Description                              | Target          |
|-------|------------------------------------------|-----------------|
| NFR-1 | Encryption overhead                      | < 5ms per MB    |
| NFR-2 | Audit latency impact on response         | < 1ms (async)   |
| NFR-3 | Audit queue persistence                  | Batch ≤ 50 recs |
| NFR-4 | Key rotation without downtime            | Yes (atomic)    |
| NFR-5 | Desensitization regex overhead           | < 1ms per call  |

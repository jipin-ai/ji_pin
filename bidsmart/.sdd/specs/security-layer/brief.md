# Security Layer — Feature Brief

## Problem Statement

BidSmart handles sensitive enterprise procurement data — bid documents, financial
analysis, contract terms, and corporate communications. Without a security layer,
the platform is vulnerable to:

1. **Data exposure** — files stored on disk as plaintext are readable by anyone 
   with filesystem access (host compromise, backup leaks, insider threat).
2. **Secrets leakage** — API keys, JWT tokens, and passwords appearing in log 
   output create a secondary attack surface for credential theft.
3. **No audit trail** — without request-level audit logging, security incidents 
   cannot be investigated retroactively. Who accessed what, when, and from where?
4. **Key mismanagement** — a single hard-coded encryption key is a single point 
   of failure. Compromise requires re-encrypting all data, with no migration path.

These risks are unacceptable for an enterprise platform storing competitive
procurement data, where confidentiality is a contractual and regulatory
requirement.

## Solution

The Security Layer module provides defense-in-depth protection:

| Capability                 | Implementation              | Code Location |
|----------------------------|-----------------------------|---------------|
| File encryption at rest    | AES-256-GCM via `EncryptedStorageBackend` | `src/security/encryption.py` |
| Key management             | KEK/DEK hierarchical model, versioned keys | `src/security/keys.py` |
| Request audit logging      | Async fire-and-forget `AuditMiddleware` | `src/security/audit.py` |
| Log desensitization        | Regex-based redaction of secrets, tokens, PII | `src/security/desensitize.py` |
| Request signing            | HMAC-SHA256 skeleton (P1)   | `src/security/signing.py` |
| HTTPS enforcement          | Redirect skeleton (P1)      | `src/security/https.py` |

### How It Works

- **Encryption**: All files pass through `EncryptedStorageBackend`, which wraps
  the underlying `StorageBackend`. On `save()`, plaintext is encrypted with
  AES-256-GCM using the current Data Encryption Key (DEK). On `get()`, the
  envelope header identifies which DEK version was used, and the file is
  decrypted transparently. Callers see only plaintext — encryption is invisible.

- **Key Management**: A `KeyManager` singleton loads a Key Encryption Key (KEK)
  from the `BIDSMART_KEK` environment variable. DEKs are generated via
  `os.urandom(32)` and stored in a versioned map. Rotation generates a new DEK
  while retaining old versions for backward compatibility.

- **Audit**: The `AuditMiddleware` (ASGI middleware) records every HTTP request
  — method, path, user, IP, status code, duration — using a fire-and-forget
  pattern. Records are enqueued and persisted in batches by a background worker,
  ensuring zero impact on response latency.

- **Desensitization**: A `DesensitizingFormatter` (Python logging Formatter)
  automatically redacts Bearer tokens, API keys, JWT strings, passwords, and
  other sensitive patterns from all log output. A companion `desensitize_dict()`
  function handles structured logging payloads.

## Scope

**In scope**: File encryption, key management, audit logging, log desensitization.

**P1 (skeleton only)**: Request signing (`signing.py`), HTTPS enforcement (`https.py`).

## Status

All core capabilities (encryption, keys, audit, desensitization) are fully
implemented. Request signing and HTTPS enforcement are P1 skeletons with TODO
markers.

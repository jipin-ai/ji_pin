"""Security package for BidSmart platform.

Components:
- KeyManager: KEK from env, DEK generation, versioned key store
- EncryptedStorageBackend: AES-256-GCM encrypt/decrypt decorator
- AuditMiddleware: async, non-blocking audit logging
- Desensitization: strip keys, tokens, document content from logs
- API signing middleware: HMAC-SHA256 request signing (P1 skeleton)
- HTTPS enforcement: redirect HTTP→HTTPS (P1 skeleton)
"""

from src.security.keys import KeyManager
from src.security.encryption import EncryptedStorageBackend, encrypt_bytes, decrypt_bytes
from src.security.audit import AuditMiddleware
from src.security.desensitize import desensitize, desensitize_dict
from src.security.signing import SignatureMiddleware
from src.security.https import HTTPSRedirectMiddleware

__all__ = [
    "KeyManager",
    "EncryptedStorageBackend",
    "encrypt_bytes",
    "decrypt_bytes",
    "AuditMiddleware",
    "desensitize",
    "desensitize_dict",
    "SignatureMiddleware",
    "HTTPSRedirectMiddleware",
]

"""EncryptedStorageBackend — AES-256-GCM encrypt/decrypt decorator.

Wraps an existing StorageBackend so that all files stored on disk are encrypted
transparently. Callers interact with plaintext — encryption and decryption
happen inside save() and get().

Format on disk (envelope):
    [1 byte: key_version] [12 bytes: nonce] [ciphertext + 16-byte GCM tag]
"""

import os
import struct
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.security.keys import KeyManager
from src.storage.base import StorageBackend

# ── Low-level AES-256-GCM primitives ────────────────────────────────────────

def encrypt_bytes(key: bytes, plaintext: bytes) -> bytes:
    """Encrypt plaintext with AES-256-GCM.

    Args:
        key: 32-byte AES-256 key.
        plaintext: Data to encrypt.

    Returns:
        [12-byte nonce] + [ciphertext] + [16-byte GCM tag]
    """
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt_bytes(key: bytes, encrypted: bytes) -> bytes:
    """Decrypt data produced by encrypt_bytes.

    Args:
        key: 32-byte AES-256 key.
        encrypted: [12-byte nonce] + [ciphertext] + [16-byte GCM tag]

    Returns:
        Original plaintext.

    Raises:
        Exception: If decryption fails (wrong key, corrupted data, etc.).
    """
    nonce = encrypted[:12]
    ciphertext = encrypted[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


# ── Envelope packing ────────────────────────────────────────────────────────

def _pack_envelope(key_version: int, encrypted_blob: bytes) -> bytes:
    """Pack key version + encrypted blob into the envelope format."""
    return struct.pack("B", key_version) + encrypted_blob


def _unpack_envelope(envelope: bytes) -> tuple[int, bytes]:
    """Unpack key version and encrypted blob from the envelope format."""
    version = envelope[0]
    encrypted_blob = envelope[1:]
    return version, encrypted_blob


# ── Encrypted Storage Backend ───────────────────────────────────────────────

class EncryptedStorageBackend(StorageBackend):
    """AES-256-GCM encrypted storage backend.

    Wraps an inner StorageBackend (e.g., LocalFileStorage) and transparently
    encrypts data on save() / decrypts data on get().

    The encryption envelope prepended to each file contains:
        - 1 byte: key version (uint8) — identifies which DEK was used
        - 12 bytes: nonce (random)
        - remainder: AES-256-GCM ciphertext with 16-byte authentication tag
    """

    def __init__(self, key_manager: KeyManager, inner: StorageBackend) -> None:
        """Initialize the encrypted storage backend.

        Args:
            key_manager: KeyManager that provides current DEK and versioned DEKs.
            inner: The underlying StorageBackend to delegate to.
        """
        self._km = key_manager
        self._inner = inner

    # ── Public API ──────────────────────────────────────────────────────────

    async def save(self, project_id: str, content: bytes, extension: str = "") -> str:
        """Encrypt *content* and persist via the inner storage backend.

        Returns:
            Relative path from storage root.
        """
        dek, version = self._km.get_current_dek()
        encrypted_blob = encrypt_bytes(dek, content)
        envelope = _pack_envelope(version, encrypted_blob)
        return await self._inner.save(project_id, envelope, extension)

    async def get(self, path: str) -> bytes:
        """Retrieve and decrypt file content.

        Raises:
            FileNotFoundError: If the path does not exist.
            KeyError: If the DEK version used for encryption is no longer available.
        """
        envelope = await self._inner.get(path)
        version, encrypted_blob = _unpack_envelope(envelope)
        dek = self._km.get_dek(version)
        return decrypt_bytes(dek, encrypted_blob)

    async def delete(self, path: str) -> None:
        """Delete the encrypted file from storage."""
        await self._inner.delete(path)

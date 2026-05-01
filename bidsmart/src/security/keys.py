"""KeyManager — Key Encryption Key (KEK) from env, DEK generation, versioned key store.

KEK is loaded from the BIDSMART_KEK environment variable. Each Data Encryption
Key (DEK) is generated via os.urandom(32) for AES-256. All DEKs are stored in a
versioned key map, with the current DEK tracked separately.

Rotation generates a new DEK and increments the version. Old DEKs are kept so
files encrypted with previous versions can still be decrypted.
"""

import os
import threading
from typing import Optional, Tuple

# Default fallback KEK for development — production MUST set BIDSMART_KEK env var.
_DEV_KEK = b"bidsmart-dev-kek-32bytes-here!"  # 32 bytes for AES-256


class KeyManager:
    """Manages encryption keys for the BidSmart platform.

    - KEK (Key Encryption Key) loaded from env var ``BIDSMART_KEK``.
    - DEKs (Data Encryption Keys) are 256-bit keys for AES-256-GCM.
    - Versioned key store maps version numbers to DEKs.
    - Thread-safe for use in async contexts.
    """

    def __init__(self, kek: Optional[bytes] = None) -> None:
        """Initialize the KeyManager.

        Args:
            kek: Explicit 32-byte Key Encryption Key. If None, loads from
                 ``BIDSMART_KEK`` env var, with a dev fallback.
        """
        if kek is not None:
            self._kek = kek
        else:
            env_kek = os.environ.get("BIDSMART_KEK")
            if env_kek:
                self._kek = env_kek.encode("utf-8")
                # Pad or truncate to 32 bytes
                if len(self._kek) < 32:
                    self._kek = self._kek.ljust(32, b"\x00")
                else:
                    self._kek = self._kek[:32]
            else:
                self._kek = _DEV_KEK

        self._lock = threading.Lock()
        self._keys: dict[int, bytes] = {}  # version → DEK
        self._current_version: int = 0

    # ── Public API ──────────────────────────────────────────────────────────

    def generate_dek(self) -> Tuple[bytes, int]:
        """Generate a new DEK and return (key_bytes, version_number).

        If no keys exist yet, this becomes the current key at version 1.
        If keys already exist, this appends a new version but does NOT
        make it current (use rotate() for that).

        Returns:
            Tuple of (32-byte DEK, version number).
        """
        with self._lock:
            new_version = max(self._keys.keys(), default=0) + 1
            new_dek = os.urandom(32)
            self._keys[new_version] = new_dek
            if self._current_version == 0:
                self._current_version = new_version
            return new_dek, new_version

    def rotate(self) -> Tuple[bytes, int]:
        """Generate a new DEK and make it the current key.

        Returns:
            Tuple of (32-byte DEK, version number).
        """
        with self._lock:
            new_version = max(self._keys.keys(), default=0) + 1
            new_dek = os.urandom(32)
            self._keys[new_version] = new_dek
            self._current_version = new_version
            return new_dek, new_version

    def get_current_dek(self) -> Tuple[bytes, int]:
        """Return the current (DEK, version).

        Raises:
            RuntimeError: If no DEK has been generated yet.
        """
        with self._lock:
            if self._current_version == 0:
                raise RuntimeError("No DEK has been generated. Call generate_dek() first.")
            return self._keys[self._current_version], self._current_version

    def get_dek(self, version: int) -> bytes:
        """Return the DEK for a specific version.

        Args:
            version: Key version number.

        Returns:
            32-byte DEK.

        Raises:
            KeyError: If the version does not exist.
        """
        with self._lock:
            if version not in self._keys:
                raise KeyError(f"DEK version {version} not found")
            return self._keys[version]

    @property
    def current_version(self) -> int:
        """Return the current active key version."""
        return self._current_version

    @property
    def kek(self) -> bytes:
        """Return the Key Encryption Key (32 bytes)."""
        return self._kek

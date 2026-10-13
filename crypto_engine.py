"""Cryptographic Engine for Secure File Protection.

Implements AES-256-GCM authenticated encryption and scrypt key derivation.
Ensures cryptographically secure random salts and nonces, deterministic
per-block IV uniqueness, and strict authentication verification.
"""

import os
import struct
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.exceptions import InvalidTag

# Constants
KEY_SIZE = 32          # 256 bits for AES-256
SALT_SIZE = 16         # 128-bit cryptographically secure random salt
NONCE_SIZE = 12        # 96-bit standard AES-GCM nonce
TAG_SIZE = 16          # 128-bit authentication tag
SCRYPT_N = 16384       # CPU/memory cost parameter (NIST recommendation)
SCRYPT_R = 8           # Block size parameter
SCRYPT_P = 1           # Parallelization parameter


class AuthenticationError(Exception):
    """Raised when authenticated decryption or integrity verification fails."""
    pass


class CryptoEngine:
    """Provides authenticated encryption and key derivation services."""

    @staticmethod
    def generate_salt() -> bytes:
        """Generate a cryptographically secure random 16-byte salt."""
        return os.urandom(SALT_SIZE)

    @staticmethod
    def generate_nonce() -> bytes:
        """Generate a cryptographically secure random 12-byte master nonce."""
        return os.urandom(NONCE_SIZE)

    @staticmethod
    def derive_key(passphrase: str, salt: bytes) -> bytes:
        """
        Derive a 256-bit symmetric encryption key from a passphrase and salt using scrypt.
        
        Args:
            passphrase: User-supplied passphrase string.
            salt: 16-byte cryptographically secure salt.
            
        Returns:
            32-byte derived AES-256 key.
        """
        if not passphrase:
            raise ValueError("Passphrase cannot be empty.")
        if len(salt) != SALT_SIZE:
            raise ValueError(f"Salt must be exactly {SALT_SIZE} bytes.")

        kdf = Scrypt(
            salt=salt,
            length=KEY_SIZE,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
        )
        return kdf.derive(passphrase.encode("utf-8"))

    @staticmethod
    def derive_block_nonce(master_nonce: bytes, block_index: int) -> bytes:
        """
        Deterministically construct a unique 12-byte nonce for a specific block.
        Combines the 12-byte master nonce with a 4-byte block index counter.
        Guarantees that no two blocks ever reuse the same IV under the same key.
        
        Args:
            master_nonce: 12-byte file master nonce.
            block_index: 0-indexed integer block number.
            
        Returns:
            12-byte block nonce.
        """
        if len(master_nonce) != NONCE_SIZE:
            raise ValueError(f"Master nonce must be {NONCE_SIZE} bytes.")
        
        # Take the first 8 bytes of the master nonce and XOR / append 4-byte counter
        prefix = master_nonce[:8]
        counter = struct.pack(">I", block_index)
        suffix = bytes(a ^ b for a, b in zip(master_nonce[8:12], counter))
        return prefix + suffix

    @staticmethod
    def encrypt_block(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> Tuple[bytes, bytes]:
        """
        Encrypt a block of plaintext using AES-256-GCM.
        
        Args:
            key: 32-byte AES-256 key.
            nonce: 12-byte unique nonce.
            plaintext: Raw data bytes to encrypt.
            aad: Associated authenticated data (authenticated but not encrypted).
            
        Returns:
            Tuple of (ciphertext, 16-byte authentication tag).
        """
        if len(key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes.")
        if len(nonce) != NONCE_SIZE:
            raise ValueError(f"Nonce must be {NONCE_SIZE} bytes.")

        aesgcm = AESGCM(key)
        # AESGCM.encrypt appends 16-byte tag to the ciphertext
        encrypted = aesgcm.encrypt(nonce, plaintext, aad)
        ciphertext = encrypted[:-TAG_SIZE]
        tag = encrypted[-TAG_SIZE:]
        return ciphertext, tag

    @staticmethod
    def decrypt_block(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes, aad: bytes = b"") -> bytes:
        """
        Authenticate and decrypt a block of ciphertext using AES-256-GCM.
        
        Args:
            key: 32-byte AES-256 key.
            nonce: 12-byte unique nonce.
            ciphertext: Encrypted data bytes.
            tag: 16-byte authentication tag.
            aad: Associated authenticated data.
            
        Returns:
            Decrypted raw plaintext bytes.
            
        Raises:
            AuthenticationError: If tag verification fails or data is corrupted/tampered.
        """
        if len(key) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes.")
        if len(nonce) != NONCE_SIZE:
            raise ValueError(f"Nonce must be {NONCE_SIZE} bytes.")
        if len(tag) != TAG_SIZE:
            raise AuthenticationError(f"Authentication tag must be {TAG_SIZE} bytes.")

        aesgcm = AESGCM(key)
        combined = ciphertext + tag
        try:
            plaintext = aesgcm.decrypt(nonce, combined, aad)
            return plaintext
        except InvalidTag as exc:
            raise AuthenticationError("AES-GCM authentication verification failed: invalid tag or data corrupted.") from exc

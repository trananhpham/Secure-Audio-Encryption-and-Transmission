import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

class KeyDerivation:
    @staticmethod
    def derive_keys(master_key: bytes, session_salt: bytes) -> tuple[bytes, bytes]:
        """
        Derives session encryption key and manifest HMAC key from master key.
        Returns: (encryption_key, hmac_key)
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64, # 32 bytes for encryption, 32 bytes for HMAC
            salt=session_salt,
            info=b"secure-audio-segment-transfer-v1"
        )
        derived = hkdf.derive(master_key)
        encryption_key = derived[:32]
        hmac_key = derived[32:]
        return encryption_key, hmac_key

    @staticmethod
    def generate_salt() -> bytes:
        """Generates a 16-byte random salt."""
        return os.urandom(16)

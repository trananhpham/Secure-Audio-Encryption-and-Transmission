import os
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from src.exceptions import DecryptionError, SegmentIntegrityError, WrongKeyError
from src.protocol.models import SegmentMetadata

class AEADEncryptor:
    @staticmethod
    def construct_aad(metadata_dict: dict) -> bytes:
        """
        Constructs Additional Authenticated Data (AAD) from important metadata fields.
        Must match sender and receiver exactly.
        """
        # Important fields to bind to ciphertext
        aad_fields = {
            "audio_id": metadata_dict.get("audio_id"),
            "session_id": metadata_dict.get("session_id"),
            "segment_id": metadata_dict.get("segment_id"),
            "sequence_number": metadata_dict.get("sequence_number"),
            "total_segments": metadata_dict.get("total_segments"),
            "duration": metadata_dict.get("duration"),
            "format": metadata_dict.get("format"),
            "original_filename": metadata_dict.get("original_filename"),
            "plaintext_size": metadata_dict.get("plaintext_size")
        }
        # Use canonical JSON to ensure consistent byte representation
        from src.utils.canonical_json import to_canonical_json
        return to_canonical_json(aad_fields)

    @staticmethod
    def encrypt(key: bytes, plaintext: bytes, metadata_dict: dict) -> tuple[bytes, bytes]:
        """
        Encrypts plaintext using AES-256-GCM.
        Returns: (ciphertext, nonce)
        """
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        aad = AEADEncryptor.construct_aad(metadata_dict)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
        return ciphertext, nonce

    @staticmethod
    def decrypt(key: bytes, nonce: bytes, ciphertext: bytes, metadata_dict: dict) -> bytes:
        """
        Decrypts ciphertext using AES-256-GCM.
        Raises DecryptionError on failure.
        """
        try:
            aesgcm = AESGCM(key)
            aad = AEADEncryptor.construct_aad(metadata_dict)
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
            return plaintext
        except Exception as e:
            # Differentiate between tampered data and completely wrong key if possible,
            # but cryptography's InvalidTag is generic for both.
            # We raise SegmentIntegrityError which covers both tampering and AAD mismatch
            raise SegmentIntegrityError(f"AES-GCM authentication failed: {str(e)}")

import hmac
import hashlib
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature
from src.exceptions import ManifestAuthenticationError
from src.utils.canonical_json import to_canonical_json

class ManifestAuth:
    @staticmethod
    def calculate_hmac(key: bytes, manifest_dict: dict) -> bytes:
        """Calculates HMAC-SHA256 of the manifest data."""
        data = manifest_dict.copy()
        if "manifest_hmac" in data:
            del data["manifest_hmac"]
        if "manifest_signature" in data:
            del data["manifest_signature"]
        
        canonical_bytes = to_canonical_json(data)
        h = hmac.new(key, canonical_bytes, hashlib.sha256)
        return h.digest()

    @staticmethod
    def verify_hmac(key: bytes, manifest_dict: dict, expected_hmac: bytes) -> None:
        """Verifies the HMAC-SHA256 of the manifest."""
        calculated = ManifestAuth.calculate_hmac(key, manifest_dict)
        if not hmac.compare_digest(calculated, expected_hmac):
            raise ManifestAuthenticationError("Manifest HMAC verification failed. It may have been tampered with.")

    @staticmethod
    def sign_ecdsa(private_key, manifest_dict: dict) -> bytes:
        """Signs the manifest data using ECDSA Private Key."""
        data = manifest_dict.copy()
        if "manifest_hmac" in data:
            del data["manifest_hmac"]
        if "manifest_signature" in data:
            del data["manifest_signature"]
            
        canonical_bytes = to_canonical_json(data)
        signature = private_key.sign(
            canonical_bytes,
            ec.ECDSA(hashes.SHA256())
        )
        return signature

    @staticmethod
    def verify_ecdsa(public_key, manifest_dict: dict, expected_signature: bytes) -> None:
        """Verifies the ECDSA signature of the manifest."""
        data = manifest_dict.copy()
        if "manifest_hmac" in data:
            del data["manifest_hmac"]
        if "manifest_signature" in data:
            del data["manifest_signature"]
            
        canonical_bytes = to_canonical_json(data)
        try:
            public_key.verify(
                expected_signature,
                canonical_bytes,
                ec.ECDSA(hashes.SHA256())
            )
        except InvalidSignature:
            raise ManifestAuthenticationError("Manifest ECDSA signature verification failed. It may have been forged.")

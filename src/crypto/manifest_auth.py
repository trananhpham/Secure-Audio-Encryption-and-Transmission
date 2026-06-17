import hmac
import hashlib
from src.exceptions import ManifestAuthenticationError
from src.utils.canonical_json import to_canonical_json

class ManifestAuth:
    @staticmethod
    def calculate_hmac(key: bytes, manifest_dict: dict) -> bytes:
        """Calculates HMAC-SHA256 of the manifest data (excluding the manifest_hmac field itself)."""
        # Create a copy to avoid modifying original
        data = manifest_dict.copy()
        if "manifest_hmac" in data:
            del data["manifest_hmac"]
        
        canonical_bytes = to_canonical_json(data)
        h = hmac.new(key, canonical_bytes, hashlib.sha256)
        return h.digest()

    @staticmethod
    def verify_hmac(key: bytes, manifest_dict: dict, expected_hmac: bytes) -> None:
        """Verifies the HMAC-SHA256 of the manifest."""
        calculated = ManifestAuth.calculate_hmac(key, manifest_dict)
        if not hmac.compare_digest(calculated, expected_hmac):
            raise ManifestAuthenticationError("Manifest HMAC verification failed. It may have been tampered with.")

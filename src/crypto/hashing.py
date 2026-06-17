import hashlib
from pathlib import Path

class Hashing:
    @staticmethod
    def hash_data(data: bytes) -> str:
        """Calculates SHA-256 hash of bytes and returns hex string."""
        hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def hash_file(filepath: Path) -> str:
        """Calculates SHA-256 hash of a file and returns hex string."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

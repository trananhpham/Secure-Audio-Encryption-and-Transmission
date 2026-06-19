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

    @staticmethod
    def calculate_entropy(data: bytes) -> float:
        """Calculates Shannon entropy of data bytes."""
        if not data:
            return 0.0
        import math
        entropy = 0
        length = len(data)
        counts = [0] * 256
        for byte in data:
            counts[byte] += 1
        for count in counts:
            if count > 0:
                p_x = float(count) / length
                entropy -= p_x * math.log(p_x, 2)
        return entropy

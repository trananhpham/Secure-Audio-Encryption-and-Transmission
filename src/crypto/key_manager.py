import os
from pathlib import Path
from src.exceptions import SecureAudioError

class KeyManager:
    def __init__(self, key_path: Path = Path("secrets/master.key")):
        self.key_path = key_path

    def generate_master_key(self) -> None:
        """Generates a random 32-byte master key and saves it to secrets/master.key."""
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        key = os.urandom(32)
        with open(self.key_path, "wb") as f:
            f.write(key)
        # Set permissions if possible
        try:
            os.chmod(self.key_path, 0o600)
        except Exception:
            pass

    def get_master_key(self) -> bytes:
        """Reads and returns the master key."""
        if not self.key_path.exists():
            raise SecureAudioError(f"Master key not found at {self.key_path}")
        with open(self.key_path, "rb") as f:
            key = f.read()
            if len(key) != 32:
                raise SecureAudioError("Invalid master key length. Expected 32 bytes.")
            return key

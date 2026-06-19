import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
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

    def generate_ecdsa_keypair(self, private_path: Path, public_path: Path) -> None:
        """Generates an ECDSA SECP256R1 keypair."""
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()
        
        private_path.parent.mkdir(parents=True, exist_ok=True)
        with open(private_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        with open(public_path, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

    def get_ecdsa_private_key(self, private_path: Path):
        """Loads ECDSA private key."""
        if not private_path.exists():
            raise SecureAudioError(f"ECDSA private key not found at {private_path}")
        with open(private_path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    def get_ecdsa_public_key(self, public_path: Path):
        """Loads ECDSA public key."""
        if not public_path.exists():
            raise SecureAudioError(f"ECDSA public key not found at {public_path}")
        with open(public_path, "rb") as f:
            return serialization.load_pem_public_key(f.read())

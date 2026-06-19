import json
from pathlib import Path
from src.protocol.models import Manifest
from src.crypto.manifest_auth import ManifestAuth
from src.utils.canonical_json import to_canonical_json
from src.exceptions import InvalidManifestError
from src.utils.file_utils import atomic_write

import base64

class ManifestManager:
    @staticmethod
    def create_manifest(manifest: Manifest, hmac_key: bytes, output_path: Path, ecdsa_private_key=None) -> None:
        """Calculates HMAC and optionally ECDSA signature, then writes manifest to file."""
        manifest_dict = manifest.model_dump()
        hmac_digest = ManifestAuth.calculate_hmac(hmac_key, manifest_dict)
        manifest.manifest_hmac = hmac_digest.hex()
        
        if ecdsa_private_key:
            manifest_dict = manifest.model_dump()
            sig = ManifestAuth.sign_ecdsa(ecdsa_private_key, manifest_dict)
            manifest.manifest_signature = base64.b64encode(sig).decode('utf-8')
        
        final_dict = manifest.model_dump()
        canonical_bytes = to_canonical_json(final_dict)
        
        atomic_write(output_path, canonical_bytes)

    @staticmethod
    def load_manifest(filepath: Path) -> Manifest:
        """Loads and parses manifest from file."""
        if not filepath.exists():
            raise InvalidManifestError(f"Manifest not found: {filepath}")
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Manifest(**data)
        except json.JSONDecodeError as e:
            raise InvalidManifestError(f"Manifest JSON is invalid: {str(e)}")
        except Exception as e:
            # Catch validation errors from Pydantic
            raise InvalidManifestError(f"Manifest schema validation failed: {str(e)}")

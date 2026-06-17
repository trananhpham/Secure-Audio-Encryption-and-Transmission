import uuid
import os
from pathlib import Path
from datetime import datetime, timezone
import base64

from src.utils.logger import logger
from src.audio.input_loader import InputLoader
from src.audio.metadata import AudioMetadata
from src.audio.assembler import AudioAssembler
from src.crypto.key_manager import KeyManager
from src.crypto.key_derivation import KeyDerivation
from src.crypto.hashing import Hashing
from src.crypto.aead import AEADEncryptor
from src.protocol.models import Manifest, SegmentMetadata
from src.protocol.manifest import ManifestManager
from src.transport.local_transport import LocalTransport
from src.exceptions import SecureAudioError

class Sender:
    def __init__(self, input_dir: Path, output_base: Path, format: str, sender_id: str, receiver_id: str):
        self.input_dir = input_dir
        self.output_base = output_base
        self.format = format.lower()
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        
        # Output directories
        self.ref_dir = self.output_base / "reference"
        self.sender_dir = self.output_base / "sender"
        self.channel_base = self.output_base / "channel"
        
        self.ref_dir.mkdir(parents=True, exist_ok=True)
        self.sender_dir.mkdir(parents=True, exist_ok=True)

    def process_and_send(self) -> str:
        """Executes the sender process (22 steps) and returns the channel path."""
        try:
            logger.log_event("TRANSFER_CREATED", f"Sender: {self.sender_id}, Receiver: {self.receiver_id}")
            
            # 1-4. Validate input directory and format
            input_paths = InputLoader.load_and_validate(self.input_dir, self.format)
            logger.log_event("INPUT_FILES_VALIDATED", f"Found 5 valid {self.format} files.")

            # 5-6. Read metadata and assign sequence number
            segments_info = []
            total_duration = 0.0
            for i, filepath in enumerate(input_paths):
                seq = i + 1
                info = AudioMetadata.get_info(filepath)
                total_duration += info["duration"]
                segments_info.append({
                    "path": filepath,
                    "sequence_number": seq,
                    "duration": info["duration"],
                    "plaintext_size": filepath.stat().st_size
                })
            logger.log_event("SEGMENT_METADATA_READ")

            # 7-8. Assemble reference file and calculate hash
            logger.log_event("REFERENCE_ASSEMBLY_STARTED")
            ref_filename = f"original_reference.{self.format}"
            ref_path = self.ref_dir / ref_filename
            AudioAssembler.assemble(input_paths, ref_path, self.format)
            original_file_hash = Hashing.hash_file(ref_path)
            logger.log_event("REFERENCE_ASSEMBLY_COMPLETED", f"Hash: {original_file_hash}")

            # 9-11. IDs and Salt
            audio_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())
            session_salt = KeyDerivation.generate_salt()
            
            # 12. Key derivation
            key_mgr = KeyManager()
            master_key = key_mgr.get_master_key()
            enc_key, hmac_key = KeyDerivation.derive_keys(master_key, session_salt)

            # Process segments
            segments = []
            expected_order = []
            encrypted_files = []
            
            sender_session_dir = self.sender_dir / session_id
            sender_session_dir.mkdir(parents=True, exist_ok=True)

            for info in segments_info:
                filepath = info["path"]
                # 13-14. Segment ID and Nonce
                segment_id = str(uuid.uuid4())
                
                # Setup metadata dict for AAD
                aad_dict = {
                    "audio_id": audio_id,
                    "session_id": session_id,
                    "segment_id": segment_id,
                    "sequence_number": info["sequence_number"],
                    "total_segments": 5,
                    "duration": info["duration"],
                    "format": self.format,
                    "original_filename": filepath.name,
                    "plaintext_size": info["plaintext_size"]
                }
                
                # 15. Read and Encrypt
                with open(filepath, "rb") as f:
                    plaintext = f.read()
                
                # 16. Plaintext Hash
                pt_hash = Hashing.hash_data(plaintext)
                
                ciphertext, nonce = AEADEncryptor.encrypt(enc_key, plaintext, aad_dict)
                
                # 17. Ciphertext Hash
                ct_hash = Hashing.hash_data(ciphertext)
                
                # Write ciphertext to temp sender dir using Steganography
                enc_filename = f"{filepath.stem}_stego.wav"
                enc_path = sender_session_dir / enc_filename
                from src.crypto.steganography import Steganography
                Steganography.embed_data_eof(ciphertext, enc_path)
                
                encrypted_files.append(enc_path)
                expected_order.append(filepath.name)
                
                # 18. Create SegmentMetadata
                seg_meta = SegmentMetadata(
                    audio_id=audio_id,
                    session_id=session_id,
                    segment_id=segment_id,
                    sequence_number=info["sequence_number"],
                    total_segments=5,
                    duration=info["duration"],
                    format=self.format,
                    original_filename=filepath.name,
                    encrypted_filename=enc_filename,
                    nonce=base64.b64encode(nonce).decode('utf-8'),
                    plaintext_size=info["plaintext_size"],
                    ciphertext_size=len(ciphertext),
                    plaintext_hash=pt_hash,
                    ciphertext_hash=ct_hash
                )
                segments.append(seg_meta)
                logger.log_event("SEGMENT_ENCRYPTED", f"Segment {info['sequence_number']}")

            # 19-20. Create Manifest and calculate HMAC
            manifest = Manifest(
                audio_id=audio_id,
                session_id=session_id,
                sender_id=self.sender_id,
                receiver_id=self.receiver_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                format=self.format,
                total_segments=5,
                total_duration=total_duration,
                original_reference_filename=ref_filename,
                original_file_hash=original_file_hash,
                session_salt=base64.b64encode(session_salt).decode('utf-8'),
                expected_order=expected_order,
                segments=segments
            )
            
            private_key_path = Path("secrets/sender_private.pem")
            public_key_path = Path("secrets/sender_public.pem")
            if not private_key_path.exists() or not public_key_path.exists():
                key_mgr.generate_ecdsa_keypair(private_key_path, public_key_path)
            private_key = key_mgr.get_ecdsa_private_key(private_key_path)
            
            manifest_path = sender_session_dir / "manifest.json"
            ManifestManager.create_manifest(manifest, hmac_key, manifest_path, ecdsa_private_key=private_key)
            logger.log_event("MANIFEST_CREATED")
            
            # 21. Simulate sending to channel
            channel_dir = self.channel_base / audio_id
            LocalTransport.send(encrypted_files, manifest_path, channel_dir)
            
            # 22. Log
            logger.log_event("TRANSFER_COMPLETED", f"Session: {session_id}, Channel: {channel_dir}")
            
            # Clean up temp sender dir
            for f in sender_session_dir.iterdir():
                f.unlink()
            sender_session_dir.rmdir()
            
            return str(channel_dir)

        except Exception as e:
            logger.log_event("TRANSFER_FAILED", str(e))
            raise

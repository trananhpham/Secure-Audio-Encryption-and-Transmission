import os
import base64
from pathlib import Path

from src.utils.logger import logger
from src.protocol.manifest import ManifestManager
from src.protocol.validator import ProtocolValidator
from src.protocol.replay_guard import ReplayGuard
from src.crypto.key_manager import KeyManager
from src.crypto.key_derivation import KeyDerivation
from src.crypto.manifest_auth import ManifestAuth
from src.crypto.aead import AEADEncryptor
from src.crypto.hashing import Hashing
from src.audio.assembler import AudioAssembler
from src.exceptions import FinalHashMismatchError, SecureAudioError, FormatMismatchError, SegmentOrderError, SegmentIntegrityError

class Receiver:
    def __init__(self, channel_dir: Path, output_base: Path):
        self.channel_dir = channel_dir
        self.output_base = output_base
        
        self.receiver_dir = self.output_base / "receiver"
        self.temp_dir = self.output_base / "temp"
        
        self.receiver_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def receive_and_process(self) -> str:
        """Executes the receiver process (23 steps) and returns the reconstructed file path."""
        try:
            logger.log_event("RECEIVE_STARTED", f"Channel: {self.channel_dir}")
            
            # 1-2. Read manifest and check schema
            manifest_path = self.channel_dir / "manifest.json"
            manifest = ManifestManager.load_manifest(manifest_path)
            
            # 13. Derive session key (moved up to check HMAC)
            key_mgr = KeyManager()
            master_key = key_mgr.get_master_key()
            session_salt = base64.b64decode(manifest.session_salt)
            enc_key, hmac_key = KeyDerivation.derive_keys(master_key, session_salt)

            # 3. Verify HMAC manifest
            expected_hmac = bytes.fromhex(manifest.manifest_hmac)
            manifest_dict = manifest.model_dump()
            ManifestAuth.verify_hmac(hmac_key, manifest_dict, expected_hmac)
            
            # 3.1 Verify ECDSA signature
            if manifest.manifest_signature:
                public_key = key_mgr.get_ecdsa_public_key(Path("secrets/sender_public.pem"))
                expected_sig = base64.b64decode(manifest.manifest_signature)
                ManifestAuth.verify_ecdsa(public_key, manifest_dict, expected_sig)
                
            logger.log_event("MANIFEST_VERIFIED")

            # 4-5. Validate total segments and expected order
            ProtocolValidator.validate_manifest(manifest)

            # 6-10. Check files, detect missing, extra, duplicate, order
            ordered_segment_paths = ProtocolValidator.validate_received_segments(manifest, self.channel_dir)
            
            # 12. Check Replay
            replay_guard = ReplayGuard()
            
            # Setup temp session directory
            session_temp_dir = self.temp_dir / manifest.session_id
            session_temp_dir.mkdir(parents=True, exist_ok=True)
            
            decrypted_files = []
            
            # Validate order: Ensure that we are processing in the expected order
            # The ordered_segment_paths are already ordered by sequence_number based on manifest.
            
            for i, seg in enumerate(sorted(manifest.segments, key=lambda x: x.sequence_number)):
                filepath = ordered_segment_paths[i]
                
                # Check replay per segment
                replay_guard.check_and_record_segment(
                    manifest.audio_id,
                    manifest.session_id,
                    seg.segment_id,
                    seg.sequence_number
                )
                
                # Extract ciphertext from Stego cover
                from src.crypto.steganography import Steganography
                ciphertext = Steganography.extract_data_eof(filepath)
                
                # 11. Check ciphertext hash
                ct_hash = Hashing.hash_data(ciphertext)
                if ct_hash != seg.ciphertext_hash:
                    raise SegmentIntegrityError(f"Ciphertext hash mismatch for {seg.encrypted_filename}")
                
                # 14. Decrypt segment
                nonce = base64.b64decode(seg.nonce)
                aad_dict = {
                    "audio_id": seg.audio_id,
                    "session_id": seg.session_id,
                    "segment_id": seg.segment_id,
                    "sequence_number": seg.sequence_number,
                    "total_segments": seg.total_segments,
                    "duration": seg.duration,
                    "format": seg.format,
                    "original_filename": seg.original_filename,
                    "plaintext_size": seg.plaintext_size
                }
                
                plaintext = AEADEncryptor.decrypt(enc_key, nonce, ciphertext, aad_dict)
                logger.log_event("SEGMENT_DECRYPTED", seg.encrypted_filename)
                
                # 15. Check plaintext hash
                pt_hash = Hashing.hash_data(plaintext)
                if pt_hash != seg.plaintext_hash:
                    raise SecureAudioError(f"Plaintext hash mismatch for {seg.encrypted_filename}")
                
                # 16. Check original filename
                if filepath.name != seg.encrypted_filename:
                    raise SecureAudioError(f"Filename mismatch for {seg.encrypted_filename}")
                
                # Save temporarily
                pt_filepath = session_temp_dir / seg.original_filename
                with open(pt_filepath, "wb") as f:
                    f.write(plaintext)
                
                decrypted_files.append(pt_filepath)
                logger.log_event("SEGMENT_RECEIVED", seg.encrypted_filename)

            # 17. Ensure sorted by sequence number
            # We already processed them in sequence_number order due to `sorted(manifest.segments)`

            # 18. Assemble according to order at1 -> at5
            logger.log_event("ASSEMBLY_STARTED")
            reconstructed_filename = f"reconstructed.{manifest.format}"
            reconstructed_path = self.receiver_dir / reconstructed_filename
            
            AudioAssembler.assemble(decrypted_files, reconstructed_path, manifest.format)
            
            # 19-20. Check resulted audio and compute SHA-256
            final_hash = Hashing.hash_file(reconstructed_path)
            
            # 21. Compare with original_file_hash
            if final_hash != manifest.original_file_hash:
                logger.log_security("HASH_MISMATCH", f"Expected {manifest.original_file_hash}, got {final_hash}")
                # We do not create a complete reconstructed file if invalid, but the assembler already wrote it.
                # The requirements state "Không tạo file reconstructed hoàn chỉnh nếu có bất kỳ đoạn nào không hợp lệ"
                # If the hash doesn't match, it means something went wrong despite GCM passing.
                # Delete the reconstructed file.
                try:
                    reconstructed_path.unlink()
                except:
                    pass
                raise FinalHashMismatchError(f"Final hash mismatch! Expected {manifest.original_file_hash}, got {final_hash}")
                
            logger.log_event("FINAL_HASH_VERIFIED", "HASH MATCH: PASS")
            
            # Mark session complete
            replay_guard.mark_session_completed(manifest.session_id, manifest.audio_id)
            
            # 23. Cleanup temporary plaintext files
            for f in session_temp_dir.iterdir():
                f.unlink()
            session_temp_dir.rmdir()
            
            return str(reconstructed_path)

        except Exception as e:
            logger.log_event("TRANSFER_FAILED", str(e))
            raise

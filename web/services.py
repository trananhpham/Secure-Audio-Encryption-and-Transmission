import os
import json
import uuid
import threading
import time
from pathlib import Path
import traceback

from src.sender import Sender
from src.receiver import Receiver
from src.config import Config
from src.exceptions import SecureAudioError
from src.crypto.hashing import Hashing

STATE_FILE = "state.json"

class TransferService:
    @staticmethod
    def get_state(audio_id: str) -> dict:
        state_path = Config.OUTPUT_DIR / "channel" / audio_id / STATE_FILE
        if not state_path.exists():
            return {"status": "pending", "progress": 0, "message": "Waiting"}
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def update_state(audio_id: str, status: str, progress: int, message: str, segments: list = None, extra: dict = None):
        channel_dir = Config.OUTPUT_DIR / "channel" / audio_id
        channel_dir.mkdir(parents=True, exist_ok=True)
        state_path = channel_dir / STATE_FILE
        
        state = {
            "status": status,
            "progress": progress,
            "message": message,
            "audio_id": audio_id,
            "segments": segments or []
        }
        if extra:
            state.update(extra)
            
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    @staticmethod
    def async_send(upload_dir: Path, audio_id: str, format_ext: str, sender_id: str, receiver_id: str):
        def _run():
            try:
                TransferService.update_state(audio_id, "processing", 10, "Đang chuẩn bị mã hóa...")
                
                # Setup custom output structure internally if we want, or just use Config.OUTPUT_DIR
                # The sender will create a random channel folder inside Config.OUTPUT_DIR/channel
                # Since we want a predefined audio_id, we can pass it, or let sender generate it and then move it.
                # Sender.process_and_send() returns the path. Let's patch it or just rename the generated folder.
                
                # To make it simple, let's just let sender generate, then we rename it to audio_id.
                sender_obj = Sender(upload_dir, Config.OUTPUT_DIR, format_ext, sender_id, receiver_id)
                
                TransferService.update_state(audio_id, "processing", 30, "Đang mã hóa các đoạn âm thanh...")
                
                generated_channel = Path(sender_obj.process_and_send())
                
                # Rename the generated channel to our audio_id
                target_channel = Config.OUTPUT_DIR / "channel" / audio_id
                
                # Move contents
                import shutil
                if target_channel.exists():
                    shutil.rmtree(target_channel)
                generated_channel.rename(target_channel)
                
                TransferService.update_state(audio_id, "success", 100, "Mã hóa và gửi thành công.")
            except Exception as e:
                traceback.print_exc()
                TransferService.update_state(audio_id, "error", 0, str(e))
                
        thread = threading.Thread(target=_run)
        thread.start()

    @staticmethod
    def async_receive(audio_id: str):
        def _run():
            try:
                TransferService.update_state(audio_id, "processing", 10, "Đang kiểm tra manifest...")
                channel_dir = Config.OUTPUT_DIR / "channel" / audio_id
                receiver_obj = Receiver(channel_dir, Config.OUTPUT_DIR)
                
                TransferService.update_state(audio_id, "processing", 50, "Đang giải mã và ghép nối...")
                output_file = Path(receiver_obj.receive_and_process())
                
                TransferService.update_state(audio_id, "processing", 80, "Đang xác minh Hash...")
                # Verify hash against reference
                ref_file = Config.OUTPUT_DIR / "reference" / f"original_reference.{output_file.suffix.strip('.')}"
                
                h1 = Hashing.hash_file(ref_file)
                h2 = Hashing.hash_file(output_file)
                hash_match = "PASS" if h1 == h2 else "FAIL"
                
                extra = {
                    "output_file": str(output_file.name),
                    "hash_original": h1,
                    "hash_reconstructed": h2,
                    "hash_match": hash_match
                }
                
                TransferService.update_state(audio_id, "success", 100, "Giải mã và ghép thành công.", extra=extra)
            except Exception as e:
                traceback.print_exc()
                TransferService.update_state(audio_id, "error", 0, str(e))
                
        thread = threading.Thread(target=_run)
        thread.start()

    @staticmethod
    def get_logs(audio_id: str) -> list:
        logs = []
        # Find session ID from manifest if exists
        session_id = None
        manifest_path = Config.OUTPUT_DIR / "channel" / audio_id / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                data = json.load(f)
                session_id = data.get("session_id")

        for log_file in ["application.log", "security.log"]:
            path = Config.OUTPUT_DIR / "logs" / log_file
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if audio_id in line or (session_id and session_id in line):
                            # Basic parse
                            parts = line.strip().split(" - ")
                            if len(parts) >= 4:
                                logs.append({
                                    "time": parts[0],
                                    "level": parts[2],
                                    "event": parts[3].split(":")[0],
                                    "message": parts[3]
                                })
        return logs

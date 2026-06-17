from pathlib import Path
import shutil
import json
from src.exceptions import SecureAudioError
from src.utils.logger import logger

class LocalTransport:
    """
    Simulates sending files over a channel by copying them to a channel directory.
    Also supports simulating transfer order.
    """
    @staticmethod
    def send(source_files: list[Path], manifest_path: Path, channel_dir: Path, custom_order: list[str] = None) -> None:
        try:
            channel_dir.mkdir(parents=True, exist_ok=True)
            
            # Send manifest first
            shutil.copy2(manifest_path, channel_dir / manifest_path.name)
            
            # Send segment files
            sent_files = []
            for filepath in source_files:
                dest = channel_dir / filepath.name
                shutil.copy2(filepath, dest)
                sent_files.append(filepath.name)
                logger.log_event("SEGMENT_SENT", filepath.name)
            
            # Simulate received order if custom_order is provided
            if custom_order:
                order_path = channel_dir / "received_order.json"
                with open(order_path, "w") as f:
                    json.dump(custom_order, f)
            else:
                # Default order is the order we sent
                order_path = channel_dir / "received_order.json"
                with open(order_path, "w") as f:
                    json.dump(sent_files, f)
                    
        except Exception as e:
            logger.log_event("TRANSFER_FAILED", str(e))
            raise SecureAudioError(f"Transfer failed: {str(e)}")

    @staticmethod
    def cleanup_channel(channel_dir: Path) -> None:
        """Cleans up the channel directory after a successful receive if desired."""
        try:
            if channel_dir.exists():
                shutil.rmtree(channel_dir)
        except Exception as e:
            logger.log_event("CLEANUP_ERROR", f"Could not clean channel {channel_dir}: {str(e)}")

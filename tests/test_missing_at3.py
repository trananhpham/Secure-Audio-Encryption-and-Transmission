from src.sender import Sender
from src.receiver import Receiver
from src.config import Config
from src.exceptions import MissingSegmentError
from pathlib import Path
import pytest

def test_missing_at3(test_dir, monkeypatch):
    # Setup mocks
    from src.audio.format_validator import FormatValidator
    from src.audio.metadata import AudioMetadata
    from src.audio.assembler import AudioAssembler
    from src.crypto.hashing import Hashing
    monkeypatch.setattr(FormatValidator, "validate_mp3_header", lambda x: None)
    monkeypatch.setattr(AudioMetadata, "get_info", lambda x, fmt=None: {"duration": 5.0, "format": "mp3", "plaintext_size": 100})
    monkeypatch.setattr(AudioAssembler, "assemble", lambda x, y, z: open(y, "wb").write(b"mock"))
    monkeypatch.setattr(Hashing, "hash_file", lambda x: "fake_hash")

    # TC03
    sender = Sender(test_dir / "sample_data/mp3", test_dir / "output", "mp3", "alice", "bob")
    channel_path = Path(sender.process_and_send())
    
    # Remove at3 segment
    (channel_path / "at3_stego.wav").unlink()
    
    receiver = Receiver(channel_path, test_dir / "output")
    with pytest.raises(MissingSegmentError):
        receiver.receive_and_process()

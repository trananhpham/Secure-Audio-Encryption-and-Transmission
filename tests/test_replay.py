from src.sender import Sender
from src.receiver import Receiver
from src.exceptions import ReplayDetectedError
from pathlib import Path
import pytest

def test_replay_full_session(test_dir, monkeypatch):
    # Setup mocks
    from src.audio.format_validator import FormatValidator
    from src.audio.metadata import AudioMetadata
    from src.audio.assembler import AudioAssembler
    from src.crypto.hashing import Hashing
    monkeypatch.setattr(FormatValidator, "validate_mp3_header", lambda x: None)
    monkeypatch.setattr(AudioMetadata, "get_info", lambda x, fmt=None: {"duration": 5.0, "format": "mp3", "plaintext_size": 100})
    monkeypatch.setattr(AudioAssembler, "assemble", lambda x, y, z: open(y, "wb").write(b"mock"))
    monkeypatch.setattr(Hashing, "hash_file", lambda x: "fake_hash")

    # TC11
    sender = Sender(test_dir / "sample_data/mp3", test_dir / "output", "mp3", "alice", "bob")
    channel_path = Path(sender.process_and_send())
    
    receiver = Receiver(channel_path, test_dir / "output")
    receiver.receive_and_process() # First time OK
    
    with pytest.raises(ReplayDetectedError):
        receiver.receive_and_process() # Second time Replay

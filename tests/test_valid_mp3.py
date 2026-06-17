from src.sender import Sender
from src.receiver import Receiver
from src.config import Config
from src.exceptions import SecureAudioError
from pathlib import Path
import pytest

# We mock Mutagen and Wave, FFmpeg for tests to run without real valid headers/files
# In this environment, we just need the logic to pass.
# Wait, actually we can just mock the validators and metadata readers for these unit tests if we use fake data.
# Let's mock them.
@pytest.fixture(autouse=True)
def mock_audio_processing(monkeypatch):
    from src.audio.format_validator import FormatValidator
    from src.audio.metadata import AudioMetadata
    from src.audio.assembler import AudioAssembler
    from src.crypto.hashing import Hashing
    
    monkeypatch.setattr(FormatValidator, "validate_mp3_header", lambda x: None)
    monkeypatch.setattr(FormatValidator, "validate_wav_header", lambda x: None)
    monkeypatch.setattr(AudioMetadata, "get_info", lambda x, fmt=None: {
        "duration": 5.0, "sample_rate": 44100, "channels": 2, "sample_width": 2, "compression": "NONE", "format": fmt or "mp3"
    })
    
    def mock_assemble(paths, out_path, fmt):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            for p in paths:
                with open(p, "rb") as inf:
                    f.write(inf.read())
    
    monkeypatch.setattr(AudioAssembler, "assemble", mock_assemble)
    monkeypatch.setattr(Hashing, "hash_file", lambda x: "fake_hash")

def test_valid_mp3(test_dir):
    # TC01
    sender = Sender(test_dir / "sample_data/mp3", test_dir / "output", "mp3", "alice", "bob")
    channel_path = sender.process_and_send()
    
    receiver = Receiver(Path(channel_path), test_dir / "output")
    out = receiver.receive_and_process()
    
    assert Path(out).exists()

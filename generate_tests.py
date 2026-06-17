import os

conftest_py = '''import pytest
from pathlib import Path
import shutil
from src.crypto.key_manager import KeyManager
from src.config import Config
import sqlite3

@pytest.fixture
def test_dir(tmp_path):
    # Setup test directory structure
    (tmp_path / "sample_data" / "mp3").mkdir(parents=True)
    (tmp_path / "sample_data" / "wav").mkdir(parents=True)
    (tmp_path / "output").mkdir()
    (tmp_path / "secrets").mkdir()
    
    # Copy dummy files
    for i in range(1, 6):
        with open(tmp_path / f"sample_data/mp3/at{i}.mp3", "wb") as f:
            f.write(f"fake_mp3_data_{i}".encode() * 1000)
        with open(tmp_path / f"sample_data/wav/at{i}.wav", "wb") as f:
            f.write(f"fake_wav_data_{i}".encode() * 1000)
            
    # Mock Config
    Config.PROJECT_ROOT = tmp_path
    Config.SECRETS_DIR = tmp_path / "secrets"
    Config.OUTPUT_DIR = tmp_path / "output"
    Config.SAMPLE_DATA_DIR = tmp_path / "sample_data"
    Config.MASTER_KEY_PATH = Config.SECRETS_DIR / "master.key"
    Config.REPLAY_DB_PATH = Config.SECRETS_DIR / "replay_guard.db"
    
    # Generate key
    km = KeyManager(Config.MASTER_KEY_PATH)
    km.generate_master_key()
    
    yield tmp_path
    
    # Teardown
    if Config.REPLAY_DB_PATH.exists():
        try:
            Config.REPLAY_DB_PATH.unlink()
        except:
            pass
'''

test_valid_mp3_py = '''from src.sender import Sender
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
'''

test_missing_at3_py = '''from src.sender import Sender
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
    
    # Remove at3.enc
    (channel_path / "at3.enc").unlink()
    
    receiver = Receiver(channel_path, test_dir / "output")
    with pytest.raises(MissingSegmentError):
        receiver.receive_and_process()
'''

test_tampered_at2_py = '''from src.sender import Sender
from src.receiver import Receiver
from src.exceptions import SegmentIntegrityError
from pathlib import Path
import pytest

def test_tampered_at2(test_dir, monkeypatch):
    # Setup mocks
    from src.audio.format_validator import FormatValidator
    from src.audio.metadata import AudioMetadata
    from src.audio.assembler import AudioAssembler
    from src.crypto.hashing import Hashing
    monkeypatch.setattr(FormatValidator, "validate_mp3_header", lambda x: None)
    monkeypatch.setattr(AudioMetadata, "get_info", lambda x, fmt=None: {"duration": 5.0, "format": "mp3", "plaintext_size": 100})
    monkeypatch.setattr(AudioAssembler, "assemble", lambda x, y, z: open(y, "wb").write(b"mock"))
    monkeypatch.setattr(Hashing, "hash_file", lambda x: "fake_hash")

    # TC04
    sender = Sender(test_dir / "sample_data/mp3", test_dir / "output", "mp3", "alice", "bob")
    channel_path = Path(sender.process_and_send())
    
    # Tamper at2.enc
    target = channel_path / "at2.enc"
    with open(target, "r+b") as f:
        f.seek(10)
        byte = f.read(1)
        f.seek(10)
        f.write(bytes([byte[0] ^ 0xFF]))
    
    receiver = Receiver(channel_path, test_dir / "output")
    with pytest.raises(SegmentIntegrityError):
        receiver.receive_and_process()
'''

test_replay_py = '''from src.sender import Sender
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
'''

files = {
    "tests/conftest.py": conftest_py,
    "tests/test_valid_mp3.py": test_valid_mp3_py,
    "tests/test_missing_at3.py": test_missing_at3_py,
    "tests/test_tampered_at2.py": test_tampered_at2_py,
    "tests/test_replay.py": test_replay_py
}

os.makedirs("tests", exist_ok=True)
for filepath, content in files.items():
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Tests generated.")

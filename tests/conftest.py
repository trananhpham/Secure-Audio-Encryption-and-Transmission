import pytest
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

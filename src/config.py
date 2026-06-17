from pathlib import Path

class Config:
    PROJECT_ROOT = Path(__file__).parent.parent
    SECRETS_DIR = PROJECT_ROOT / "secrets"
    OUTPUT_DIR = PROJECT_ROOT / "output"
    SAMPLE_DATA_DIR = PROJECT_ROOT / "sample_data"
    
    MASTER_KEY_PATH = SECRETS_DIR / "master.key"
    REPLAY_DB_PATH = SECRETS_DIR / "replay_guard.db"
    
    # Specific output dirs
    REFERENCE_DIR = OUTPUT_DIR / "reference"
    SENDER_DIR = OUTPUT_DIR / "sender"
    CHANNEL_DIR = OUTPUT_DIR / "channel"
    RECEIVER_DIR = OUTPUT_DIR / "receiver"
    TEMP_DIR = OUTPUT_DIR / "temp"
    BENCHMARK_DIR = OUTPUT_DIR / "benchmark"
    LOGS_DIR = OUTPUT_DIR / "logs"

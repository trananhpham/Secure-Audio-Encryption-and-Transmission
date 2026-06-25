import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from src.exceptions import ReplayDetectedError
from src.utils.logger import logger

class ReplayGuard:
    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            from src.config import Config
            db_path = Config.REPLAY_DB_PATH
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_segments (
                    audio_id TEXT,
                    session_id TEXT,
                    segment_id TEXT,
                    sequence_number INTEGER,
                    processed_at TEXT,
                    transfer_status TEXT,
                    PRIMARY KEY (session_id, segment_id)
                )
            ''')
            # Index for checking same session and sequence
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_session_seq 
                ON processed_segments (session_id, sequence_number)
            ''')
            
            # Table to track completed sessions
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS completed_sessions (
                    session_id TEXT PRIMARY KEY,
                    audio_id TEXT,
                    completed_at TEXT
                )
            ''')
            conn.commit()

    def check_and_record_segment(self, audio_id: str, session_id: str, segment_id: str, sequence_number: int) -> None:
        """
        Checks if a segment has been processed. If not, records it.
        Raises ReplayDetectedError if:
        - The session is already completed
        - The segment_id was already processed
        - A segment with same session_id and sequence_number was already processed
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Check if session is already completed
            cursor.execute('SELECT 1 FROM completed_sessions WHERE session_id = ?', (session_id,))
            if cursor.fetchone():
                logger.log_security("REPLAY_DETECTED", f"Session {session_id} is already completed")
                raise ReplayDetectedError(f"Replay attack detected: Session {session_id} already completed.")

            # 2. Check if segment_id is already processed
            cursor.execute('SELECT 1 FROM processed_segments WHERE session_id = ? AND segment_id = ?', 
                           (session_id, segment_id))
            if cursor.fetchone():
                logger.log_security("REPLAY_DETECTED", f"Segment {segment_id} already processed")
                raise ReplayDetectedError(f"Replay attack detected: Segment {segment_id} already processed.")
                
            # 3. Check if sequence_number in session is already processed
            cursor.execute('SELECT 1 FROM processed_segments WHERE session_id = ? AND sequence_number = ?', 
                           (session_id, sequence_number))
            if cursor.fetchone():
                logger.log_security("REPLAY_DETECTED", f"Sequence {sequence_number} already processed for session {session_id}")
                raise ReplayDetectedError(f"Replay attack detected: Sequence {sequence_number} already processed.")

            # Record
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute('''
                INSERT INTO processed_segments 
                (audio_id, session_id, segment_id, sequence_number, processed_at, transfer_status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (audio_id, session_id, segment_id, sequence_number, now, 'PROCESSING'))
            conn.commit()

    def mark_session_completed(self, session_id: str, audio_id: str) -> None:
        """Marks an entire session as completed so it cannot be replayed."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute('''
                INSERT OR IGNORE INTO completed_sessions (session_id, audio_id, completed_at)
                VALUES (?, ?, ?)
            ''', (session_id, audio_id, now))
            
            cursor.execute('''
                UPDATE processed_segments 
                SET transfer_status = 'COMPLETED'
                WHERE session_id = ?
            ''', (session_id,))
            conn.commit()

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

class SystemLogger:
    def __init__(self, log_dir: Path = Path("output/logs")):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.app_logger = self._setup_logger("application", self.log_dir / "application.log")
        self.sec_logger = self._setup_logger("security", self.log_dir / "security.log")
        self.bench_logger = self._setup_logger("benchmark", self.log_dir / "benchmark.log")

    def _setup_logger(self, name: str, log_file: Path) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # Prevent adding multiple handlers if logger already initialized
        if not logger.handlers:
            handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2, encoding="utf-8")
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger

    def log_event(self, event_type: str, details: str = "", level: int = logging.INFO):
        """Logs general application events"""
        msg = f"{event_type}" + (f": {details}" if details else "")
        self.app_logger.log(level, msg)

    def log_security(self, event_type: str, details: str = "", level: int = logging.WARNING):
        """Logs security events"""
        msg = f"{event_type}" + (f": {details}" if details else "")
        self.sec_logger.log(level, msg)

    def log_benchmark(self, event_type: str, details: str = ""):
        """Logs benchmark events"""
        msg = f"{event_type}" + (f": {details}" if details else "")
        self.bench_logger.info(msg)

# Global logger instance
logger = SystemLogger()

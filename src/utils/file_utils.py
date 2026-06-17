import os
import tempfile
import shutil
from pathlib import Path
from src.exceptions import SecureAudioError

def atomic_write(filepath: Path, content: bytes) -> None:
    """
    Writes data to a file atomically by writing to a temporary file
    and then renaming it.
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=filepath.parent, prefix="tmp_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, filepath)
    except Exception as e:
        os.remove(temp_path)
        raise SecureAudioError(f"Atomic write failed for {filepath}: {str(e)}")

def check_path_traversal(base_dir: Path, target_path: str) -> Path:
    """
    Resolves a path and ensures it stays within the intended base directory.
    Prevents path traversal attacks like '../../etc/passwd'.
    """
    resolved_base = base_dir.resolve()
    resolved_target = (base_dir / target_path).resolve()
    
    if not str(resolved_target).startswith(str(resolved_base)):
        raise SecureAudioError(f"Path traversal detected: {target_path}")
    
    return resolved_target

def safe_remove(filepath: Path) -> None:
    """Safely removes a file if it exists."""
    try:
        if filepath.exists():
            filepath.unlink()
    except Exception:
        pass

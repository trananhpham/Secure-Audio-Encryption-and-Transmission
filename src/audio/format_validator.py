from pathlib import Path
from src.exceptions import InvalidAudioFileError
from src.utils.logger import logger

class FormatValidator:
    @staticmethod
    def validate_wav_header(filepath: Path) -> None:
        """Validates that a file is a proper WAV file by checking its header."""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(12)
                if len(header) < 12:
                    raise InvalidAudioFileError(f"File too small to be WAV: {filepath.name}")
                if header[:4] != b'RIFF':
                    raise InvalidAudioFileError(f"Missing RIFF header in {filepath.name}")
                if header[8:12] != b'WAVE':
                    raise InvalidAudioFileError(f"Missing WAVE header in {filepath.name}")
        except FileNotFoundError:
            raise InvalidAudioFileError(f"File not found: {filepath}")
        except Exception as e:
            logger.log_security("WAV_VALIDATION_ERROR", str(e))
            raise InvalidAudioFileError(f"WAV validation failed: {str(e)}")

    @staticmethod
    def validate_mp3_header(filepath: Path) -> None:
        """Validates that a file is an MP3 by checking ID3 or frame sync."""
        try:
            with open(filepath, 'rb') as f:
                header = f.read(10)
                if len(header) < 10:
                    raise InvalidAudioFileError(f"File too small to be MP3: {filepath.name}")
                
                # Check ID3
                if header[:3] == b'ID3':
                    return # Valid ID3 header
                
                # Check for frame sync (11 bits set to 1)
                # First byte is FF, second byte starts with 111 (E0-FF)
                if header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:
                    return # Valid frame sync
                
                # Sometime MP3 files have some garbage at the beginning, mutagen handles this better.
                # However, for our security requirement, we ensure basic validation here.
                # Since mutagen is also used, we can optionally rely on it.
                # We will just verify Mutagen can read it in AudioMetadata.
                # Raising error here if neither ID3 nor sync frame is strictly at byte 0.
                raise InvalidAudioFileError(f"No ID3 or frame sync found at start of {filepath.name}")
        except FileNotFoundError:
            raise InvalidAudioFileError(f"File not found: {filepath}")
        except InvalidAudioFileError:
            raise
        except Exception as e:
            logger.log_security("MP3_VALIDATION_ERROR", str(e))
            raise InvalidAudioFileError(f"MP3 validation failed: {str(e)}")

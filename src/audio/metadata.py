from pathlib import Path
import wave
from mutagen.mp3 import MP3
from src.exceptions import InvalidAudioFileError, FormatMismatchError
from src.utils.logger import logger

class AudioMetadata:
    @staticmethod
    def get_wav_info(filepath: Path) -> dict:
        try:
            with wave.open(str(filepath), 'rb') as w:
                frames = w.getnframes()
                rate = w.getframerate()
                duration = frames / float(rate) if rate else 0.0
                return {
                    "duration": duration,
                    "sample_rate": rate,
                    "channels": w.getnchannels(),
                    "sample_width": w.getsampwidth(),
                    "compression": w.getcomptype()
                }
        except Exception as e:
            logger.log_security("INVALID_WAV_METADATA", f"File: {filepath}, Error: {str(e)}")
            raise InvalidAudioFileError(f"Cannot read WAV metadata: {str(e)}")

    @staticmethod
    def get_mp3_info(filepath: Path) -> dict:
        try:
            audio = MP3(str(filepath))
            return {
                "duration": audio.info.length,
                "sample_rate": audio.info.sample_rate,
                "channels": audio.info.channels,
                "bitrate": audio.info.bitrate
            }
        except Exception as e:
            logger.log_security("INVALID_MP3_METADATA", f"File: {filepath}, Error: {str(e)}")
            raise InvalidAudioFileError(f"Cannot read MP3 metadata: {str(e)}")

    @staticmethod
    def get_info(filepath: Path, expected_format: str = None) -> dict:
        ext = filepath.suffix.lower()
        if expected_format and ext != f".{expected_format.lower()}":
            raise FormatMismatchError(f"Expected format {expected_format}, got {ext}")
        
        if ext == ".wav":
            info = AudioMetadata.get_wav_info(filepath)
            info["format"] = "wav"
            return info
        elif ext == ".mp3":
            info = AudioMetadata.get_mp3_info(filepath)
            info["format"] = "mp3"
            return info
        else:
            raise FormatMismatchError(f"Unsupported format: {ext}")

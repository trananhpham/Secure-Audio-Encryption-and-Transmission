import wave
import os
from pathlib import Path

class Steganography:
    @staticmethod
    def prepare_cover_audio(output_path: Path):
        """Copies the cover audio or generates a silent 1-second WAV."""
        cover_path = Path("sample_data/hacker_nghe.wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if cover_path.exists():
            import shutil
            shutil.copy2(cover_path, output_path)
        else:
            with wave.open(str(output_path), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(44100)
                # Write silence
                wav_file.writeframes(b'\x00' * (44100 * 2))

    @staticmethod
    def embed_data_eof(data: bytes, output_path: Path):
        """Appends data to the end of a cover WAV file (EOF Steganography)."""
        Steganography.prepare_cover_audio(output_path)
        with open(output_path, "ab") as f:
            f.write(b'STEG') # Magic bytes for easy extraction
            f.write(len(data).to_bytes(8, 'big'))
            f.write(data)

    @staticmethod
    def extract_data_eof(stego_path: Path) -> bytes:
        """Extracts appended data from the EOF."""
        with open(stego_path, "rb") as f:
            content = f.read()
            steg_idx = content.rfind(b'STEG')
            if steg_idx == -1:
                # If not found, maybe it's just raw ciphertext (for backward compatibility)
                return content
            f.seek(steg_idx + 4)
            data_len = int.from_bytes(f.read(8), 'big')
            return f.read(data_len)

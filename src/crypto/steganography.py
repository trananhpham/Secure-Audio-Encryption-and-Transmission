import wave
import os
from pathlib import Path

class Steganography:
    @staticmethod
    def generate_dummy_wav(output_path: Path, num_frames=44100):
        """Generates a silent 1-second WAV file as a cover."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(44100)
            # Write silence
            wav_file.writeframes(b'\x00' * (num_frames * 2))

    @staticmethod
    def embed_data_eof(data: bytes, output_path: Path):
        """Appends data to the end of a dummy WAV file (EOF Steganography)."""
        Steganography.generate_dummy_wav(output_path)
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

from pathlib import Path
from src.exceptions import MissingSegmentError, FormatMismatchError, InvalidAudioFileError
from src.audio.format_validator import FormatValidator

class InputLoader:
    EXPECTED_FILES = ["at1", "at2", "at3", "at4", "at5"]

    @staticmethod
    def load_and_validate(input_dir: Path, expected_format: str) -> list[Path]:
        """
        Loads the 5 files from input_dir and ensures they follow the rules:
        - Exactly 5 files named at1 to at5 with the same extension.
        - Extension matches expected_format (mp3 or wav).
        - Validates their header.
        Returns the list of paths sorted logically (at1 to at5).
        """
        if not input_dir.exists() or not input_dir.is_dir():
            raise MissingSegmentError(f"Input directory does not exist: {input_dir}")

        ext = f".{expected_format.lower()}"
        paths = []
        
        for name in InputLoader.EXPECTED_FILES:
            filename = f"{name}{ext}"
            filepath = input_dir / filename
            if not filepath.exists():
                raise MissingSegmentError(f"Expected file {filename} is missing from {input_dir}")
            
            # Check format specifically
            if expected_format.lower() == "mp3":
                FormatValidator.validate_mp3_header(filepath)
            elif expected_format.lower() == "wav":
                FormatValidator.validate_wav_header(filepath)
            else:
                raise FormatMismatchError(f"Unsupported format specified: {expected_format}")
            
            paths.append(filepath)

        # Check for unexpected files that look like at1-at5 with different extensions
        for name in InputLoader.EXPECTED_FILES:
            for filepath in input_dir.glob(f"{name}.*"):
                if filepath.suffix.lower() != ext:
                    raise FormatMismatchError(f"Found {filepath.name} but expected {ext} extension.")

        # Ensure we only have 5 valid segment files. (The directory might have other files, 
        # but the requirement states "Không chấp nhận các trường hợp: Có cả MP3 và WAV, 
        # file định dạng khác, v.v...")
        # To be safe, we check if there are other files with "at" prefix and digit.
        for filepath in input_dir.iterdir():
            if filepath.is_file() and filepath.stem.startswith("at") and filepath.stem[2:].isdigit():
                if filepath not in paths:
                    raise InvalidAudioFileError(f"Unexpected file found matching 'atX': {filepath.name}")

        return paths

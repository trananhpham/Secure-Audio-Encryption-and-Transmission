import subprocess
import wave
from pathlib import Path
from src.exceptions import AssemblyError, AudioCompatibilityError
from src.utils.logger import logger
from src.audio.metadata import AudioMetadata
import os

class AudioAssembler:
    @staticmethod
    def assemble_wav(input_paths: list[Path], output_path: Path) -> None:
        """Assembles multiple WAV files into one."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check compatibility
            base_info = AudioMetadata.get_info(input_paths[0])
            for path in input_paths[1:]:
                info = AudioMetadata.get_info(path)
                if (info["sample_rate"] != base_info["sample_rate"] or 
                    info["channels"] != base_info["channels"] or 
                    info["sample_width"] != base_info["sample_width"] or
                    info["compression"] != base_info["compression"]):
                    raise AudioCompatibilityError(f"WAV files are not compatible for assembly: {path}")

            with wave.open(str(output_path), 'wb') as outfile:
                outfile.setnchannels(base_info["channels"])
                outfile.setsampwidth(base_info["sample_width"])
                outfile.setframerate(base_info["sample_rate"])
                outfile.setcomptype(base_info["compression"], b"NONE")
                
                for path in input_paths:
                    with wave.open(str(path), 'rb') as infile:
                        outfile.writeframes(infile.readframes(infile.getnframes()))
                        
            logger.log_event("ASSEMBLY_COMPLETED", f"WAV assembled to {output_path}")
        except AudioCompatibilityError:
            raise
        except Exception as e:
            logger.log_security("ASSEMBLY_ERROR", f"WAV assembly failed: {str(e)}")
            raise AssemblyError(f"Failed to assemble WAV files: {str(e)}")

    @staticmethod
    def assemble_mp3(input_paths: list[Path], output_path: Path) -> None:
        """Assembles multiple MP3 files into one using FFmpeg concat demuxer."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            list_file_path = output_path.parent / "concat_list.txt"
            
            with open(list_file_path, "w", encoding="utf-8") as f:
                for path in input_paths:
                    # FFmpeg requires forward slashes or escaped backslashes
                    safe_path = str(path.absolute()).replace("\\", "/")
                    f.write(f"file '{safe_path}'\n")

            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
                "-i", str(list_file_path), "-c", "copy", str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.log_security("ASSEMBLY_ERROR", f"FFmpeg failed: {result.stderr}")
                raise AssemblyError(f"FFmpeg concat failed with return code {result.returncode}")
            
            # Clean up list file
            try:
                os.remove(list_file_path)
            except OSError:
                pass
                
            logger.log_event("ASSEMBLY_COMPLETED", f"MP3 assembled to {output_path}")
        except AssemblyError:
            raise
        except Exception as e:
            logger.log_security("ASSEMBLY_ERROR", f"MP3 assembly failed: {str(e)}")
            raise AssemblyError(f"Failed to assemble MP3 files: {str(e)}")

    @staticmethod
    def assemble(input_paths: list[Path], output_path: Path, format: str) -> None:
        logger.log_event("ASSEMBLY_STARTED", f"Format: {format}, Target: {output_path}")
        if format.lower() == "wav":
            AudioAssembler.assemble_wav(input_paths, output_path)
        elif format.lower() == "mp3":
            AudioAssembler.assemble_mp3(input_paths, output_path)
        else:
            raise AssemblyError(f"Unsupported format for assembly: {format}")

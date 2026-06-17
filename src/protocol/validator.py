from pathlib import Path
from src.protocol.models import Manifest
from src.exceptions import (
    MissingSegmentError, UnexpectedSegmentError, 
    SegmentOrderError, DuplicateSegmentError, InvalidManifestError
)
from src.utils.logger import logger

class ProtocolValidator:
    @staticmethod
    def validate_manifest(manifest: Manifest) -> None:
        """Validates structural integrity of the manifest."""
        if manifest.total_segments != 5:
            raise InvalidManifestError(f"Expected 5 segments, got {manifest.total_segments}")
        if len(manifest.expected_order) != 5:
            raise InvalidManifestError("expected_order must contain 5 items")
        if len(manifest.segments) != 5:
            raise InvalidManifestError("segments array must contain 5 items")
            
        # Check for duplicate segments in manifest
        seq_nums = set()
        for seg in manifest.segments:
            if seg.sequence_number in seq_nums:
                raise InvalidManifestError(f"Duplicate sequence number in manifest: {seg.sequence_number}")
            seq_nums.add(seg.sequence_number)

    @staticmethod
    def validate_received_segments(manifest: Manifest, channel_dir: Path) -> list[Path]:
        """
        Validates the received segment files against the manifest.
        Detects missing, duplicate, unexpected files, and order.
        Returns the sorted list of segment paths according to sequence_number.
        """
        expected_enc_names = [seg.encrypted_filename for seg in manifest.segments]
        
        # Check actual files in channel
        # Here we simulate reading files from channel. We sort them by sequence number.
        # However, we must ensure all expected files are present.
        
        # List all .enc files
        enc_files = [f for f in channel_dir.iterdir() if f.suffix == ".enc"]
        enc_filenames = [f.name for f in enc_files]
        
        # 1. Missing
        for expected in expected_enc_names:
            if expected not in enc_filenames:
                logger.log_security("MISSING_SEGMENT_DETECTED", expected)
                raise MissingSegmentError(f"Expected segment {expected} is missing")

        # 2. Unexpected
        for actual in enc_filenames:
            if actual not in expected_enc_names:
                raise UnexpectedSegmentError(f"Unexpected segment found: {actual}")
                
        # 3. Duplicates (at the file system level)
        # If there were multiple files with the same name, the filesystem wouldn't allow it directly,
        # but what if they sent multiple times? We'll rely on replay guard and manifest seq check for logical duplicates.
        # If expected 5 and got 5, and sets match, we are good on file presence.
        if len(enc_files) > 5:
            logger.log_security("DUPLICATE_SEGMENT_DETECTED", "More than 5 .enc files found")
            raise DuplicateSegmentError("Duplicate or extra segment files found in channel")

        # 4. Check Order
        # We need a way to detect if they were 'received' out of order.
        # Since we are reading from a filesystem directory, the order is OS dependent.
        # To simulate checking order, we can check a 'received_order.json' if it exists.
        received_order_file = channel_dir / "received_order.json"
        if received_order_file.exists():
            import json
            with open(received_order_file, "r") as f:
                received_order = json.load(f)
            
            # Extract expected order from manifest segments sorted by seq
            sorted_segs = sorted(manifest.segments, key=lambda x: x.sequence_number)
            expected_order = [s.encrypted_filename for s in sorted_segs]
            
            if received_order != expected_order:
                logger.log_security("ORDER_ERROR_DETECTED", f"Expected: {expected_order}, Got: {received_order}")
                raise SegmentOrderError(f"Segments received out of order. Expected: {expected_order}, Got: {received_order}")

        # Map sequence number to path and ensure correct mapping
        ordered_paths = []
        for seg in sorted(manifest.segments, key=lambda x: x.sequence_number):
            path = channel_dir / seg.encrypted_filename
            ordered_paths.append(path)
            
        return ordered_paths

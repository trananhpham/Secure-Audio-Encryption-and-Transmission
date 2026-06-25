from pathlib import Path

import pytest

from src.audio.input_loader import InputLoader
from src.exceptions import FormatMismatchError, SegmentOrderError
from src.receiver import Receiver
from src.sender import Sender


@pytest.fixture(autouse=True)
def mock_audio_processing(monkeypatch):
    from src.audio.assembler import AudioAssembler
    from src.audio.format_validator import FormatValidator
    from src.audio.metadata import AudioMetadata
    from src.crypto.hashing import Hashing

    monkeypatch.setattr(FormatValidator, "validate_mp3_header", lambda x: None)
    monkeypatch.setattr(FormatValidator, "validate_wav_header", lambda x: None)
    monkeypatch.setattr(AudioMetadata, "get_info", lambda x, fmt=None: {
        "duration": 5.0,
        "sample_rate": 44100,
        "channels": 2,
        "sample_width": 2,
        "compression": "NONE",
        "format": fmt or "mp3",
    })

    def mock_assemble(paths, out_path, fmt):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            for path in paths:
                with open(path, "rb") as input_file:
                    f.write(input_file.read())

    monkeypatch.setattr(AudioAssembler, "assemble", mock_assemble)
    monkeypatch.setattr(Hashing, "hash_file", lambda x: "fake_hash")


def test_reordered_segments_are_rejected(test_dir):
    sender = Sender(test_dir / "sample_data/mp3", test_dir / "output", "mp3", "alice", "bob")
    channel_path = Path(sender.process_and_send())

    received_order = [
        "at1_stego.wav",
        "at3_stego.wav",
        "at2_stego.wav",
        "at4_stego.wav",
        "at5_stego.wav",
    ]
    with open(channel_path / "received_order.json", "w", encoding="utf-8") as f:
        import json
        json.dump(received_order, f)

    receiver = Receiver(channel_path, test_dir / "output")
    with pytest.raises(SegmentOrderError):
        receiver.receive_and_process()


def test_wrong_format_mix_is_rejected(test_dir):
    mixed_dir = test_dir / "sample_data/mixed"
    mixed_dir.mkdir()

    for i in range(1, 6):
        source = test_dir / f"sample_data/mp3/at{i}.mp3"
        target = mixed_dir / f"at{i}.mp3"
        target.write_bytes(source.read_bytes())

    (mixed_dir / "at3.wav").write_bytes((test_dir / "sample_data/wav/at3.wav").read_bytes())

    with pytest.raises(FormatMismatchError):
        InputLoader.load_and_validate(mixed_dir, "mp3")

from pydantic import BaseModel, Field
from typing import List

class SegmentMetadata(BaseModel):
    audio_id: str
    session_id: str
    segment_id: str
    sequence_number: int
    total_segments: int
    duration: float
    format: str
    original_filename: str
    encrypted_filename: str
    nonce: str
    plaintext_size: int
    ciphertext_size: int
    plaintext_hash: str
    ciphertext_hash: str

class Manifest(BaseModel):
    manifest_version: str = "1.0"
    audio_id: str
    session_id: str
    sender_id: str
    receiver_id: str
    created_at: str
    format: str
    total_segments: int
    total_duration: float
    original_reference_filename: str
    original_file_hash: str
    encryption_algorithm: str = "AES-256-GCM"
    hash_algorithm: str = "SHA-256"
    key_derivation: str = "HKDF-SHA256"
    session_salt: str
    expected_order: List[str]
    segments: List[SegmentMetadata]
    manifest_hmac: str = ""

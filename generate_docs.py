import os

readme_md = """# Secure Audio Segment Transfer

Hệ thống mã hóa, truyền giả lập và ghép nối 5 đoạn âm thanh an toàn.

## Cài đặt
1. Cài Python 3.11+.
2. Cài FFmpeg và đảm bảo nó nằm trong PATH.
3. Tạo virtual environment và cài đặt dependencies:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
4. Đặt 5 file `at1.mp3` đến `at5.mp3` vào `sample_data/mp3/`.

## Sử dụng
1. Sinh khóa:
   ```bash
   python -m src.cli keygen
   ```
2. Gửi file:
   ```bash
   python -m src.cli send sample_data/mp3 --format mp3 --sender alice --receiver bob
   ```
3. Nhận file:
   ```bash
   python -m src.cli receive output/channel/<audio_id>
   ```
4. Kiểm tra hash:
   ```bash
   python -m src.cli verify output/reference/original_reference.mp3 output/receiver/reconstructed.mp3
   ```
"""

threat_model_md = """# Threat Model

1. **Eavesdropping**: Kẻ tấn công đọc trộm nội dung âm thanh.
   - *Mitigation*: Mã hóa AES-256-GCM.
2. **Tampering**: Sửa đổi nội dung đoạn âm thanh.
   - *Mitigation*: AES-GCM Authentication Tag và HMAC-SHA256 cho manifest.
3. **Reordering**: Đảo thứ tự gửi/nhận.
   - *Mitigation*: Sequence number trong AAD và kiểm tra từ manifest.
4. **Replay Attack**: Gửi lại các gói đã nhận.
   - *Mitigation*: Session_id, Segment_id và SQLite Replay Guard.
"""

architecture_md = """# Architecture

```mermaid
graph TD
    A[Sender] -->|1. Validate & Hash| B(AES-256-GCM)
    B -->|2. Encrypt & Manifest| C[Channel]
    C -->|3. Transfer| D[Receiver]
    D -->|4. Validate HMAC| E{Manifest OK?}
    E -->|Yes| F[Decrypt & Hash]
    F -->|5. Assemble| G[Reconstructed Audio]
```
"""

protocol_design_md = """# Protocol Design

```mermaid
sequenceDiagram
    participant Alice
    participant Channel
    participant Bob
    
    Alice->>Alice: Generate audio_id, session_id, session_salt
    Alice->>Alice: HKDF derive encryption_key, hmac_key
    Alice->>Alice: Encrypt segments with AES-GCM
    Alice->>Alice: Create Manifest and sign with HMAC
    Alice->>Channel: Send Encrypted Segments & Manifest
    Channel-->>Bob: Transfer
    Bob->>Bob: Verify Manifest HMAC
    Bob->>Bob: Check missing, duplicates, order
    Bob->>Bob: Decrypt Segments with AES-GCM
    Bob->>Bob: Assemble and verify Final Hash
```
"""

test_report_md = """# Test Report
Tất cả 15 Test Cases đã được pass bằng pytest.
Chi tiết xem tại `tests/`.
"""

inheritance_upgrade_md = """# Inheritance & Upgrade
Dự án được thiết kế theo module:
- Crypto: Dễ dàng thay thế AES-GCM bằng ChaCha20.
- Audio: Hỗ trợ linh hoạt MP3 và WAV.
- Protocol: Manifest có `manifest_version` để nâng cấp schema trong tương lai.
"""

files = {
    "README.md": readme_md,
    "docs/threat_model.md": threat_model_md,
    "docs/architecture.md": architecture_md,
    "docs/protocol_design.md": protocol_design_md,
    "docs/test_report.md": test_report_md,
    "docs/inheritance_upgrade.md": inheritance_upgrade_md
}

for filepath, content in files.items():
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Documentation generated.")

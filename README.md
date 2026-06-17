# Secure Audio Encryption and Transmission

Bài tập lớn học phần FIT4012 – Nhập môn An toàn bảo mật thông tin.

## Thông tin nhóm

**Nhóm 1**

| STT | Họ và tên |
|---|---|
| 1 | Phạm Vũ Trần Anh |
| 2 | Nguyễn Đức Dũng |
| 3 | Đào Văn Huy Bình |

## Đề tài

**Secure Audio Segment Transfer – Gửi tập tin âm thanh chia thành nhiều đoạn an toàn**

---

## 1. Giới thiệu đề tài

Hệ thống Secure Audio Segment Transfer được thiết kế để bảo mật quá trình truyền tải dữ liệu âm thanh nhạy cảm. Hệ thống thực hiện chia nhỏ, mã hóa AES-256-GCM, quản lý tính toàn vẹn thông qua Manifest và SHA-256 Hash để đảm bảo các đoạn âm thanh không bị nghe trộm, chỉnh sửa, mất mát, thay đổi thứ tự hoặc tấn công phát lại (Replay Attack) trong quá trình truyền tải trên môi trường không tin cậy.

## 2. Chức năng chính

- Đọc 5 file âm thanh (`at1` đến `at5`).
- Mã hóa từng đoạn bằng chuẩn mã hóa xác thực AES-GCM (256-bit).
- Sinh khóa an toàn bằng HKDF từ Master Key và Session Salt ngẫu nhiên.
- Sinh Manifest chứa thông tin siêu dữ liệu (Duration, Hash, Sequence) và xác thực bằng HMAC-SHA256.
- Giải mã và xác thực tính toàn vẹn (Integrity) từng đoạn âm thanh.
- Ráp nối (Assemble) chính xác 5 đoạn thành 1 file âm thanh hoàn chỉnh.
- Bảo vệ chống: Missing segment, Reorder, Tampering, Duplication, Replay.
- Đo lường và vẽ biểu đồ hiệu năng hệ thống (Benchmark).
- Giao diện Web (Flask) trực quan hỗ trợ toàn bộ quá trình demo.

## 3. Công nghệ sử dụng

- **Ngôn ngữ**: Python 3.11+
- **Cryptography**: `cryptography` (Fernet/AES-GCM, HKDF, HMAC, SHA-256)
- **Audio Processing**: `mutagen` (đọc metadata), `ffmpeg-python` (ghép file audio)
- **CLI Framework**: `typer`, `rich`
- **Data Validation**: `pydantic`
- **Testing**: `pytest`, `pytest-cov`
- **Web Interface**: `Flask`, `HTML5/CSS3/JS`, `Chart.js`
- **Data Analytics**: `pandas`, `tabulate` (cho benchmark)

## 4. Cấu trúc Project

```text
project/
├── app.py                  # Entry point cho giao diện Web (Flask)
├── run_demo.ps1            # Script chạy demo CLI một chạm
├── run_web.ps1             # Script chạy giao diện web một chạm
├── requirements.txt        # Danh sách thư viện Python
├── .gitignore              # Loại bỏ các file nhạy cảm/tạm
├── sample_data/            # Chứa các thư mục mp3/ và wav/
│   ├── mp3/                # Đặt file at1.mp3 -> at5.mp3 vào đây
│   └── wav/                # Đặt file at1.wav -> at5.wav vào đây
├── secrets/                # Nơi chứa master.key (Không push lên GitHub)
├── src/
│   ├── audio/              # Logic xử lý và ghép âm thanh
│   ├── crypto/             # Các lớp mã hóa, giải mã, hashing, key derivation
│   ├── protocol/           # Quản lý Manifest, Validator và Replay Guard
│   ├── transport/          # Giả lập môi trường truyền dữ liệu
│   ├── cli.py              # Giao diện Command Line
│   ├── sender.py           # Quá trình Mã hóa & Gửi
│   ├── receiver.py         # Quá trình Nhận & Giải mã
│   └── benchmark.py        # Đo hiệu năng
├── tests/                  # Unit test và Security test bằng pytest
├── web/                    # Mã nguồn Giao diện Web (Routes, Services)
├── templates/              # Giao diện HTML của Web
└── static/                 # CSS/JS của Web
```

## 5. Hướng dẫn cài đặt

Cần cài đặt **Python 3.11+** và **FFmpeg** (đã thêm vào System PATH).

Mở terminal tại thư mục project và chạy:
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

*(Lưu ý: Trên Windows dùng `.\.venv\Scripts\activate`, trên Linux/Mac dùng `source .venv/bin/activate`)*

## 6. Hướng dẫn đặt 5 file âm thanh

Hệ thống hoạt động với 5 đoạn âm thanh. Vui lòng tạo thư mục `sample_data/mp3/` và đặt 5 file mp3 theo đúng thứ tự:
- `at1.mp3`
- `at2.mp3`
- `at3.mp3`
- `at4.mp3`
- `at5.mp3`

*(Tương tự cho `.wav` trong `sample_data/wav/`)*

> Để bảo vệ bản quyền và dung lượng, chỉ các tệp mẫu giả lập nhỏ gọn được đưa lên GitHub hoặc được thay thế bằng file `README.md` hướng dẫn.

## 7. Hướng dẫn chạy chương trình (CLI)

Chạy hệ thống thông qua Command Line Interface (CLI):

**1. Khởi tạo Master Key:**
```bash
python -m src.cli keygen
```

**2. Mã hóa và Gửi (Sender):**
```bash
python -m src.cli send sample_data/mp3 --format mp3 --sender alice --receiver bob
```
Lệnh này sẽ trả về ID của kênh truyền (`audio_id`), ví dụ: `output/channel/<audio_id>`.

**3. Nhận và Giải mã (Receiver):**
```bash
python -m src.cli receive output/channel/<audio_id>
```

**4. Xác minh Toàn vẹn (Verify Hash):**
```bash
python -m src.cli verify output/reference/original_reference.mp3 output/receiver/reconstructed.mp3
```

*(Bạn cũng có thể chạy tự động toàn bộ luồng trên bằng script `.\run_demo.ps1`)*

## 8. Hướng dẫn chạy giao diện Web

Khởi động Flask Server:
```bash
flask --app app run
# hoặc
python app.py
```
*(Bạn có thể chạy nhanh bằng lệnh `.\run_web.ps1`)*

Sau đó truy cập trình duyệt tại:
```text
http://127.0.0.1:5000
```
- Trên web, bạn có thể Tải lên trực tiếp 5 file, bấm **Mã hóa và gửi**, sau đó bấm **Giải mã và ghép**. Kết quả Hash và Audio Player sẽ hiển thị ngay trên màn hình.

## 9. Hướng dẫn chạy Test

Hệ thống sử dụng Pytest để chạy các Unit Tests và Security Tests.
```bash
pytest -v
```

## 10. Hướng dẫn chạy Benchmark

Công cụ benchmark sẽ chạy quá trình gửi/nhận nhiều lần để đo đạc thời gian, thông lượng và overhead lưu trữ.
```bash
python -m src.cli benchmark sample_data/mp3 sample_data/wav --iterations 5
```
Kết quả được xuất ra file CSV, JSON và một biểu đồ `benchmark_chart.png` trong `output/benchmark/`.
(Bạn cũng có thể xem trực quan tại chức năng Benchmark trên giao diện Web).

## 11. Các trường hợp kiểm thử bảo mật

Dự án có khả năng đối phó với các cuộc tấn công thông qua các kịch bản mô phỏng. Sử dụng CLI hoặc Web UI để mô phỏng:

- **Missing Segment**: Xóa 1 đoạn mã hóa trên đường truyền.
- **Tampering**: Chỉnh sửa bit trong file bị mã hóa (Dẫn đến hỏng AEAD GCM Auth Tag).
- **Reorder**: Thay đổi thứ tự các file truyền đến Receiver.
- **Duplicate**: Gửi dư file (nhân bản 1 đoạn).
- **Replay Attack**: Gọi nhận file 2 lần cho cùng một Session ID (bị hệ thống Replay Guard từ chối).

## 12. Hình thức kiểm tra hash PASS/FAIL

Khi hoàn tất ghép nối, hệ thống sẽ tự động SHA-256 hash của `reconstructed.mp3` và so sánh với file tham chiếu `original_reference.mp3` (được tạo trước khi chia nhỏ hoặc đại diện cho file ghép hoàn hảo).

- Nếu Hash khớp hoàn toàn: Hiển thị nổi bật trạng thái **`HASH MATCH: PASS`** màu xanh.
- Nếu Hash sai khác (chỉ cần sai 1 bit): Hiển thị trạng thái **`HASH MATCH: FAIL`** màu đỏ. Việc giải mã chỉ được tính là thành công khi qua được lớp kiểm tra này.

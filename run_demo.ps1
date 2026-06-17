$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING="utf-8"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "     SECURE AUDIO SEGMENT TRANSFER" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Kích hoạt môi trường ảo nếu có
if (Test-Path ".\.venv\Scripts\activate.ps1") {
    . ".\.venv\Scripts\activate.ps1"
}

Write-Host "`n[1] Sinh Master Key (Keygen)..." -ForegroundColor Yellow
python -m src.cli keygen

Write-Host "`n[2] Bắt đầu quá trình Sender (Mã hóa và Gửi)..." -ForegroundColor Yellow
python -m src.cli send sample_data/mp3 --format mp3 --sender alice --receiver bob

# Lấy Channel ID mới nhất được tạo
$channel = Get-ChildItem -Path output\channel | Sort-Object CreationTime -Descending | Select-Object -First 1

if ($channel) {
    Write-Host "`n[3] Bắt đầu quá trình Receiver (Nhận và Giải mã) trên kênh: $($channel.Name)" -ForegroundColor Yellow
    python -m src.cli receive output\channel\$($channel.Name)

    Write-Host "`n[4] Xác minh tính toàn vẹn (Verify Hash)..." -ForegroundColor Yellow
    python -m src.cli verify output\reference\original_reference.mp3 output\receiver\reconstructed.mp3
} else {
    Write-Host "Không tìm thấy kênh truyền nào trong output\channel!" -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Cyan
Write-Host "             HOÀN TẤT DEMO" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

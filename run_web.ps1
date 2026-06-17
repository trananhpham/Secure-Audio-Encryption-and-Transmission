$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING="utf-8"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "     SECURE AUDIO SEGMENT TRANSFER WEB" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Kích hoạt môi trường ảo nếu có
if (Test-Path ".\.venv\Scripts\activate.ps1") {
    . ".\.venv\Scripts\activate.ps1"
}

Write-Host "Khởi động Server tại http://127.0.0.1:5000 ..." -ForegroundColor Yellow
python app.py

# Inheritance & Upgrade
Dự án được thiết kế theo module:
- Crypto: Dễ dàng thay thế AES-GCM bằng ChaCha20.
- Audio: Hỗ trợ linh hoạt MP3 và WAV.
- Protocol: Manifest có `manifest_version` để nâng cấp schema trong tương lai.

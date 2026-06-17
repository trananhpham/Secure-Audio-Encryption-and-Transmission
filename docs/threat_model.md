# Threat Model

1. **Eavesdropping**: Kẻ tấn công đọc trộm nội dung âm thanh.
   - *Mitigation*: Mã hóa AES-256-GCM.
2. **Tampering**: Sửa đổi nội dung đoạn âm thanh.
   - *Mitigation*: AES-GCM Authentication Tag và HMAC-SHA256 cho manifest.
3. **Reordering**: Đảo thứ tự gửi/nhận.
   - *Mitigation*: Sequence number trong AAD và kiểm tra từ manifest.
4. **Replay Attack**: Gửi lại các gói đã nhận.
   - *Mitigation*: Session_id, Segment_id và SQLite Replay Guard.

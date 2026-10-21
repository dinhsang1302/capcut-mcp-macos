# Repository dành riêng cho macOS

Đọc README trước khi cài. Không ghép mã hoặc script Windows vào repo này và không sửa repo Windows để hỗ trợ Mac.

- Không tuyên bố chạy được trên Mac thật từ kết quả mock test. Mọi đường dẫn ứng viên phải xác minh file thật. Nếu có nhiều kho draft, yêu cầu chỉ định kho đang dùng.
- Chỉ cài ứng dụng/môi trường khi người dùng yêu cầu cài; dùng nguồn chính thức trong README. Không API trả phí, không tắt SIP/Gatekeeper, không tự sửa quyền hệ thống.
- Repo Private: dùng tài khoản đã được cấp quyền; không đưa token vào URL, log hoặc chat. Không tự mời lại tài khoản đã bị thu hồi.
- Cấu hình MCP bằng entry point `.venv/bin/capcut-mcp`. Backup config trước khi đổi; giữ các MCP khác. Không copy venv từ máy khác và không dùng môi trường Python Apple quản lý.
- Bước kiểm tra cài đặt chỉ đọc/probe, không chỉnh hoặc lưu project thật. Không gọi verify_render từ repo khác trên project thật.
- Force save bị cấm. Không biết trạng thái tiến trình thì không được ghi. Nếu draft đã đổi trên ổ đĩa, đọc lại và đánh giá thay vì ghi đè.
- Cần kiểm thử thực tế schema/tài nguyên và vòng thêm chữ/render/discard trên project Mac mẫu trước khi khẳng định tương thích edit. Chỉ lưu bản sao mẫu khi người dùng cho phép.
- Không commit config, project, source media, cache, .venv hoặc credential.

# CapCut MCP dành riêng cho macOS

Repo Private độc lập: **https://github.com/dinhsang1302/capcut-mcp-macos**.

Đây là mã nguồn đã chuyển trực tiếp sang macOS, không phải gói bổ sung cho repo Windows. Tải nguyên repo này để cài trên Mac; không cần tải repo Windows hoặc áp dụng patch/file hỗ trợ bên ngoài. Repo Windows không bị sửa.

**Trạng thái:** đã chuẩn bị mã nguồn native macOS và có kiểm thử bằng fixture/mô phỏng. Chưa chạy trên Mac thật hoặc project CapCut tạo trên Mac; chưa khẳng định tương thích thực tế. Xem mục Kiểm thử bên dưới trước khi sử dụng.

## 1 Trên máy Mac mới cần cài gì

Mở Terminal bằng Spotlight. Kiểm tra kiến trúc và phiên bản hệ điều hành:

```bash
uname -m
sw_vers
```

`arm64` là Apple Silicon; `x86_64` là Intel (hoặc Terminal đang chạy qua Rosetta). Dùng Terminal native nếu có thể. Quy trình dùng Python 3.13 và dependency MCP 2.3.0. Không xóa hoặc thay Python do Apple quản lý.

### Cài Homebrew

Mở **https://brew.sh** và làm theo hướng dẫn cài hiện hành. Đọc kỹ trước khi chạy trình cài; có thể cần mật khẩu quản trị hoặc hoàn tất Command Line Tools. Homebrew có yêu cầu phiên bản macOS riêng, xem https://docs.brew.sh/Installation. Máy không đáp ứng yêu cầu phải dùng bộ cài phù hợp từ nguồn chính thức, không tắt Gatekeeper/SIP để vượt lỗi.

Sau khi cài, thực hiện các lệnh `brew shellenv` mà trình cài in ra. Vị trí thường gặp được Homebrew công bố:

```bash
# Chạy đúng một dòng phù hợp với bản Homebrew đã cài.
# Apple Silicon:
eval "$(/opt/homebrew/bin/brew shellenv)"
# Intel:
# eval "$(/usr/local/bin/brew shellenv)"
brew --version
```

Theo Next steps của Homebrew để lưu shellenv vào cấu hình shell nếu cần, giữ nguyên các dòng có sẵn. Không chạy `sudo brew ...`.

### Cài Python Git FFmpeg và công cụ đăng nhập GitHub

```bash
brew install python@3.13 git ffmpeg gh
"$(brew --prefix python@3.13)/bin/python3.13" --version
git --version
ffmpeg -version
ffprobe -version
gh --version
```

FFprobe đi cùng FFmpeg. Nếu pip báo lỗi chứng chỉ, xem hướng dẫn Python/Homebrew; không dùng `--trusted-host` để bỏ kiểm tra TLS. Có thể dùng bộ cài `.pkg` của Python từ https://www.python.org/downloads/macos/ thay cho Python Homebrew, rồi chạy Install Certificates.command theo tài liệu Python. Chỉ chọn một cách cài Python làm môi trường cho repo.

### Cài Codex và CapCut Desktop

- Codex: tải ứng dụng macOS từ nguồn OpenAI chính thức và đăng nhập tài khoản có quyền dùng Codex. Không cần cài Node.js/Codex CLI để chạy MCP từ ứng dụng.
- CapCut Desktop: tải bản Mac từ https://www.capcut.com/tools/desktop-video-editor và cài vào Applications. Tạo project thử `MCP_SETUP_TEST`, nhập một video local và đưa lên timeline. Chờ lưu rồi **Quit CapCut** bình thường.
- Việc cài CapCut không đảm bảo draft vẫn là JSON thuần. Probe phải xác minh trên từng máy/phiên bản. Nếu macOS chặn quyền đọc Movies hoặc ổ ngoài, cấp đúng quyền ứng dụng cần qua giao diện Settings; không tắt cơ chế bảo mật hoặc tự cấp Full Disk Access hàng loạt.

## 2 Đăng nhập và tải repo Private

Chủ repo phải cấp quyền cho tài khoản GitHub; người được mời cần chấp nhận lời mời trước. Repo có thể trả 404 khi chưa được cấp quyền hoặc đăng nhập sai tài khoản.

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git clone https://github.com/dinhsang1302/capcut-mcp-macos.git "$HOME/capcut-mcp-macos"
cd "$HOME/capcut-mcp-macos"
```

`gh auth setup-git` cấu hình Git dùng credential GitHub CLI cho tài khoản đang đăng nhập. Không đưa token vào URL hoặc dán token vào chat. Nếu không muốn cấu hình helper Git, có thể đăng nhập trình duyệt và tải Code → Download ZIP, rồi mở Terminal tại thư mục đã giải nén. Không clone đè lên thư mục có sẵn và không copy `.venv` từ máy khác.

## 3 Cài và cấu hình trong repo Mac

Đọc `scripts/install.sh` trước khi chạy. Script không tự cài ứng dụng hệ thống, không đổi quyền macOS và không sửa project.

```bash
export CAPCUT_MCP_PYTHON="$(brew --prefix python@3.13)/bin/python3.13"
bash scripts/install.sh --configure-codex
```

Nếu dùng Python từ python.org và `python3.13` đã nhận diện được, không cần biến CAPCUT_MCP_PYTHON. Script tạo `.venv`, cài package, xác nhận tìm được FFmpeg/FFprobe và 35 tools; chỉ với `--configure-codex` mới backup và thêm/sửa section CapCut trong `~/.codex/config.toml`.

Có thể làm từng bước thay cho script:

```bash
"$CAPCUT_MCP_PYTHON" -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python scripts/verify_tools.py
.venv/bin/python scripts/configure_codex.py --exe "$PWD/.venv/bin/capcut-mcp"
```

Với python.org, dùng `python3.13 -m venv .venv` ở dòng đầu. Không cần activate môi trường. Giữ repo ở vị trí cố định; nếu chuyển thư mục, tạo lại môi trường và cập nhật command.

Script cấu hình giữ nguyên MCP khác và các biến môi trường hiện có; đặt command là đường dẫn tuyệt đối của entry point Mac và `args = []`. Có backup trước khi đổi file, parse TOML trước/sau và dừng nếu cấu trúc phức tạp không xử lý chắc chắn. Ví dụ kết quả (thay tên tài khoản thật):

```toml
[mcp_servers.capcut]
command = "/Users/lan/capcut-mcp-macos/.venv/bin/capcut-mcp"
args = []
```

Không dùng `~` hoặc `$HOME` nguyên văn trong command. Không dùng `.exe`, thư mục Scripts hoặc đường dẫn ổ đĩa Windows. Không cần sửa config thật chỉ để chạy bộ unit test.

## 4 Kho project ứng dụng và FFmpeg

Mã Mac đọc `Contents/Info.plist` trong CapCut.app, quét các vị trí ứng dụng thông dụng và xác minh file kho draft. Các đường dẫn Movies/Library trong mã chỉ là **ứng viên**, chưa được quan sát trên Mac thật trong đợt phát triển này. Không tự chọn nếu thấy nhiều kho.

Nếu không tìm được kho, mở CapCut để xác định vị trí lưu thật. Chọn **thư mục chứa root_meta_info.json và các project**, không phải một project con. Backup config trước khi thêm các biến cần thiết:

```toml
[mcp_servers.capcut.env]
CAPCUT_MCP_DRAFT_ROOT = "/Users/lan/duong-dan-that/com.lveditor.draft"
# Chỉ thêm nếu ứng dụng bị đổi tên hoặc đặt ở vị trí khác:
CAPCUT_MCP_APP = "/Applications/CapCut.app"
# Chỉ thêm nếu không tìm thấy FFmpeg tự động:
CAPCUT_MCP_FFMPEG = "/opt/homebrew/bin/ffmpeg"
CAPCUT_MCP_FFPROBE = "/opt/homebrew/bin/ffprobe"
```

Đây là ví dụ, không chép đường dẫn chưa tồn tại. Biến APP trỏ tới gói `.app`; hai biến FFmpeg trỏ tới **file thực thi**, không phải thư mục. Server tự thử `/opt/homebrew/bin` và `/usr/local/bin` khi Codex mở từ Dock không có PATH của shell. Các biến tương đối hoặc file thiếu sẽ báo lỗi thay vì bỏ qua.

Project/source từ Windows hoặc NAS không được tự ánh xạ sang Mac. Cần có media thật đã mount và đường dẫn đúng; không sửa hàng loạt đường dẫn khi chưa được yêu cầu.

## 5 Kiểm tra trên Mac trước khi sửa project

```bash
.venv/bin/python scripts/verify_setup.py
.venv/bin/python scripts/verify_connection.py
```

Lệnh đầu báo khả năng trên Mac. Lệnh sau kiểm tra stdio MCP, liệt kê tools và **chỉ gọi capcut_probe**. Không chỉnh/lưu project. Thành công handshake chưa đồng nghĩa draft tương thích: xem đầy đủ warning và các trường:

- `supported_platform: true` và `process_check_ok: true`.
- `running_pids: []` khi CapCut đã thoát. `null` nghĩa là chưa xác minh được, không được coi là đã đóng.
- `capcut_version` nhận từ gói `.app`.
- `draft_root` đúng; `plaintext_drafts: true` sau khi đọc một project thử có tracks/materials.
- Có cả `ffmpeg` và `ffprobe`.

Thoát rồi mở lại Codex và gửi:

```text
Dùng CapCut MCP. Chỉ chạy capcut_probe.
Không chỉnh sửa hoặc lưu project nào.
```

Tiếp theo chỉ đọc timeline của `MCP_SETUP_TEST`. Khi được người dùng cho phép mới test thêm chữ, render frame và discard; chỉ thử lưu trên bản sao project mẫu, rồi mở CapCut xem thực tế. Không dùng project quan trọng làm bài thử đầu tiên.

## 6 Bảo vệ khi lưu và giới hạn hiện tại

- Kiểm tra tiến trình bằng `/bin/ps`. Khi lệnh lỗi, kết quả trống hoặc sai định dạng, hệ thống từ chối ghi. Nhận diện cả tiến trình trong bundle CapCut và helper; Quit ứng dụng bình thường, không tự kill process.
- `force=True` bị từ chối trong bản Mac. Không cho lưu mà bỏ backup. Nếu draft trên ổ đã thay đổi từ lúc đọc hoặc CapCut khởi động trước khi ghi, hủy lưu và yêu cầu đọc lại.
- Backup ở `.mcp_backups` trong project. Không coi backup thay cho việc làm trên bản sao trong lần kiểm thử đầu.
- Không có font khả dụng thì preview chữ báo lỗi, không âm thầm bỏ chữ. Denoise không tự bật khi không có model thật.
- Chưa xác nhận schema và các companion material của CapCut macOS. Đọc được JSON chưa đủ chứng minh mọi edit tương thích. Hiệu ứng riêng cần tài nguyên đã dùng trên chính máy Mac; không tái sử dụng cache đường dẫn từ Windows.
- Preview FFmpeg không tái hiện đầy đủ hiệu ứng/transition/filter riêng của CapCut. Không tự động export bản cuối qua CapCut.

## 7 Prompt giao agent cài máy Mac mới

```text
Hãy cài repo Private https://github.com/dinhsang1302/capcut-mcp-macos
trên Mac này. Đọc README.md và AGENTS.md trước.
Kiểm tra macOS/kiến trúc máy và phần mềm hiện có. Theo nguồn chính thức
trong README để cài Homebrew, Python 3.13, Git, FFmpeg/FFprobe, GitHub CLI
còn thiếu. Hướng dẫn tôi đăng nhập GitHub và chấp nhận lời mời repo.
Cài Codex và CapCut Desktop nếu thiếu, báo các bước giao diện cần tôi làm.
Clone đúng repo Mac, chạy installer native của repo và cấu hình MCP.
Backup config trước khi sửa, giữ MCP khác và kiểm tra TOML.
Không đổi quyền hệ thống, tắt Gatekeeper/SIP, dùng force save hoặc sửa
project thật để thử cài. Chạy probe, báo lỗi thật và phần chưa xác minh.
```

## 8 Kiểm thử và tình trạng bàn giao

Các bài test chạy bằng fixture ở thư mục tạm: plist ứng dụng, đường dẫn kho draft, danh sách tiến trình macOS mô phỏng, fail-closed khi không biết trạng thái, backup/xung đột file, sửa chữ trong bộ nhớ và cấu hình TOML. Chạy:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

Kết quả ngày 21 tháng 10 năm 2026: **24 unit test qua** trên Python 3.13.14 ở Windows x64; build wheel thành công; import server/list_tools đăng ký đủ **35 tools**; cú pháp Bash hợp lệ và installer từ chối host không phải macOS. Không sửa/lưu project thật hay config người dùng trong các bài thử.

Đợt phát triển diễn ra trên Windows. Các bài kiểm tra logic không thay thế macOS: chưa chạy Homebrew, nhánh cài đặt thực của installer trên Mac, `/bin/ps` thật, handshake server Mac hoặc lưu/mở một project Mac thật. README không coi các phần này là đã đạt. Cần probe và kiểm thử project mẫu trên Mac của người dùng trước khi dựng thật.

## Nguồn và giấy phép

- [Homebrew và vị trí cài Apple Silicon Intel](https://brew.sh), [yêu cầu cài Homebrew](https://docs.brew.sh/Installation).
- [Python trên macOS](https://docs.python.org/3/using/mac.html), [Git trên macOS](https://git-scm.com/install/mac), [FFmpeg](https://ffmpeg.org/download.html).
- [MCP trong Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), [CapCut Desktop](https://www.capcut.com/tools/desktop-video-editor).
- Dựa trên snapshot CapCut MCP của Henri8 đã lưu local; giữ nguyên [LICENSE](LICENSE) MIT. Phần discovery, kiểm tra tiến trình, font và installer được chuyển trực tiếp sang macOS ở repo này. Không khẳng định repo nguồn cũ hiện truy cập được.

Repo Private chỉ hạn chế tải/cập nhật từ GitHub. Người đã có bản local vẫn sử dụng được sau khi thu hồi quyền; đây không phải hệ thống license/kích hoạt theo máy.

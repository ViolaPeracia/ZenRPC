# Discord RPC Watcher 🎮

App chạy nền trên Windows, tự detect cửa sổ đang dùng và hiện lên Discord Rich Presence.

---

## Cài đặt

### Bước 1 — Tạo Discord Application

1. Vào https://discord.com/developers/applications
2. Nhấn **New Application** → đặt tên (VD: "My PC")
3. Copy **Application ID** (chính là Client ID)

### Bước 2 — Điền Client ID

Mở `config.json`, thay `YOUR_CLIENT_ID_HERE` bằng ID vừa copy:

```json
{
  "client_id": "1234567890123456789",
  ...
}
```

### Bước 3 — Chạy app

Double-click `run.bat` → app sẽ tự cài thư viện và chạy nền.

Icon hình tròn màu tím sẽ xuất hiện ở **System Tray** (góc dưới phải).

---

## Cấu hình

Chỉnh `config.json` theo ý muốn:

| Key | Mô tả |
|-----|-------|
| `client_id` | ID của Discord App |
| `update_interval` | Tần suất cập nhật (giây, tối thiểu 15) |
| `show_window_title` | Hiện tiêu đề cửa sổ lên Discord |
| `custom_mappings` | Map tên process → tên đẹp + icon |

### Thêm app mới vào mappings

```json
"obs64.exe": {
  "name": "OBS Studio",
  "icon": "obs",
  "detail": "Đang stream 📡"
}
```

> **Lưu ý**: `icon` phải là key ảnh đã upload trong Discord Developer Portal.
> Nếu không có icon riêng, để `"default"` là được.

---

## Tray Menu

Chuột phải vào icon:
- **▶/■ Bật/Tắt RPC** — bật hoặc tắt tạm thời
- **⚙ Mở config.json** — chỉnh cấu hình
- **✕ Thoát** — đóng hoàn toàn

---

## Yêu cầu

- Windows 10/11
- Python 3.8+
- Discord Desktop App (bản web/mobile không support RPC)

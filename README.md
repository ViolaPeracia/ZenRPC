# Discord RPC Watcher

App chạy nền trên Windows, tự detect cửa sổ đang dùng và hiện lên Discord Rich Presence.

## Yêu cầu

- Windows 10/11
- Python 3.8+
- Discord Desktop App (bản web/mobile không support RPC)

---

## Cài đặt

### Bước 1 — Tạo Discord Application

1. Vào https://discord.com/developers/applications
2. Nhấn **New Application** → đặt tên bất kỳ (VD: "My PC")
3. Copy **Application ID** (chính là Client ID)

### Bước 2 — Điền Client ID

M�� `config.json`, thay `YOUR_CLIENT_ID_HERE`:

```json
{
  "client_id": "1234567890123456789"
}
```

### Bước 3 — Cài thư viện

Double-click `install.bat` → đợi cài xong.

### Bước 4 — Chạy

Double-click `run.bat` → icon tròn màu tím xuất hiện ở System Tray góc dưới phải.

---

## Cấu hình

Chỉnh `config.json` theo ý muốn:

| Key | Mô tả | Mặc định |
|-----|-------|----------|
| `client_id` | Application ID từ Discord Developer Portal | bắt buộc |
| `update_interval` | Tần suất cập nhật (giây, tối thiểu 15) | `15` |
| `reconnect_delay` | Thời gian chờ trước khi thử kết nối lại (giây) | `30` |
| `show_window_title` | Hiện tiêu đề cửa sổ đang mở lên Discord | `true` |
| `clear_on_idle` | Xóa presence khi không có window active | `true` |
| `custom_mappings` | Map tên process → tên hiển thị + icon + detail | xem bên dưới |

### Thêm app mới

M�� `config.json`, thêm vào `custom_mappings`:

```json
"obs64.exe": {
    "name": "OBS Studio",
    "icon": "obs",
    "detail": "Dang stream"
}
```

Tên key (`obs64.exe`) phải là tên process chính xác — tìm trong **Task Manager → tab Details**.

Sau khi thêm, bấm **Reload config** từ tray menu để áp dụng ngay mà không cần restart.

### Thêm icon

Discord RPC chỉ nhận icon đã upload lên **Art Assets** trong Developer Portal:

1. Vào https://discord.com/developers/applications → chọn app
2. Sidebar → **Rich Presence** → **Art Assets**
3. Upload ảnh PNG (khuyến nghị 512x512) → đặt tên key khớp với `"icon"` trong config

Nguồn ảnh icon: https://simpleicons.org hoặc https://icon-icons.com

---

## Tray Menu

Chuột phải vào icon:

| Menu | Chức năng |
|------|-----------|
| Bat/Tat RPC | Bật hoặc tắt RPC tạm thời |
| Khoa app hien tai | Giữ nguyên app hiện tại dù chuyển sang cửa sổ khác |
| Mo khoa | Quay về chế độ tự động theo dõi |
| Reload config | Áp dụng thay đổi config mà không cần restart |
| Mo config.json | Mở file config bằng Notepad |
| Thoat | Đóng app hoàn toàn |

Khi đang lock, icon tray đổi sang **màu đỏ**.

---

## License

GPL v3 — xem file [LICENSE](LICENSE).

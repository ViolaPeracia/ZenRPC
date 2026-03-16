# Discord RPC Watcher

A lightweight tray app that detects your active window and displays it on Discord Rich Presence — available for both Windows and Linux.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-GPL%20v3-green)

---

## Preview

> Your Discord profile will show what app you are currently using, with the window title and how long you have been using it.

---

## Features

- Detects active window and updates Discord presence automatically
- Lock mode — keep showing a specific app even when you switch windows
- Idle detection — clears presence when no window is active
- Reload config without restarting
- Tray icon with red/purple indicator for lock state
- Fully configurable via `config.json`

---

## Download

Choose your platform:

| Platform | Folder |
|----------|--------|
| Windows 10/11 | [`/windows`](./windows) |
| Ubuntu / Debian | [`/linux`](./linux) |

---

## Quick Start

### Windows

1. Go to the [`/windows`](./windows) folder
2. Download all files
3. Run `install.bat` to install dependencies
4. Edit `config.json` and set your `client_id`
5. Run `run.bat`

### Linux

1. Go to the [`/linux`](./linux) folder
2. Download all files
3. Run the installer:
```bash
chmod +x install.sh
./install.sh
```
4. Edit `config.json` and set your `client_id`
5. Run:
```bash
python3 main.py
```

---

## Getting a Client ID

1. Go to https://discord.com/developers/applications
2. Click **New Application** and give it any name
3. Copy the **Application ID** — this is your `client_id`
4. Paste it into `config.json`

---

## Configuration

Both versions share the same `config.json` format:

```json
{
  "client_id": "YOUR_CLIENT_ID_HERE",
  "update_interval": 15,
  "reconnect_delay": 30,
  "show_window_title": true,
  "clear_on_idle": true,
  "custom_mappings": {
    "chrome.exe": {
      "name": "Google Chrome",
      "icon": "chrome",
      "detail": "Browsing the web"
    }
  }
}
```

| Key | Description | Default |
|-----|-------------|---------|
| `client_id` | Your Discord Application ID | required |
| `update_interval` | Presence update frequency in seconds (min 15) | `15` |
| `reconnect_delay` | Seconds to wait before reconnecting after disconnect | `30` |
| `show_window_title` | Show the active window title on Discord | `true` |
| `clear_on_idle` | Clear presence when no window is active | `true` |
| `custom_mappings` | Map process names to display info | see below |

### Adding a new app

Add an entry to `custom_mappings`:

```json
"obs64.exe": {
  "name": "OBS Studio",
  "icon": "obs",
  "detail": "Streaming"
}
```

> **Note:** On Windows use the `.exe` name (e.g. `chrome.exe`). On Linux use the process name without extension (e.g. `chrome`).
>
> Find the process name on Windows via **Task Manager -> Details tab**, on Linux run:
> ```bash
> xdotool getactivewindow getwindowpid | xargs -I{} cat /proc/{}/comm
> ```

After editing, click **Reload config** from the tray menu — no restart needed.

---

## Adding Icons

Discord RPC only accepts icons uploaded to your Developer Portal:

1. Go to https://discord.com/developers/applications -> select your app
2. Sidebar -> **Rich Presence** -> **Art Assets**
3. Upload a PNG (512x512 recommended) and set the key name to match `"icon"` in your config

Icon sources: [simpleicons.org](https://simpleicons.org) and [icon-icons.com](https://icon-icons.com)

---

## Tray Menu

Right-click the tray icon:

| Option | Description |
|--------|-------------|
| Enable / Disable RPC | Toggle presence on or off |
| Lock current app | Keep showing current app even when switching windows |
| Unlock | Return to auto-detect mode |
| Reload config | Apply config changes without restarting |
| Open config | Open `config.json` |
| Quit | Exit the app |

When **locked**, the tray icon turns **red**.

---

## Requirements

### Windows
- Windows 10/11
- Python 3.8+
- Discord Desktop App

### Linux
- Ubuntu / Debian (or any distro with apt)
- Python 3.8+
- X11 (Wayland supported via XWayland)
- Discord Desktop App

---

## License

This project is licensed under the **GNU General Public License v3.0** — see the [LICENSE](LICENSE) file for details.

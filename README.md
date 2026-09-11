# Discord RPC Watcher

A lightweight desktop tray app that detects your active window and displays it on Discord Rich Presence — unified for both Windows and Linux.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-AGPL%20v3-orange)

---

## Features

- **Active Application Detection:** Automatically updates Discord presence with the currently active application and window title.
- **Per-Application Elapsed Time:** The activity timer resets when switching to a different application, but stays continuous when switching tabs or files within the same app.
- **Resilient Auto-Reconnect:** The watcher starts and remains alive even if Discord is not yet running, reconnecting automatically whenever Discord opens.
- **Lock Mode:** Keep showing a specific app on Discord even while switching to other tasks.
- **Idle Detection:** Clears presence automatically when no application window is active.
- **Live Configuration Reload:** Edit `config.json` and reload immediately from the tray menu without restarting.
- **Tray Status Indicator:** Visual tray icon (Blurple for active presence, Red for locked mode).

---

## Quick Start

### Windows

1. Clone or download this repository.
2. Run `install.bat` (or `pip install -r requirements.txt`).
3. Copy `config.example.json` to `config.json` (created automatically on first run) and enter your Discord `client_id`.
4. Run `run.bat` (or `pythonw main.py` for silent background execution).

### Linux

1. Clone or download this repository.
2. Install system dependency for X11 window detection:
   ```bash
   sudo apt install xdotool   # Debian / Ubuntu
   # or: sudo pacman -S xdotool  # Arch Linux
   ```
3. Run the installer:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
4. Edit `config.json` with your Discord `client_id`.
5. Run:
   ```bash
   python3 main.py
   ```

---

## Getting a Client ID

1. Go to [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and choose any name (e.g. "My Desktop").
3. Copy the **Application ID** — this is your `client_id`.
4. Paste it into your local `config.json`.

---

## Configuration

Settings are stored in `config.json` next to `main.py` (`config.example.json` is provided as a template):

```json
{
  "client_id": "YOUR_CLIENT_ID_HERE",
  "update_interval": 15,
  "reconnect_delay": 30,
  "show_window_title": true,
  "clear_on_idle": true,
  "custom_mappings": {
    "Code.exe": {
      "name": "Visual Studio Code",
      "icon": "vscode",
      "detail": "Editing code"
    },
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
| `client_id` | Application ID from Discord Developer Portal | `YOUR_CLIENT_ID_HERE` |
| `update_interval` | Presence update frequency in seconds (minimum `15` to respect Discord rate limits) | `15` |
| `reconnect_delay` | Seconds to wait before attempting reconnection when Discord closes | `30` |
| `show_window_title` | Display the active window title in Discord state | `true` |
| `clear_on_idle` | Clear presence when no window is active | `true` |
| `custom_mappings` | Map process names to custom display names, icons, and activity descriptions | see `config.example.json` |

### Built-in Recognized Applications

The watcher includes 28 built-in recognition rules covering 14 popular desktop applications across Windows and Linux:

| Application | Process Names | Discord Asset Key | Default Activity |
| :--- | :--- | :--- | :--- |
| **Visual Studio Code** | `Code.exe`, `code` | `vscode` | Editing code / Coding |
| **Google Chrome** | `chrome.exe`, `chrome`, `google-chrome` | `chrome` | Browsing the web / Browsing |
| **Mozilla Firefox** | `firefox.exe`, `firefox` | `firefox` | Browsing the web / Browsing |
| **Discord** | `discord.exe`, `discord` | `discord` | Chatting |
| **Notepad / Text Editor** | `notepad.exe`, `gedit` | `notepad` | Writing |
| **File Explorer / Files** | `explorer.exe`, `nautilus` | `explorer` | Viewing files / Browsing files |
| **Adobe Photoshop** | `Photoshop.exe`, `photoshop` | `photoshop` | Editing images |
| **GIMP** | `gimp` | `gimp` | Editing image |
| **VLC Media Player** | `vlc.exe`, `vlc` | `vlc` | Watching video |
| **Spotify** | `spotify.exe`, `spotify` | `spotify` | Listening to music |
| **Steam** | `steam.exe`, `steam` | `steam` | Playing games / Gaming |
| **OBS Studio** | `obs64.exe`, `obs` | `obs` | Streaming |
| **Zed** | `zed.exe`, `zed` | `zed` | Editing code |
| **Terminal** | `terminal`, `gnome-terminal`, `konsole` | `terminal` | In terminal |

Unrecognized applications automatically fall back to `"Using <process_name>"` without crashing.

### Custom Application Mappings

Add an entry to `custom_mappings` in `config.json` to customize existing apps or add new ones:

```json
"obs64.exe": {
  "name": "OBS Studio",
  "icon": "obs",
  "detail": "Streaming"
}
```

> **Tip:** You can define both Windows (`.exe`) and Linux process names in `custom_mappings`. The matcher checks exact names, lowercase names, and names without `.exe` automatically. User custom mappings automatically merge with built-in defaults without losing standard rules.

After editing, right-click the tray icon and select **Reload config** — changes take effect immediately.


---

## Platform Support & Limitations

### Windows
- Windows 10/11 supported out of the box using Win32 API and `psutil`.

### Linux
- **X11:** Fully supported via `xdotool` with strict timeouts. Process names are read directly from `/proc/<pid>/cmdline`.
- **XWayland:** Applications running through XWayland are detectable via existing X11 tools.
- **Native Wayland:** Wayland's security architecture intentionally prevents arbitrary unprivileged applications from querying other windows. On pure Wayland sessions without XWayland, the application will degrade gracefully to an idle state rather than crashing.

---

## Tray Menu

Right-click the tray icon:

| Option | Description |
|--------|-------------|
| Enable / Disable RPC | Toggle presence updates on or off |
| Lock current app / Unlock | Keep broadcasting the current app even when switching windows |
| Reload config | Apply changes made in `config.json` without restarting |
| Open config.json | Open `config.json` in your default text editor |
| Quit | Cleanly disconnect and exit the application |

---

## Development & Testing

Run unit tests offline without requiring Discord or a graphical display:

```bash
pytest
```

---

## Development Roadmap

The project follows a focused, platform-prioritized development roadmap:

1. **Windows Stabilization & Baseline (Active Focus):**
   - **`M2.6-W`:** Active-window Win32 detector hardening, offline mock unit tests, launcher independence, and mapping parity.
   - **`M2.7-W`:** Windows end-to-end verification checklist, documentation audit, and stable source release gate.
2. **Linux Stabilization & Baseline (Planned Follow-up):**
   - **`M3-L`:** `/proc/<pid>/cmdline` parsing reliability, subprocess timeout safety tests, desktop launcher validation, and Wayland graceful degradation.
3. **Optional Cross-Platform Enhancements (Deferred):**
   - **`M4`:** Native Wayland compositor IPC, local privacy filtering, rotating local file logging, and standalone packaging.

For architecture principles, detailed issue breakdowns, and task status, see [`docs/ROADMAP.md`](docs/ROADMAP.md) and the [GitHub Milestones](https://github.com/githubuser2777/discord-rpc/milestones).

---

## License

This project includes the [GNU Affero General Public License v3.0](LICENSE).
*(Note: If you are the repository owner, verify whether AGPL-3.0 or GPL-3.0 is your intended license).*

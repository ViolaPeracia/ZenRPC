# Discord RPC Watcher — Linux

Tray app for Linux that detects your active window and shows it on Discord Rich Presence.

## Requirements

- Ubuntu/Debian (or any distro with apt)
- Python 3.8+
- X11 or Wayland (X11 recommended for best compatibility)
- Discord Desktop App

## Setup

### Step 1 — Create a Discord Application

1. Go to https://discord.com/developers/applications
2. Click **New Application** and give it a name
3. Copy the **Application ID** (Client ID)

### Step 2 — Install

```bash
chmod +x install.sh
./install.sh
```

### Step 3 — Set Client ID

```bash
nano config.json
```

Replace `YOUR_CLIENT_ID_HERE` with your Application ID.

### Step 4 — Run

```bash
python3 main.py
```

A tray icon will appear in the system tray.

---

## Autostart on login

To run automatically on login, copy the desktop file:

```bash
mkdir -p ~/.config/autostart
cp discord-rpc.desktop ~/.config/autostart/
# Edit the path to match where you placed the files
nano ~/.config/autostart/discord-rpc.desktop
```

---

## Configuration

Same as Windows version — edit `config.json`:

| Key | Description | Default |
|-----|-------------|---------|
| `client_id` | Application ID from Discord Developer Portal | required |
| `update_interval` | Update frequency in seconds (min 15) | `15` |
| `reconnect_delay` | Seconds to wait before reconnecting | `30` |
| `show_window_title` | Show active window title on Discord | `true` |
| `clear_on_idle` | Clear presence when no window is active | `true` |
| `custom_mappings` | Map process names to display info | see below |

### Adding a new app

```json
"obs": {
    "name": "OBS Studio",
    "icon": "obs",
    "detail": "Streaming"
}
```

Note: on Linux, process names are usually **lowercase without .exe** (e.g. `code`, `chrome`, `vlc`).

Find the process name with:
```bash
xdotool getactivewindow getwindowpid | xargs -I{} cat /proc/{}/comm
```

---

## Tray Menu

Right-click the tray icon:

| Option | Description |
|--------|-------------|
| Enable/Disable RPC | Toggle RPC on or off |
| Lock current app | Keep showing current app even when switching windows |
| Unlock | Return to auto-detect mode |
| Reload config | Apply config changes without restarting |
| Open config | Open config.json |
| Quit | Exit the app |

---

## Wayland note

Active window detection requires `xdotool` which works on X11.
On Wayland, install `xdg-desktop-portal` and run Discord under XWayland for best results:

```bash
DISCORD_DISABLE_GPU=1 discord &
```

---

## License

GPL v3 — see [LICENSE](../LICENSE).

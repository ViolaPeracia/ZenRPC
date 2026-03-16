# Discord RPC Watcher

A lightweight Windows tray app that detects your active window and displays it on Discord Rich Presence.

## Requirements

- Windows 10/11
- Python 3.8+
- Discord Desktop App (web/mobile does not support RPC)

---

## Setup

### Step 1 — Create a Discord Application

1. Go to https://discord.com/developers/applications
2. Click **New Application** and give it a name (e.g. "My PC")
3. Copy the **Application ID** (this is your Client ID)

### Step 2 — Set your Client ID

Open `config.json` and replace `YOUR_CLIENT_ID_HERE`:

```json
{
  "client_id": "1234567890123456789"
}
```

### Step 3 — Install dependencies

Double-click `install.bat` and wait for it to finish.

### Step 4 — Run

Double-click `run.bat`. A purple circle icon will appear in the System Tray (bottom right).

---

## Configuration

Edit `config.json` to customize behavior:

| Key | Description | Default |
|-----|-------------|---------|
| `client_id` | Application ID from Discord Developer Portal | required |
| `update_interval` | How often to update presence (seconds, min 15) | `15` |
| `reconnect_delay` | How long to wait before retrying connection (seconds) | `30` |
| `show_window_title` | Show the active window title on Discord | `true` |
| `clear_on_idle` | Clear presence when no window is active | `true` |
| `custom_mappings` | Map process names to display info | see below |

### Adding a new app

Add an entry to `custom_mappings` in `config.json`:

```json
"obs64.exe": {
    "name": "OBS Studio",
    "icon": "obs",
    "detail": "Streaming"
}
```

The key (`obs64.exe`) must be the exact process name — find it in **Task Manager &#8594; Details tab**.

After editing, click **Reload config** from the tray menu to apply changes without restarting.

### Adding icons

Discord RPC only accepts icons uploaded to the **Art Assets** section of your Developer Portal:

1. Go to https://discord.com/developers/applications and select your app
2. Sidebar &#8594; **Rich Presence** &#8594; **Art Assets**
3. Upload a PNG image (512x512 recommended) and set the key name to match `"icon"` in your config

Icon sources: https://simpleicons.org or https://icon-icons.com

---

## Tray Menu

Right-click the tray icon:

| Option | Description |
|--------|-------------|
| Bat/Tat RPC | Toggle RPC on or off |
| Khoa app hien tai | Lock current app — keeps showing it even when you switch windows |
| Mo khoa | Unlock and return to auto-detect mode |
| Reload config | Apply config changes without restarting |
| Mo config.json | Open config file in Notepad |
| Thoat | Exit the app |

When locked, the tray icon turns **red**.

---

## License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE) file for details.

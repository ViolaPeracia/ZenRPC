# ZenRPC

A personal, lightweight desktop background utility that automatically detects your currently active application and broadcasts it to your Discord profile via Rich Presence — seamlessly unified across Windows and Linux.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-GPL%20v3-blue)

---

## 🌟 Overview

**ZenRPC** sits quietly in your system tray and monitors what window or application you are actively focused on. Whether you are coding in VS Code, browsing research in Firefox, drawing in Photoshop, listening to Spotify, or working in the terminal, it dynamically updates your Discord status with matching icons, activity details, and clean elapsed timers.

### Key Highlights

- 🪶 **Ultra Lightweight:** Written in pure Python using native platform APIs (`win32gui` on Windows, `xdotool` / `/proc` on Linux). Zero Electron bloat, minimal memory footprint (< 25 MB RAM).
- 🔄 **Resilient Background Reconnect:** Starts and stays alive even if Discord is not yet running. Reconnects automatically whenever Discord starts or restarts.
- ⏱️ **Smart Per-Application Elapsed Timers:** The activity timer resets cleanly when switching between different applications (e.g. Chrome → VS Code), but stays continuous when switching tabs, files, or documents within the same application.
- 🔒 **Instant Lock Mode:** Working on documentation or reading a guide, but still want Discord to show you are "Editing code" in VS Code? Right-click the tray icon and lock presence to your current app.
- 🌙 **Idle Detection:** Automatically clears your Discord status when no application window is active or when you step away.
- ⚡ **Hot Configuration Reload:** Modify application names, icons, or activity descriptions in `config.json` and reload immediately from the tray icon without restarting.
- 🎨 **Visual Tray Indicator:** Dynamic tray icon displays **Blurple** for active broadcasting and turns **Red** when Lock Mode is engaged.

---

## 🚀 Getting Started

### Step 1 — Get a Discord Client ID

To display rich presence on Discord, you need a free Discord Application ID:

1. Visit the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** in the top-right corner.
3. Give your application a name (e.g., *Desktop Activity*, *My Workstation*). This name appears as the top header on your Discord profile card.
4. Copy the **Application ID** from the *General Information* tab. This is your `client_id`.

---

### Step 2 — Installation & Launch

#### 🪟 Windows Setup

1. **Clone or download** this repository:
   ```bash
   git clone https://github.com/githubuser2777/ZenRPC.git
   cd ZenRPC
   ```
2. **Install dependencies:**
   Double-click `install.bat` (or run `pip install -r requirements.txt` in your terminal or virtual environment).
3. **Configure your Client ID:**
   Open `config.json` (auto-generated from `config.example.json` on first run) and paste your `client_id`:
   ```json
   {
     "client_id": "YOUR_DISCORD_APPLICATION_ID_HERE"
   }
   ```
4. **Start ZenRPC:**
   - **Silent Background Mode:** Double-click `run.bat` (runs unobtrusively in the system tray via `pythonw.exe`).
   - **Terminal / Debug Mode:** Run `python main.py` in your terminal to view real-time detection logs.
5. *(Optional)* **Run at Windows Startup:**
   Press `Win + R`, type `shell:startup`, and press Enter. Place a shortcut to `run.bat` into this folder.

---

#### 🐧 Linux Setup

1. **Install system requirement** for X11 active-window inspection:
   ```bash
   sudo apt install xdotool         # Debian / Ubuntu / Mint
   # or: sudo pacman -S xdotool    # Arch Linux / Manjaro
   # or: sudo dnf install xdotool   # Fedora
   ```
2. **Run the installer:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
3. **Configure your Client ID:**
   Edit `config.json` and enter your Discord `client_id`.
4. **Start ZenRPC:**
    ```bash
    python3 main.py
    ```
 5. *(Optional)* **Desktop Menu Integration:**
    Copy `zenrpc.desktop` to `~/.local/share/applications/` to launch from your desktop application launcher.

---

## 🖥️ System Tray Controls

Once running, **ZenRPC** lives in your system tray (notification area). Right-click the icon to access quick controls:

| Menu Action | Description |
| :--- | :--- |
| **Enable RPC / Disable RPC** | Toggle presence broadcasting on or off on the fly without closing the app. |
| **Lock current app / Unlock** | Freeze presence to the active app so you can multitask without changing your status. |
| **Reload config** | Immediately apply edits made to `config.json` without restarting. |
| **Open config.json** | Open `config.json` in your operating system's default text editor. |
| **Quit** | Gracefully disconnect from Discord RPC, clear presence, and exit. |

### Tray Icon Status Colors

- 🟣 **Blurple Circle:** Active & broadcasting foreground window presence.
- 🔴 **Red Circle:** Locked mode active (displaying frozen application).

---

## 📦 Supported Applications Out of the Box

ZenRPC includes 97 built-in recognition rules covering 39 popular desktop applications across Windows and Linux, complete with matching 512×512 art assets in `assets/art_assets/`:

### 💻 Modern AI & Code Editors
| Application | Process Names | Discord Asset Key | Default Activity Text |
| :--- | :--- | :--- | :--- |
| **Cursor** | `Cursor.exe`, `cursor` | `cursor` | Editing code |
| **Windsurf IDE** | `Windsurf.exe`, `windsurf` | `windsurf` | Editing code |
| **Visual Studio Code** | `Code.exe`, `code` | `vscode` | Editing code / Coding |
| **Zed** | `zed.exe`, `zed` | `zed` | Editing code |
| **Sublime Text** | `sublime_text.exe`, `sublime_text` | `sublime` | Editing code |
| **PyCharm** | `pycharm64.exe`, `pycharm.exe`, `pycharm` | `pycharm` | Editing Python |
| **IntelliJ IDEA** | `idea64.exe`, `idea.exe`, `idea` | `idea` | Writing code |
| **WebStorm** | `webstorm64.exe`, `webstorm.exe`, `webstorm` | `webstorm` | Writing JavaScript |
| **JetBrains Rider** | `rider64.exe`, `rider.exe`, `rider` | `rider` | Developing .NET |
| **Visual Studio IDE** | `devenv.exe`, `devenv` | `visualstudio` | Developing software |
| **Neovim / Vim** | `nvim.exe`, `nvim`, `gvim.exe`, `vim.exe`, `vim` | `neovim` | Editing text |

### 🌐 Web Browsers
| Application | Process Names | Discord Asset Key | Default Activity Text |
| :--- | :--- | :--- | :--- |
| **Google Chrome** | `chrome.exe`, `chrome`, `google-chrome` | `chrome` | Browsing the web / Browsing |
| **Mozilla Firefox** | `firefox.exe`, `firefox` | `firefox` | Browsing the web / Browsing |
| **Microsoft Edge** | `msedge.exe`, `msedge` | `edge` | Browsing the web |
| **Brave Browser** | `brave.exe`, `brave` | `brave` | Browsing the web |
| **Opera & Opera GX** | `opera.exe`, `opera`, `opera_gx.exe` | `opera` | Browsing the web |
| **Arc Browser** | `Arc.exe`, `arc` | `arc` | Browsing the web |
| **Vivaldi** | `vivaldi.exe`, `vivaldi` | `vivaldi` | Browsing the web |

### 💬 Communication & Collaboration
| Application | Process Names | Discord Asset Key | Default Activity Text |
| :--- | :--- | :--- | :--- |
| **Discord** | `discord.exe`, `discord` | `discord` | Chatting |
| **Telegram** | `Telegram.exe`, `telegram-desktop`, `telegram` | `telegram` | Chatting |
| **Zalo** | `Zalo.exe`, `zalo` | `zalo` | Chatting |
| **Slack** | `slack.exe`, `slack` | `slack` | Collaborating |
| **Microsoft Teams** | `ms-teams.exe`, `Teams.exe`, `teams` | `teams` | Meeting & Chatting |

### 🎨 Productivity, Design & Office
| Application | Process Names | Discord Asset Key | Default Activity Text |
| :--- | :--- | :--- | :--- |
| **Notion** | `Notion.exe`, `notion` | `notion` | Organizing notes |
| **Obsidian** | `Obsidian.exe`, `obsidian` | `obsidian` | Writing notes |
| **Figma** | `Figma.exe`, `figma` | `figma` | Designing UI/UX |
| **Blender** | `blender.exe`, `blender` | `blender` | 3D Modeling |
| **Adobe Photoshop** | `Photoshop.exe`, `photoshop` | `photoshop` | Editing images |
| **GIMP** | `gimp`, `gimp-2.10.exe` | `gimp` | Editing image |
| **Microsoft Word** | `WINWORD.EXE`, `winword` | `word` | Writing document |
| **Microsoft Excel** | `EXCEL.EXE`, `excel` | `excel` | Analyzing data |
| **Microsoft PowerPoint** | `POWERPNT.EXE`, `powerpnt` | `powerpoint` | Designing slides |
| **Notepad / Text Editor** | `notepad.exe`, `gedit` | `notepad` | Writing |
| **File Explorer / Files** | `explorer.exe`, `nautilus` | `explorer` | Viewing files / Browsing files |

### 🎮 Media, Gaming & System Tools
| Application | Process Names | Discord Asset Key | Default Activity Text |
| :--- | :--- | :--- | :--- |
| **VLC Media Player** | `vlc.exe`, `vlc` | `vlc` | Watching video |
| **Spotify** | `spotify.exe`, `spotify` | `spotify` | Listening to music |
| **Steam** | `steam.exe`, `steam` | `steam` | Playing games / Gaming |
| **OBS Studio** | `obs64.exe`, `obs` | `obs` | Streaming |
| **System Terminal** | `WindowsTerminal.exe`, `pwsh.exe`, `powershell.exe`, `cmd.exe`, `terminal`, `gnome-terminal`, `konsole` | `terminal` | In terminal / In PowerShell / In Command Prompt |

> **Unrecognized Applications:** Any application not listed above automatically falls back to displaying `Using <process_name>` with the active window title, without crashing or failing.

---

## 🖼️ Setting Up Discord Art Assets (Developer Portal Guide)

### Why Don't Icons Appear by Default?
Discord Rich Presence operates on an **isolated application model**. When ZenRPC broadcasts presence, it tells Discord:
```json
{
  "assets": {
    "large_image": "vscode",
    "large_text": "Visual Studio Code"
  }
}
```
Discord does **not** fetch third-party icons from the web automatically. Instead, it looks up the key `"vscode"` inside the **Art Assets** uploaded to your specific Application ID. If your Application has no assets uploaded under that key, Discord renders the activity text but leaves the icon slot empty.

To make icons appear on your profile, you simply upload the matching icon files provided in this repository to your Discord Application.

### Step-by-Step Walkthrough

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and log in.
2. Select your Application (the one matching the `client_id` in your `config.json`).
3. In the left sidebar, navigate to **Rich Presence** → **Art Assets**.
4. Click **Add Image(s)**.
5. Select the icons from the [`assets/art_assets/`](assets/art_assets/) folder in this repository:
   * Every file is pre-normalized to **512 × 512 PNG** with transparency.
   * **Crucial:** Ensure the **Asset Name** in Discord exactly matches the file's base name (e.g. name `vscode.png` as `vscode`, `chrome.png` as `chrome`, `edge.png` as `edge`).
6. Click **Save Changes** at the bottom of the page.

> [!NOTE]
> **CDN Propagation:** Discord caches art assets across global CDN servers. It may take **2 to 10 minutes** after saving before newly uploaded assets appear on your active profile card.

### Technical Note: Art Assets vs. External Image URLs
During investigation of Discord Rich Presence capabilities, Discord client RPC does permit passing raw HTTPS URLs into `large_image`. However, external URLs introduce several significant drawbacks:
* They require public image hosting with valid CORS and direct image MIME types.
* They trigger rate-limiting or thumbnail proxying delays through Discord's media proxy (`mp:external/...`).
* If the external host experiences downtime or network blocking, the presence icon silently breaks.

Uploading assets directly to the **Discord Developer Portal** remains the official, zero-latency, and 100% reliable standard for desktop Rich Presence. For asset provenance, licenses, and sources, see [`assets/art_assets/SOURCES.md`](assets/art_assets/SOURCES.md).

---

## ⚙️ Configuration & Custom Mappings

Settings are stored in `config.json` in the root repository folder:

```json
{
  "client_id": "YOUR_CLIENT_ID_HERE",
  "update_interval": 15,
  "reconnect_delay": 30,
  "show_window_title": true,
  "clear_on_idle": true,
  "custom_mappings": {
    "blender.exe": {
      "name": "Blender",
      "icon": "blender",
      "detail": "3D Modeling"
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `client_id` | String | `"YOUR_CLIENT_ID_HERE"` | Your Discord Developer Application ID. |
| `update_interval` | Integer | `15` | Polling frequency in seconds (minimum `15` to respect Discord rate limits). |
| `reconnect_delay` | Integer | `30` | Seconds to wait between background reconnection attempts when Discord is closed. |
| `show_window_title` | Boolean | `true` | When `true`, displays the active window title in Discord's presence state. |
| `clear_on_idle` | Boolean | `true` | When `true`, clears status from Discord when no window is active or desktop is idle. |
| `custom_mappings` | Object | `{}` | User-defined mappings that override or add new process recognition rules. |

### Adding Custom Application Mappings

You can add custom mappings for any game, browser, or tool by adding its executable name to `custom_mappings`:

```json
"custom_mappings": {
  "sublime_text.exe": {
    "name": "Sublime Text",
    "icon": "sublime",
    "detail": "Coding"
  }
}
```

- **Case-Insensitive & Extension-Agnostic:** You can define `sublime_text.exe`, `sublime_text`, or `SUBLIME_TEXT.EXE` — the matcher handles case variations and extension stripping automatically.
- **Smart Merging:** User custom mappings merge cleanly with default rules, so adding custom entries never wipes out the built-in application mappings.
- **Discord Art Assets:** To show custom icons, upload art assets matching your `"icon"` key in the Discord Developer Portal under **Rich Presence -> Art Assets**.

---

## 🛡️ Platform Support & Technical Details

- **Windows (10 / 11):** Native active-window tracking using `win32gui`, `win32process`, and `psutil`. Fully isolated from UI freezes.
- **Linux (X11 & XWayland):** Tracked via `xdotool` with strict 2-second subprocess timeouts. Binary names are extracted directly from `/proc/<pid>/cmdline` to avoid the 15-character truncation limit of `/proc/<pid>/comm`.
- **Linux (Native Wayland):** Due to Wayland's security architecture restricting arbitrary inter-client window inspection, the app gracefully degrades to an idle state on pure Wayland sessions without crashing.

---

## 🧪 Testing & Verification

Unit tests run completely offline with mocked RPC transport and require no physical display or running Discord client:

```bash
pytest
```

---

## 🔍 Troubleshooting (Windows)

- **Status Not Updating on Discord:**
  - Verify that your Discord Developer Application ID is entered in `config.json` under `"client_id"`.
  - Ensure the Discord desktop client is actively running. ZenRPC will automatically reconnect once Discord starts.
  - Make sure **Activity Privacy -> Display current activity as a status message** is enabled in your Discord user settings.
- **Tray Icon Not Visible:**
  - Windows automatically places new tray icons in the taskbar overflow area. Click the **^** arrow in your taskbar to reveal the ZenRPC icon, and drag it into the taskbar tray.
- **Python Not Found on Windows:**
  - Re-run the Python installer from [python.org](https://www.python.org/downloads/) and ensure **"Add python.exe to PATH"** is checked.
- **Application Logo / Icon Not Appearing in Discord Profile:**
  - Discord does not bundle third-party application icons automatically. You must upload the matching icon files from [`assets/art_assets/`](assets/art_assets/) into the **Discord Developer Portal** under your application's **Rich Presence → Art Assets** settings. See the [Developer Portal Guide](#️-setting-up-discord-art-assets-developer-portal-guide) above.
- **Presence Update Delay:**
  - Discord enforces a 15-second rate limit on rich presence updates. Setting `"update_interval"` lower than `15` in `config.json` is automatically clamped to `15` seconds to prevent rate-limit bans.

---

## 🗺️ Development Roadmap

The project follows a disciplined, platform-prioritized development roadmap:

1. **Windows Stabilization & Baseline (Active Focus):**
   - **`M2.6-W`:** Active-window Win32 detector reliability, offline mock unit tests, launcher independence, and mapping parity.
   - **`M2.7-W`:** Windows end-to-end verification checklist, documentation audit, and stable source release gate.
2. **Linux Stabilization & Baseline (Planned Follow-up):**
   - **`M3-L`:** `/proc/<pid>/cmdline` parsing reliability, subprocess timeout safety tests, desktop launcher validation, and Wayland graceful degradation.
3. **Optional Cross-Platform Enhancements (Deferred):**
   - **`M4`:** Native Wayland compositor IPC, local privacy filtering, rotating local file logging, and standalone packaging.

For complete roadmap directives and task tracking, see [`docs/ROADMAP.md`](docs/ROADMAP.md) and the [GitHub Milestones](https://github.com/githubuser2777/ZenRPC/milestones).

---

## 📄 License

This program is free software: you can redistribute it and/or modify it under the terms of the [GNU General Public License v3.0](LICENSE) as published by the Free Software Foundation, version 3 of the License (GPL-3.0-only).

Copyright (C) 2026 githubuser2777.

# Discord Rich Presence Art Assets Guide

Welcome to the **ZenRPC Art Assets Pack**! This folder contains **58 pre-normalized, high-resolution application icons** formatted specifically for Discord Rich Presence.

---

## ❓ Why Do I Need to Upload These Assets?

Discord Rich Presence operates on a **sandboxed application model**:
* When ZenRPC communicates with your local Discord desktop client, it sends a payload containing an asset key string:
  ```json
  {
    "assets": {
      "large_image": "vscode",
      "large_text": "Visual Studio Code"
    }
  }
  ```
* Discord does **not** search the web or pull third-party application icons automatically.
* Instead, Discord checks whether an image key named `"vscode"` has been uploaded under your specific Application's **Art Assets** tab in the **Discord Developer Portal**.
* If the key exists, Discord displays the icon on your profile card. If the key is missing, Discord displays your activity details and elapsed timer, but leaves the logo slot blank.

By uploading these icons to your Discord Application, your status will instantly show official, crisp logos whenever you focus on any supported application.

---

## 🚀 Quick Setup Walkthrough

Uploading these assets takes only a couple of minutes:

### 1. Open the Discord Developer Portal
Navigate to the [Discord Developer Applications Dashboard](https://discord.com/developers/applications) and sign in.

### 2. Select Your Application
Click on the application corresponding to the `client_id` configured in your `config.json`.

### 3. Open Art Assets
In the left-hand sidebar menu, navigate to:
**Rich Presence** → **Art Assets**

### 4. Upload Icon Images
1. Click the **Add Image(s)** button.
2. Select the icons you want to upload from this `assets/art_assets/` folder.
   > **Tip:** You can select all files or just the applications you frequently use.
3. **CRITICAL REQUIREMENT — Asset Key Naming:**
   Discord will prompt you for an **Asset Name** for each image.
   * **The Asset Name MUST match the filename without the `.png` extension!**
   * *Example:* For `vscode.png`, name the asset `vscode`.
   * *Example:* For `chrome.png`, name the asset `chrome`.
   * *Example:* For `alacritty.png`, name the asset `alacritty`.
   * *Example:* For `word.png`, name the asset `word`.
   * Discord asset names are lowercase alphanumeric strings (a-z, 0-9, and underscores).

### 5. Save Changes
Scroll down to the bottom of the page and click the green **Save Changes** button.

---

## ⏳ Important: Discord CDN Propagation Latency

After clicking **Save Changes**, Discord uploads your images to its worldwide Content Delivery Network (CDN):
* Newly uploaded assets typically take **2 to 10 minutes** to propagate across Discord's CDN servers.
* If an icon does not appear immediately upon switching applications, wait a few minutes and restart your Discord client or toggle ZenRPC off and on (`Disable RPC` → `Enable RPC` via the tray icon).

---

## 📋 Asset Keys & Application Mapping Reference

Every image in this folder is named exactly after its Discord asset key configured in `DEFAULT_CONFIG` and `config.example.json`:

| Asset Key | Application | Category | File Name |
| :--- | :--- | :--- | :--- |
| `vscode` | Visual Studio Code | Code Editor | `vscode.png` |
| `cursor` | Cursor | AI Code Editor | `cursor.png` |
| `windsurf` | Windsurf IDE | AI Code Editor | `windsurf.png` |
| `zed` | Zed | Code Editor | `zed.png` |
| `sublime` | Sublime Text | Code Editor | `sublime.png` |
| `pycharm` | JetBrains PyCharm | Python IDE | `pycharm.png` |
| `idea` | JetBrains IntelliJ IDEA | Java/Kotlin IDE | `idea.png` |
| `webstorm` | JetBrains WebStorm | Web IDE | `webstorm.png` |
| `rider` | JetBrains Rider | .NET IDE | `rider.png` |
| `visualstudio`| Visual Studio | IDE | `visualstudio.png` |
| `neovim` | Neovim / Vim | Text Editor | `neovim.png` |
| `emacs` | GNU Emacs | Extensible Editor | `emacs.png` |
| `kate` | Kate | KDE Text Editor | `kate.png` |
| `geany` | Geany | Lightweight IDE | `geany.png` |
| `notepad` | Notepad / Text Editors | Basic Editor | `notepad.png` |
| `chrome` | Google Chrome | Web Browser | `chrome.png` |
| `firefox` | Mozilla Firefox | Web Browser | `firefox.png` |
| `chromium` | Chromium | Web Browser | `chromium.png` |
| `edge` | Microsoft Edge | Web Browser | `edge.png` |
| `brave` | Brave Browser | Web Browser | `brave.png` |
| `tor` | Tor Browser | Privacy Browser | `tor.png` |
| `zen` | Zen Browser | Privacy Browser | `zen.png` |
| `opera` | Opera & Opera GX | Web Browser | `opera.png` |
| `arc` | Arc Browser | Web Browser | `arc.png` |
| `vivaldi` | Vivaldi | Web Browser | `vivaldi.png` |
| `epiphany` | GNOME Web | Web Browser | `epiphany.png` |
| `discord` | Discord | Communication | `discord.png` |
| `telegram` | Telegram | Communication | `telegram.png` |
| `zalo` | Zalo | Communication | `zalo.png` |
| `slack` | Slack | Collaboration | `slack.png` |
| `teams` | Microsoft Teams | Collaboration | `teams.png` |
| `notion` | Notion | Notes & Wiki | `notion.png` |
| `obsidian` | Obsidian | Knowledge Base | `obsidian.png` |
| `figma` | Figma | UI/UX Design | `figma.png` |
| `blender` | Blender | 3D Graphics | `blender.png` |
| `photoshop` | Adobe Photoshop | Graphic Design | `photoshop.png` |
| `gimp` | GIMP | Image Editor | `gimp.png` |
| `krita` | Krita | Digital Painting | `krita.png` |
| `inkscape` | Inkscape | Vector Graphics | `inkscape.png` |
| `kdenlive` | Kdenlive | Video Editor | `kdenlive.png` |
| `audacity` | Audacity | Audio Editor | `audacity.png` |
| `libreoffice`| LibreOffice | Office Suite | `libreoffice.png` |
| `word` | Microsoft Word / Writer| Document Processing| `word.png` |
| `excel` | Microsoft Excel / Calc | Spreadsheets | `excel.png` |
| `powerpoint` | PowerPoint / Impress | Presentations | `powerpoint.png` |
| `evince` | Evince | Document Viewer | `evince.png` |
| `okular` | Okular | Document Viewer | `okular.png` |
| `explorer` | File Explorer / Nautilus| File Manager | `explorer.png` |
| `dolphin` | Dolphin | KDE File Manager | `dolphin.png` |
| `vlc` | VLC Media Player | Media Player | `vlc.png` |
| `mpv` | mpv | Media Player | `mpv.png` |
| `spotify` | Spotify | Music Streaming | `spotify.png` |
| `steam` | Steam | Gaming Platform | `steam.png` |
| `obs` | OBS Studio | Live Streaming | `obs.png` |
| `alacritty` | Alacritty | GPU Terminal | `alacritty.png` |
| `kitty` | Kitty | GPU Terminal | `kitty.png` |
| `wezterm` | WezTerm | Terminal Emulator | `wezterm.png` |
| `terminal` | System Terminals | Terminal / Shell | `terminal.png` |

---

## 📐 Asset Technical Specifications

All assets in this directory have been compiled and verified to meet Discord's strict Rich Presence requirements:

* **Dimensions:** Exact 512 × 512 pixels (Discord's recommended 1:1 square canvas).
* **Color Space & Depth:** 32-bit RGBA with full alpha transparency support.
* **File Format:** Optimized PNG.
* **Aspect Ratio Preservation:** Non-square logos have been centered and padded with transparent borders to prevent stretching or distortion when rendered in Discord's circular and rounded-corner avatar frames.

---

## 📜 Provenance & Licenses

Every asset in this collection has been sourced legally from official brand guidelines, permissive open-source vector icon collections (Simple Icons, SVGL), or Wikimedia Commons under CC0, Public Domain, MIT, BSD, or fair use trademark guidelines.

For complete provenance, license classifications, and upstream sources for each individual icon, please refer to [`SOURCES.md`](SOURCES.md).

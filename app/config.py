import copy
import json
import logging
import os

logger = logging.getLogger("zenrpc")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
EXAMPLE_CONFIG_FILE = os.path.join(BASE_DIR, "config.example.json")

DEFAULT_CONFIG = {
    "client_id": "YOUR_CLIENT_ID_HERE",
    "update_interval": 15,
    "reconnect_delay": 30,
    "show_window_title": True,
    "clear_on_idle": True,
    "custom_mappings": {
        "Code.exe": {
            "name": "Visual Studio Code",
            "icon": "vscode",
            "detail": "Editing code"
        },
        "code": {
            "name": "Visual Studio Code",
            "icon": "vscode",
            "detail": "Coding"
        },
        "chrome.exe": {
            "name": "Google Chrome",
            "icon": "chrome",
            "detail": "Browsing the web"
        },
        "chrome": {
            "name": "Google Chrome",
            "icon": "chrome",
            "detail": "Browsing"
        },
        "google-chrome": {
            "name": "Google Chrome",
            "icon": "chrome",
            "detail": "Browsing"
        },
        "firefox.exe": {
            "name": "Firefox",
            "icon": "firefox",
            "detail": "Browsing the web"
        },
        "firefox": {
            "name": "Firefox",
            "icon": "firefox",
            "detail": "Browsing"
        },
        "discord.exe": {
            "name": "Discord",
            "icon": "discord",
            "detail": "Chatting"
        },
        "discord": {
            "name": "Discord",
            "icon": "discord",
            "detail": "Chatting"
        },
        "DiscordPTB.exe": {
            "name": "Discord PTB",
            "icon": "discord",
            "detail": "Chatting"
        },
        "discordptb.exe": {
            "name": "Discord PTB",
            "icon": "discord",
            "detail": "Chatting"
        },
        "DiscordPTB": {
            "name": "Discord PTB",
            "icon": "discord",
            "detail": "Chatting"
        },
        "discord-ptb": {
            "name": "Discord PTB",
            "icon": "discord",
            "detail": "Chatting"
        },
        "notepad.exe": {
            "name": "Notepad",
            "icon": "notepad",
            "detail": "Writing"
        },
        "gedit": {
            "name": "Text Editor",
            "icon": "notepad",
            "detail": "Writing"
        },
        "explorer.exe": {
            "name": "File Explorer",
            "icon": "explorer",
            "detail": "Viewing files"
        },
        "nautilus": {
            "name": "Files",
            "icon": "explorer",
            "detail": "Browsing files"
        },
        "Photoshop.exe": {
            "name": "Adobe Photoshop",
            "icon": "photoshop",
            "detail": "Editing images"
        },
        "photoshop": {
            "name": "Adobe Photoshop",
            "icon": "photoshop",
            "detail": "Editing images"
        },
        "gimp": {
            "name": "GIMP",
            "icon": "gimp",
            "detail": "Editing image"
        },
        "vlc.exe": {
            "name": "VLC Media Player",
            "icon": "vlc",
            "detail": "Watching video"
        },
        "vlc": {
            "name": "VLC Media Player",
            "icon": "vlc",
            "detail": "Watching video"
        },
        "spotify.exe": {
            "name": "Spotify",
            "icon": "spotify",
            "detail": "Listening to music"
        },
        "spotify": {
            "name": "Spotify",
            "icon": "spotify",
            "detail": "Listening to music"
        },
        "steam.exe": {
            "name": "Steam",
            "icon": "steam",
            "detail": "Playing games"
        },
        "steam": {
            "name": "Steam",
            "icon": "steam",
            "detail": "Gaming"
        },
        "obs64.exe": {
            "name": "OBS Studio",
            "icon": "obs",
            "detail": "Streaming"
        },
        "obs": {
            "name": "OBS Studio",
            "icon": "obs",
            "detail": "Streaming"
        },
        "zed.exe": {
            "name": "Zed",
            "icon": "zed",
            "detail": "Editing code"
        },
        "zed": {
            "name": "Zed",
            "icon": "zed",
            "detail": "Editing code"
        },
        "terminal": {
            "name": "Terminal",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "gnome-terminal": {
            "name": "Terminal",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "konsole": {
            "name": "Terminal",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "Cursor.exe": {
            "name": "Cursor",
            "icon": "cursor",
            "detail": "Editing code"
        },
        "cursor": {
            "name": "Cursor",
            "icon": "cursor",
            "detail": "Editing code"
        },
        "Orca.exe": {
            "name": "Orca",
            "icon": "orca",
            "detail": "Developing with Orca"
        },
        "orca": {
            "name": "Orca",
            "icon": "orca",
            "detail": "Developing with Orca"
        },
        "orca-ide.exe": {
            "name": "Orca",
            "icon": "orca",
            "detail": "Developing with Orca"
        },
        "orca-ide": {
            "name": "Orca",
            "icon": "orca",
            "detail": "Developing with Orca"
        },
        "Windsurf.exe": {
            "name": "Windsurf",
            "icon": "windsurf",
            "detail": "Editing code"
        },
        "windsurf": {
            "name": "Windsurf",
            "icon": "windsurf",
            "detail": "Editing code"
        },
        "sublime_text.exe": {
            "name": "Sublime Text",
            "icon": "sublime",
            "detail": "Editing code"
        },
        "sublime_text": {
            "name": "Sublime Text",
            "icon": "sublime",
            "detail": "Editing code"
        },
        "pycharm64.exe": {
            "name": "PyCharm",
            "icon": "pycharm",
            "detail": "Editing Python"
        },
        "pycharm.exe": {
            "name": "PyCharm",
            "icon": "pycharm",
            "detail": "Editing Python"
        },
        "pycharm": {
            "name": "PyCharm",
            "icon": "pycharm",
            "detail": "Editing Python"
        },
        "idea64.exe": {
            "name": "IntelliJ IDEA",
            "icon": "idea",
            "detail": "Writing code"
        },
        "idea.exe": {
            "name": "IntelliJ IDEA",
            "icon": "idea",
            "detail": "Writing code"
        },
        "idea": {
            "name": "IntelliJ IDEA",
            "icon": "idea",
            "detail": "Writing code"
        },
        "webstorm64.exe": {
            "name": "WebStorm",
            "icon": "webstorm",
            "detail": "Writing JavaScript"
        },
        "webstorm.exe": {
            "name": "WebStorm",
            "icon": "webstorm",
            "detail": "Writing JavaScript"
        },
        "webstorm": {
            "name": "WebStorm",
            "icon": "webstorm",
            "detail": "Writing JavaScript"
        },
        "rider64.exe": {
            "name": "JetBrains Rider",
            "icon": "rider",
            "detail": "Developing .NET"
        },
        "rider.exe": {
            "name": "JetBrains Rider",
            "icon": "rider",
            "detail": "Developing .NET"
        },
        "rider": {
            "name": "JetBrains Rider",
            "icon": "rider",
            "detail": "Developing .NET"
        },
        "devenv.exe": {
            "name": "Visual Studio",
            "icon": "visualstudio",
            "detail": "Developing software"
        },
        "devenv": {
            "name": "Visual Studio",
            "icon": "visualstudio",
            "detail": "Developing software"
        },
        "nvim.exe": {
            "name": "Neovim",
            "icon": "neovim",
            "detail": "Editing text"
        },
        "nvim": {
            "name": "Neovim",
            "icon": "neovim",
            "detail": "Editing text"
        },
        "gvim.exe": {
            "name": "Vim",
            "icon": "neovim",
            "detail": "Editing text"
        },
        "vim.exe": {
            "name": "Vim",
            "icon": "neovim",
            "detail": "Editing text"
        },
        "vim": {
            "name": "Vim",
            "icon": "neovim",
            "detail": "Editing text"
        },
        "msedge.exe": {
            "name": "Microsoft Edge",
            "icon": "edge",
            "detail": "Browsing the web"
        },
        "msedge": {
            "name": "Microsoft Edge",
            "icon": "edge",
            "detail": "Browsing the web"
        },
        "brave.exe": {
            "name": "Brave Browser",
            "icon": "brave",
            "detail": "Browsing the web"
        },
        "brave": {
            "name": "Brave Browser",
            "icon": "brave",
            "detail": "Browsing the web"
        },
        "opera.exe": {
            "name": "Opera",
            "icon": "opera",
            "detail": "Browsing the web"
        },
        "opera": {
            "name": "Opera",
            "icon": "opera",
            "detail": "Browsing the web"
        },
        "opera_gx.exe": {
            "name": "Opera GX",
            "icon": "opera",
            "detail": "Browsing the web"
        },
        "Arc.exe": {
            "name": "Arc",
            "icon": "arc",
            "detail": "Browsing the web"
        },
        "arc": {
            "name": "Arc",
            "icon": "arc",
            "detail": "Browsing the web"
        },
        "vivaldi.exe": {
            "name": "Vivaldi",
            "icon": "vivaldi",
            "detail": "Browsing the web"
        },
        "vivaldi": {
            "name": "Vivaldi",
            "icon": "vivaldi",
            "detail": "Browsing the web"
        },
        "Telegram.exe": {
            "name": "Telegram",
            "icon": "telegram",
            "detail": "Chatting"
        },
        "telegram-desktop": {
            "name": "Telegram",
            "icon": "telegram",
            "detail": "Chatting"
        },
        "telegram": {
            "name": "Telegram",
            "icon": "telegram",
            "detail": "Chatting"
        },
        "Zalo.exe": {
            "name": "Zalo",
            "icon": "zalo",
            "detail": "Chatting"
        },
        "zalo": {
            "name": "Zalo",
            "icon": "zalo",
            "detail": "Chatting"
        },
        "slack.exe": {
            "name": "Slack",
            "icon": "slack",
            "detail": "Collaborating"
        },
        "slack": {
            "name": "Slack",
            "icon": "slack",
            "detail": "Collaborating"
        },
        "ms-teams.exe": {
            "name": "Microsoft Teams",
            "icon": "teams",
            "detail": "Meeting & Chatting"
        },
        "Teams.exe": {
            "name": "Microsoft Teams",
            "icon": "teams",
            "detail": "Meeting & Chatting"
        },
        "teams": {
            "name": "Microsoft Teams",
            "icon": "teams",
            "detail": "Meeting & Chatting"
        },
        "Notion.exe": {
            "name": "Notion",
            "icon": "notion",
            "detail": "Organizing notes"
        },
        "notion": {
            "name": "Notion",
            "icon": "notion",
            "detail": "Organizing notes"
        },
        "Obsidian.exe": {
            "name": "Obsidian",
            "icon": "obsidian",
            "detail": "Writing notes"
        },
        "obsidian": {
            "name": "Obsidian",
            "icon": "obsidian",
            "detail": "Writing notes"
        },
        "Figma.exe": {
            "name": "Figma",
            "icon": "figma",
            "detail": "Designing UI/UX"
        },
        "figma": {
            "name": "Figma",
            "icon": "figma",
            "detail": "Designing UI/UX"
        },
        "blender.exe": {
            "name": "Blender",
            "icon": "blender",
            "detail": "3D Modeling"
        },
        "blender": {
            "name": "Blender",
            "icon": "blender",
            "detail": "3D Modeling"
        },
        "WINWORD.EXE": {
            "name": "Microsoft Word",
            "icon": "word",
            "detail": "Writing document"
        },
        "winword": {
            "name": "Microsoft Word",
            "icon": "word",
            "detail": "Writing document"
        },
        "EXCEL.EXE": {
            "name": "Microsoft Excel",
            "icon": "excel",
            "detail": "Analyzing data"
        },
        "excel": {
            "name": "Microsoft Excel",
            "icon": "excel",
            "detail": "Analyzing data"
        },
        "POWERPNT.EXE": {
            "name": "Microsoft PowerPoint",
            "icon": "powerpoint",
            "detail": "Designing slides"
        },
        "powerpnt": {
            "name": "Microsoft PowerPoint",
            "icon": "powerpoint",
            "detail": "Designing slides"
        },
        "WindowsTerminal.exe": {
            "name": "Windows Terminal",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "wt.exe": {
            "name": "Windows Terminal",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "pwsh.exe": {
            "name": "PowerShell",
            "icon": "terminal",
            "detail": "In PowerShell"
        },
        "pwsh": {
            "name": "PowerShell",
            "icon": "terminal",
            "detail": "In PowerShell"
        },
        "powershell.exe": {
            "name": "PowerShell",
            "icon": "terminal",
            "detail": "In PowerShell"
        },
        "powershell": {
            "name": "PowerShell",
            "icon": "terminal",
            "detail": "In PowerShell"
        },
        "cmd.exe": {
            "name": "Command Prompt",
            "icon": "terminal",
            "detail": "In Command Prompt"
        },
        "cmd": {
            "name": "Command Prompt",
            "icon": "terminal",
            "detail": "In Command Prompt"
        },
        "alacritty": {
            "name": "Alacritty",
            "icon": "alacritty",
            "detail": "In terminal"
        },
        "Alacritty.exe": {
            "name": "Alacritty",
            "icon": "alacritty",
            "detail": "In terminal"
        },
        "kitty": {
            "name": "Kitty",
            "icon": "kitty",
            "detail": "In terminal"
        },
        "wezterm-gui": {
            "name": "WezTerm",
            "icon": "wezterm",
            "detail": "In terminal"
        },
        "wezterm": {
            "name": "WezTerm",
            "icon": "wezterm",
            "detail": "In terminal"
        },
        "foot": {
            "name": "Foot",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "tilix": {
            "name": "Tilix",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "xfce4-terminal": {
            "name": "XFCE Terminal",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "urxvt": {
            "name": "URxvt",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "xterm": {
            "name": "XTerm",
            "icon": "terminal",
            "detail": "In terminal"
        },
        "chromium": {
            "name": "Chromium",
            "icon": "chromium",
            "detail": "Browsing the web"
        },
        "chromium-browser": {
            "name": "Chromium",
            "icon": "chromium",
            "detail": "Browsing the web"
        },
        "tor-browser": {
            "name": "Tor Browser",
            "icon": "tor",
            "detail": "Browsing securely"
        },
        "torbrowser-launcher": {
            "name": "Tor Browser",
            "icon": "tor",
            "detail": "Browsing securely"
        },
        "zen": {
            "name": "Zen Browser",
            "icon": "zen",
            "detail": "Browsing the web"
        },
        "zen-bin": {
            "name": "Zen Browser",
            "icon": "zen",
            "detail": "Browsing the web"
        },
        "zen-browser": {
            "name": "Zen Browser",
            "icon": "zen",
            "detail": "Browsing the web"
        },
        "epiphany": {
            "name": "GNOME Web",
            "icon": "epiphany",
            "detail": "Browsing the web"
        },
        "epiphany-browser": {
            "name": "GNOME Web",
            "icon": "epiphany",
            "detail": "Browsing the web"
        },
        "emacs": {
            "name": "GNU Emacs",
            "icon": "emacs",
            "detail": "Editing text"
        },
        "emacsclient": {
            "name": "GNU Emacs",
            "icon": "emacs",
            "detail": "Editing text"
        },
        "kate": {
            "name": "Kate",
            "icon": "kate",
            "detail": "Editing code"
        },
        "kwrite": {
            "name": "KWrite",
            "icon": "notepad",
            "detail": "Writing"
        },
        "geany": {
            "name": "Geany",
            "icon": "geany",
            "detail": "Editing code"
        },
        "nano": {
            "name": "GNU nano",
            "icon": "terminal",
            "detail": "Editing text"
        },
        "mousepad": {
            "name": "Mousepad",
            "icon": "notepad",
            "detail": "Writing"
        },
        "xed": {
            "name": "Xed",
            "icon": "notepad",
            "detail": "Writing"
        },
        "pluma": {
            "name": "Pluma",
            "icon": "notepad",
            "detail": "Writing"
        },
        "leafpad": {
            "name": "Leafpad",
            "icon": "notepad",
            "detail": "Writing"
        },
        "krita": {
            "name": "Krita",
            "icon": "krita",
            "detail": "Painting"
        },
        "inkscape": {
            "name": "Inkscape",
            "icon": "inkscape",
            "detail": "Vector drawing"
        },
        "kdenlive": {
            "name": "Kdenlive",
            "icon": "kdenlive",
            "detail": "Editing video"
        },
        "mpv": {
            "name": "mpv",
            "icon": "mpv",
            "detail": "Watching video"
        },
        "audacity": {
            "name": "Audacity",
            "icon": "audacity",
            "detail": "Editing audio"
        },
        "soffice.bin": {
            "name": "LibreOffice",
            "icon": "libreoffice",
            "detail": "Office work"
        },
        "libreoffice": {
            "name": "LibreOffice",
            "icon": "libreoffice",
            "detail": "Office work"
        },
        "swriter": {
            "name": "LibreOffice Writer",
            "icon": "word",
            "detail": "Writing document"
        },
        "scalc": {
            "name": "LibreOffice Calc",
            "icon": "excel",
            "detail": "Analyzing data"
        },
        "simpress": {
            "name": "LibreOffice Impress",
            "icon": "powerpoint",
            "detail": "Designing slides"
        },
        "evince": {
            "name": "Evince",
            "icon": "evince",
            "detail": "Reading document"
        },
        "okular": {
            "name": "Okular",
            "icon": "okular",
            "detail": "Reading document"
        },
        "dolphin": {
            "name": "Dolphin",
            "icon": "dolphin",
            "detail": "Browsing files"
        },
        "thunar": {
            "name": "Thunar",
            "icon": "explorer",
            "detail": "Browsing files"
        },
        "nemo": {
            "name": "Nemo",
            "icon": "explorer",
            "detail": "Browsing files"
        },
        "pcmanfm": {
            "name": "PCManFM",
            "icon": "explorer",
            "detail": "Browsing files"
        },
        "htop": {
            "name": "System Monitor",
            "icon": "terminal",
            "detail": "Monitoring system"
        },
        "btop": {
            "name": "System Monitor",
            "icon": "terminal",
            "detail": "Monitoring system"
        }
    }
}


def get_config_path(config_path=None):
    """Returns absolute path to configuration file."""
    return os.path.abspath(config_path or CONFIG_FILE)


def _validate_and_sanitize(cfg):
    """Ensures configuration contains all expected keys with safe types and bounds."""
    validated = copy.deepcopy(DEFAULT_CONFIG)

    if isinstance(cfg, dict):
        for k, v in cfg.items():
            validated[k] = v

    # Enforce type and minimum bounds
    interval = validated.get("update_interval")
    try:
        interval = int(interval)
        if interval < 15:
            logger.warning("update_interval %s is below Discord rate limit (15s); clamping to 15.", interval)
            interval = 15
    except (ValueError, TypeError):
        logger.warning("Invalid update_interval; resetting to default 15.")
        interval = 15
    validated["update_interval"] = interval

    delay = validated.get("reconnect_delay")
    try:
        delay = int(delay)
        if delay < 5:
            delay = 5
    except (ValueError, TypeError):
        delay = 30
    validated["reconnect_delay"] = delay

    validated["show_window_title"] = bool(validated.get("show_window_title", True))
    validated["clear_on_idle"] = bool(validated.get("clear_on_idle", True))

    merged_mappings = copy.deepcopy(DEFAULT_CONFIG["custom_mappings"])
    if isinstance(cfg, dict) and isinstance(cfg.get("custom_mappings"), dict):
        merged_mappings.update(cfg["custom_mappings"])
    validated["custom_mappings"] = merged_mappings

    return validated


def load_config(config_path=None):
    """
    Loads configuration from disk.
    If file doesn't exist, initializes it from example template or defaults.
    Falls back gracefully if JSON is corrupted.
    """
    target = get_config_path(config_path)

    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            return _validate_and_sanitize(loaded)
        except Exception as e:
            logger.warning("Failed to parse config at %s (%s). Falling back to defaults.", target, e)
            return copy.deepcopy(DEFAULT_CONFIG)

    # File does not exist: create from example or default
    initial_data = None
    if os.path.exists(EXAMPLE_CONFIG_FILE):
        try:
            with open(EXAMPLE_CONFIG_FILE, "r", encoding="utf-8") as f:
                initial_data = json.load(f)
        except Exception:
            pass

    if initial_data is None:
        initial_data = copy.deepcopy(DEFAULT_CONFIG)

    cfg = _validate_and_sanitize(initial_data)
    try:
        save_config(cfg, target)
        logger.info("Created default configuration at %s", target)
    except Exception as e:
        logger.error("Could not write initial config to %s: %s", target, e)

    return cfg


def save_config(cfg, config_path=None):
    """Saves configuration safely to disk formatted as UTF-8 JSON."""
    target = get_config_path(config_path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

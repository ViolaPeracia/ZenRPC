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

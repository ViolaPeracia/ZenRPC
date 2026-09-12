import json
import os
import tempfile
from app.config import DEFAULT_CONFIG, get_config_path, load_config, save_config


def test_default_config_structure():
    """Default config must contain all expected top-level fields."""
    assert "client_id" in DEFAULT_CONFIG
    assert "update_interval" in DEFAULT_CONFIG
    assert "reconnect_delay" in DEFAULT_CONFIG
    assert "show_window_title" in DEFAULT_CONFIG
    assert "clear_on_idle" in DEFAULT_CONFIG
    assert "custom_mappings" in DEFAULT_CONFIG
    assert DEFAULT_CONFIG["update_interval"] >= 15


def test_config_created_if_missing():
    """If target config does not exist, load_config creates it with defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        assert not os.path.exists(cfg_path)

        cfg = load_config(cfg_path)
        assert os.path.exists(cfg_path)
        assert cfg["client_id"] == "YOUR_CLIENT_ID_HERE"
        assert cfg["update_interval"] == 15


def test_config_merges_missing_keys():
    """Partial configuration must be merged with defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        # Write config with missing keys
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"client_id": "123456789"}, f)

        cfg = load_config(cfg_path)
        assert cfg["client_id"] == "123456789"
        assert cfg["update_interval"] == 15
        assert cfg["reconnect_delay"] == 30
        assert cfg["show_window_title"] is True
        assert cfg["clear_on_idle"] is True
        assert "Code.exe" in cfg["custom_mappings"]


def test_malformed_json_fallback():
    """Corrupted JSON must not crash load_config and must fall back to defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            f.write("{ this is not valid json: true, ")

        cfg = load_config(cfg_path)
        assert cfg["client_id"] == DEFAULT_CONFIG["client_id"]
        assert cfg["update_interval"] == 15


def test_update_interval_clamped():
    """update_interval lower than 15 must be clamped to 15 (Discord rate limit)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"client_id": "123", "update_interval": 2}, f)

        cfg = load_config(cfg_path)
        assert cfg["update_interval"] == 15

        # Invalid string value
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"client_id": "123", "update_interval": "invalid"}, f)

        cfg = load_config(cfg_path)
        assert cfg["update_interval"] == 15


def test_script_relative_path():
    """Default config path must resolve relative to repository base dir."""
    default_path = get_config_path()
    assert os.path.isabs(default_path)
    assert default_path.endswith("config.json")


def test_cwd_independence(tmp_path):
    """Configuration path resolution must not depend on process current working directory."""
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        default_path = get_config_path()
        assert os.path.isabs(default_path)
        assert os.path.dirname(default_path) != str(tmp_path)
        assert default_path.endswith("config.json")
    finally:
        os.chdir(original_cwd)


def test_custom_mappings_merge_user_and_defaults():
    """User mappings must merge with defaults, allowing overrides while retaining built-ins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({
                "client_id": "123",
                "custom_mappings": {
                    "my_editor": {"name": "My Editor", "icon": "editor", "detail": "Writing"},
                    "Code.exe": {"name": "Custom VS Code", "icon": "vscode_custom", "detail": "Hacking"}
                }
            }, f)

        cfg = load_config(cfg_path)
        # Custom mapping present
        assert "my_editor" in cfg["custom_mappings"]
        assert cfg["custom_mappings"]["my_editor"]["name"] == "My Editor"
        # User override preserved
        assert cfg["custom_mappings"]["Code.exe"]["name"] == "Custom VS Code"
        # Built-in mappings preserved
        assert "chrome.exe" in cfg["custom_mappings"]
        assert "Photoshop.exe" in cfg["custom_mappings"]


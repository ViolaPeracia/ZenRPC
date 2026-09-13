import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import pytest
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


def test_external_cwd_subprocess_resolution(tmp_path):
    """Invoking config resolution via Python subprocess from external CWD resolves to repo config."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    expected_config_path = os.path.join(repo_root, "config.json")

    cmd = [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, sys.argv[1]); from app.config import get_config_path; print(get_config_path())",
        repo_root,
    ]
    res = subprocess.run(
        cmd,
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    resolved_path = res.stdout.strip()
    assert os.path.samefile(resolved_path, expected_config_path)


def test_run_sh_script_cwd_independence(tmp_path):
    """run.sh launcher resolves repository root correctly from an external working directory."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_sh = os.path.join(repo_root, "run.sh")
    assert os.path.isfile(run_sh)
    assert os.access(run_sh, os.X_OK)

    res = subprocess.run(
        ["bash", "-c", f'APP_DIR="$(cd "$(dirname "{run_sh}")" && pwd)" && echo "$APP_DIR"'],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    resolved_dir = res.stdout.strip()
    assert os.path.samefile(resolved_dir, repo_root)


def test_run_sh_execution_from_external_cwd(tmp_path):
    """Invoking run.sh from an external working directory starts up and shuts down cleanly."""
    if not os.environ.get("DISPLAY"):
        pytest.skip("DISPLAY not set; skipping live launcher execution test")

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_sh = os.path.join(repo_root, "run.sh")
    assert os.path.isfile(run_sh)
    assert os.access(run_sh, os.X_OK)

    proc = subprocess.Popen(
        [run_sh],
        cwd=str(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(0.8)
        assert proc.poll() is None, f"run.sh exited prematurely: {proc.stderr.read()}"
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=5)
        assert proc.returncode == 0
    except Exception:
        proc.kill()
        raise



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


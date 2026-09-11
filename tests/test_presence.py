import os
import tempfile
import time
from app.config import save_config
from app.presence import PresenceEngine, truncate_utf8


def test_truncate_utf8_ascii():
    """ASCII strings shorter than 128 bytes remain unchanged; longer ones truncate at 128."""
    short = "Hello World"
    assert truncate_utf8(short, 128) == short

    exact = "A" * 128
    assert truncate_utf8(exact, 128) == exact
    assert len(truncate_utf8(exact, 128).encode("utf-8")) == 128

    long_str = "A" * 200
    truncated = truncate_utf8(long_str, 128)
    assert len(truncated.encode("utf-8")) == 128
    assert truncated == "A" * 128


def test_truncate_utf8_multibyte():
    """Multi-byte Unicode characters (e.g. Vietnamese, emojis) must not be split."""
    # Character 'ế' (U+1EBF) is 3 bytes in UTF-8
    # 65 chars * 3 bytes = 195 bytes -> must be truncated to 42 chars (126 bytes, not splitting the 43rd char)
    vietnamese = "ế" * 65
    truncated = truncate_utf8(vietnamese, 128)
    encoded = truncated.encode("utf-8")
    assert len(encoded) <= 128
    assert len(encoded) == 126
    assert truncated == "ế" * 42

    # Emoji '🚀' is 4 bytes in UTF-8
    # 32 emojis * 4 = 128 bytes
    # 33 emojis * 4 = 132 bytes
    emojis = "🚀" * 33
    truncated_emoji = truncate_utf8(emojis, 128)
    encoded_emoji = truncated_emoji.encode("utf-8")
    assert len(encoded_emoji) <= 128
    assert len(encoded_emoji) == 128
    assert truncated_emoji == "🚀" * 32

    # String with character that straddles the 128 boundary
    # 127 'a's (127 bytes) + 1 'ế' (2 bytes) = 129 bytes
    # Truncation must drop the 'ế' and leave exactly 127 'a's
    straddle = "a" * 127 + "ế"
    res = truncate_utf8(straddle, 128)
    assert len(res.encode("utf-8")) <= 128
    assert res == "a" * 127


def test_app_change_resets_timer(mock_rpc_factory):
    """Switching applications must reset the start timestamp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        save_config({"client_id": "123456789"}, cfg_path)

        current_window = ["chrome.exe", "Google Chrome - Home"]

        def mock_detector():
            return current_window[0], current_window[1]

        engine = PresenceEngine(
            config_path=cfg_path,
            detector_fn=mock_detector,
            rpc_factory=mock_rpc_factory,
        )

        assert engine.connect() is True
        assert len(mock_rpc_factory.instances) == 1
        rpc = mock_rpc_factory.instances[0]

        # Step 1: App is Chrome
        engine.update_once()
        assert len(rpc.updates) == 1
        chrome_start_ts = rpc.updates[0]["start"]
        assert rpc.updates[0]["details"] == "Browsing the web"

        # Step 2: Switch to VS Code 2 seconds later
        time.sleep(1.1)
        current_window[0] = "Code.exe"
        current_window[1] = "main.py - VS Code"

        engine.update_once()
        assert len(rpc.updates) == 2
        code_start_ts = rpc.updates[1]["start"]
        assert rpc.updates[1]["details"] == "Editing code"

        # Start timestamp MUST have reset and be greater than previous Chrome start
        assert code_start_ts > chrome_start_ts


def test_title_change_preserves_timer(mock_rpc_factory):
    """Changing window title within the same application must PRESERVE the elapsed timer."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        save_config({"client_id": "123456789"}, cfg_path)

        current_window = ["chrome.exe", "Tab 1 - Search"]

        def mock_detector():
            return current_window[0], current_window[1]

        engine = PresenceEngine(
            config_path=cfg_path,
            detector_fn=mock_detector,
            rpc_factory=mock_rpc_factory,
        )

        assert engine.connect() is True
        rpc = mock_rpc_factory.instances[0]

        # Step 1: Chrome Tab 1
        engine.update_once()
        assert len(rpc.updates) == 1
        initial_start_ts = rpc.updates[0]["start"]
        assert rpc.updates[0]["state"] == "Tab 1 - Search"

        # Step 2: Chrome Tab 2 (title change only, still chrome.exe)
        time.sleep(1.1)
        current_window[1] = "Tab 2 - YouTube"

        engine.update_once()
        assert len(rpc.updates) == 2
        second_start_ts = rpc.updates[1]["start"]
        assert rpc.updates[1]["state"] == "Tab 2 - YouTube"

        # Start timestamp MUST be preserved!
        assert second_start_ts == initial_start_ts


def test_lock_mode_semantics(mock_rpc_factory):
    """Lock mode must lock presence to current app and maintain locked_since timestamp."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        save_config({"client_id": "123456789"}, cfg_path)

        current_window = ["Code.exe", "project.py"]

        def mock_detector():
            return current_window[0], current_window[1]

        engine = PresenceEngine(
            config_path=cfg_path,
            detector_fn=mock_detector,
            rpc_factory=mock_rpc_factory,
        )

        assert engine.connect() is True
        rpc = mock_rpc_factory.instances[0]

        # Lock to VS Code
        engine.toggle_lock()
        assert engine.locked is True
        assert engine.locked_proc == "Code.exe"
        locked_ts = engine.locked_since

        # Update while locked
        engine.update_once()
        assert len(rpc.updates) == 1
        assert rpc.updates[0]["start"] == locked_ts
        assert rpc.updates[0]["small_text"] == "[LOCKED]"

        # Switch window to Chrome in background; presence should REMAIN locked to VS Code
        current_window[0] = "chrome.exe"
        current_window[1] = "Reddit"

        engine.update_once()
        # Duplicate state suppressed, still locked to VS Code
        assert rpc.updates[-1]["start"] == locked_ts
        assert rpc.updates[-1]["details"] == "Editing code"

        # Unlock
        engine.toggle_lock()
        assert engine.locked is False


def test_reconnect_loop_runs_when_discord_offline(mock_rpc_factory):
    """Engine.start() must keep worker thread running even if initial connect() fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        save_config({"client_id": "123456789", "reconnect_delay": 5}, cfg_path)

        engine = PresenceEngine(
            config_path=cfg_path,
            detector_fn=lambda: ("test.exe", "Test Window"),
            rpc_factory=mock_rpc_factory,
        )

        # Force initial connect to fail (Discord closed)
        mock_rpc_factory_instance = mock_rpc_factory("123456789")
        mock_rpc_factory_instance.fail_connect = True

        # Factory returns the failing instance first
        def failing_factory(cid):
            return mock_rpc_factory_instance

        engine.rpc_factory = failing_factory

        engine.start()
        # Worker thread must be alive even though connection failed!
        assert engine.running is True
        assert engine._thread is not None
        assert engine._thread.is_alive()
        assert engine.connected is False

        # Stop cleanly
        engine.stop()
        assert engine.running is False
        assert not engine._thread.is_alive()


def test_premigration_process_and_asset_mappings(mock_rpc_factory):
    """
    Verifies that every pre-migration process recognition rule and Discord asset/icon
    mapping produces the expected large_image and display text.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        save_config({"client_id": "123456789"}, cfg_path)
        engine = PresenceEngine(
            config_path=cfg_path,
            rpc_factory=mock_rpc_factory,
        )
        assert engine.connect() is True
        rpc = mock_rpc_factory.instances[0]

        test_cases = [
            # (process_name, expected_icon, expected_name, expected_detail)
            ("Code.exe", "vscode", "Visual Studio Code", "Editing code"),
            ("code", "vscode", "Visual Studio Code", "Coding"),
            ("chrome.exe", "chrome", "Google Chrome", "Browsing the web"),
            ("chrome", "chrome", "Google Chrome", "Browsing"),
            ("google-chrome", "chrome", "Google Chrome", "Browsing"),
            ("CHROME.EXE", "chrome", "Google Chrome", "Browsing the web"),
            ("firefox.exe", "firefox", "Firefox", "Browsing the web"),
            ("firefox", "firefox", "Firefox", "Browsing"),
            ("discord.exe", "discord", "Discord", "Chatting"),
            ("discord", "discord", "Discord", "Chatting"),
            ("notepad.exe", "notepad", "Notepad", "Writing"),
            ("gedit", "notepad", "Text Editor", "Writing"),
            ("explorer.exe", "explorer", "File Explorer", "Viewing files"),
            ("nautilus", "explorer", "Files", "Browsing files"),
            ("Photoshop.exe", "photoshop", "Adobe Photoshop", "Editing images"),
            ("photoshop", "photoshop", "Adobe Photoshop", "Editing images"),
            ("gimp", "gimp", "GIMP", "Editing image"),
            ("vlc.exe", "vlc", "VLC Media Player", "Watching video"),
            ("vlc", "vlc", "VLC Media Player", "Watching video"),
            ("spotify.exe", "spotify", "Spotify", "Listening to music"),
            ("spotify", "spotify", "Spotify", "Listening to music"),
            ("steam.exe", "steam", "Steam", "Playing games"),
            ("steam", "steam", "Steam", "Gaming"),
            ("obs64.exe", "obs", "OBS Studio", "Streaming"),
            ("obs", "obs", "OBS Studio", "Streaming"),
            ("zed.exe", "zed", "Zed", "Editing code"),
            ("zed", "zed", "Zed", "Editing code"),
            ("terminal", "terminal", "Terminal", "In terminal"),
            ("gnome-terminal", "terminal", "Terminal", "In terminal"),
            ("konsole", "terminal", "Terminal", "In terminal"),
        ]

        for proc, expected_icon, expected_name, expected_detail in test_cases:
            presence = engine._build_presence(proc, "Sample Title", 1000)
            assert presence.get("large_image") == expected_icon, f"Failed icon for {proc}: {presence}"
            assert presence.get("large_text") == expected_name, f"Failed name for {proc}: {presence}"
            assert presence.get("details") == expected_detail, f"Failed detail for {proc}: {presence}"
            assert presence["state"] == "Sample Title"


def test_unrecognized_process_fallback(mock_rpc_factory):
    """
    Unrecognized processes must fall back to 'Using <process>' without setting large_image.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = os.path.join(tmpdir, "config.json")
        save_config({"client_id": "123456789"}, cfg_path)
        engine = PresenceEngine(
            config_path=cfg_path,
            rpc_factory=mock_rpc_factory,
        )
        assert engine.connect() is True

        # Windows-style unknown process
        win_presence = engine._build_presence("CustomTool.exe", "My Document", 1000)
        assert "large_image" not in win_presence
        assert win_presence["details"] == "Using CustomTool"
        assert win_presence["state"] == "My Document"

        # Windows-style unknown process with uppercase .EXE
        win_presence_upper = engine._build_presence("CustomTool.EXE", "My Document", 1000)
        assert "large_image" not in win_presence_upper
        assert win_presence_upper["details"] == "Using CustomTool"
        assert win_presence_upper["state"] == "My Document"

        # Linux-style unknown process
        linux_presence = engine._build_presence("custom_binary", "Terminal Output", 1000)
        assert "large_image" not in linux_presence
        assert linux_presence["details"] == "Using custom_binary"
        assert linux_presence["state"] == "Terminal Output"


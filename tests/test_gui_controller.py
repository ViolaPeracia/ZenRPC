import os
import tempfile
import pytest

from app.config import save_config, DEFAULT_CONFIG
from app.gui.controller import GUIController
from app.presence import PresenceEngine


@pytest.fixture
def mock_gui_controller(mock_rpc_factory, tmp_path):
    cfg_file = str(tmp_path / "config.json")
    save_config({"client_id": "1234567890", "update_interval": 20}, cfg_file)

    state = ["Code.exe", "test.py - VS Code"]

    def mock_detector():
        return state[0], state[1]

    engine = PresenceEngine(
        config_path=cfg_file,
        detector_fn=mock_detector,
        rpc_factory=mock_rpc_factory,
    )

    controller = GUIController(engine=engine, config_path=cfg_file)
    return controller, engine, state, cfg_file


def test_controller_initial_state(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    s = controller.get_state()

    assert s["running"] is False
    assert s["connected"] is False
    assert s["locked"] is False
    assert s["client_id"] == "1234567890"
    assert s["update_interval"] == 20
    assert s["app_name"] == "Idle"


def test_controller_state_after_update(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.connect() is True
    engine.running = True
    engine.update_once()

    s = controller.get_state()
    assert s["connected"] is True
    assert s["running"] is True
    assert s["proc_name"] == "Code.exe"
    assert s["app_name"] == "Visual Studio Code"
    assert s["icon_key"] == "vscode"
    assert s["state_text"] == "test.py - VS Code"


def test_controller_toggle_rpc(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.running is False

    # Start RPC
    res = controller.toggle_rpc()
    assert res is True
    assert engine.running is True

    # Stop RPC
    res = controller.toggle_rpc()
    assert res is False
    assert engine.running is False


def test_controller_toggle_lock(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.locked is False

    controller.toggle_lock()
    assert engine.locked is True
    s = controller.get_state()
    assert s["locked"] is True
    assert s["locked_proc"] == "Code.exe"

    controller.toggle_lock()
    assert engine.locked is False
    s = controller.get_state()
    assert s["locked"] is False


def test_controller_save_settings_clamped(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller

    # Test interval clamping below 15
    cfg = controller.save_settings(update_interval=5)
    assert cfg["update_interval"] == 15

    cfg = controller.save_settings(update_interval=30)
    assert cfg["update_interval"] == 30

    cfg = controller.save_settings(client_id="999888777")
    assert cfg["client_id"] == "999888777"
    assert controller.get_state()["client_id"] == "999888777"

    # Test toggling boolean settings and reconnect delay
    cfg = controller.save_settings(
        reconnect_delay=10,
        clear_on_idle=False,
        show_window_title=False,
        minimize_to_tray=False,
    )
    assert cfg["reconnect_delay"] == 10
    assert cfg["clear_on_idle"] is False
    assert cfg["show_window_title"] is False
    assert cfg["minimize_to_tray"] is False

    st = controller.get_state()
    assert st["reconnect_delay"] == 10
    assert st["clear_on_idle"] is False
    assert st["show_window_title"] is False
    assert st["minimize_to_tray"] is False


def test_format_elapsed_time():
    from app.gui.controller import format_elapsed_time

    assert format_elapsed_time(-5) == "00:00"
    assert format_elapsed_time(0) == "00:00"
    assert format_elapsed_time(45) == "00:45"
    assert format_elapsed_time(65) == "01:05"
    assert format_elapsed_time(3600) == "01:00:00"
    assert format_elapsed_time(3665) == "01:01:05"



def test_controller_mapping_crud(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller

    # Initially empty user mappings
    assert controller.get_user_mappings() == {}

    # All mappings should include built-in defaults
    all_maps = controller.get_all_mappings()
    assert "code" in all_maps
    assert "orca" in all_maps

    # Add mapping
    controller.save_mapping(
        proc_name="my_custom_tool",
        display_name="Custom Tool",
        icon_key="terminal",
        detail_text="Working on custom tool",
    )

    user_maps = controller.get_user_mappings()
    assert "my_custom_tool" in user_maps
    assert user_maps["my_custom_tool"]["name"] == "Custom Tool"
    assert user_maps["my_custom_tool"]["icon"] == "terminal"

    # Verify all mappings now includes custom tool
    all_maps = controller.get_all_mappings()
    assert "my_custom_tool" in all_maps

    # Delete mapping
    deleted = controller.delete_mapping("my_custom_tool")
    assert deleted is True
    assert "my_custom_tool" not in controller.get_user_mappings()

    # Deleting non-existent mapping returns False
    assert controller.delete_mapping("non_existent") is False

    # Empty proc name raises ValueError
    with pytest.raises(ValueError):
        controller.save_mapping("", "Name", "icon", "detail")


def test_controller_listeners(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller

    received = []

    def on_update(st):
        received.append(st)

    controller.add_listener(on_update)
    controller.poll_update()

    assert len(received) == 1
    assert received[0]["client_id"] == "1234567890"

    controller.remove_listener(on_update)
    controller.poll_update()
    assert len(received) == 1


def test_engine_get_current_presence_api(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.connect() is True
    engine.running = True

    expected_keys = {
        "proc_name",
        "app_name",
        "details",
        "window_title",
        "state",
        "large_image",
        "large_text",
        "start",
        "payload",
        "active",
    }

    # When idle/no proc
    engine.current_proc = None
    presence = engine.get_current_presence()
    assert set(presence.keys()) == expected_keys
    assert presence["active"] is False
    assert presence["app_name"] == "Idle"
    assert presence["details"] == "No active application"
    assert presence["window_title"] == ""
    assert presence["state"] == "Idle"

    # When active proc
    engine.update_once()
    presence = engine.get_current_presence()
    assert set(presence.keys()) == expected_keys
    assert presence["active"] is True
    assert presence["proc_name"] == "Code.exe"
    assert presence["app_name"] == "Visual Studio Code"
    assert presence["large_image"] == "vscode"
    assert presence["large_text"] == "Visual Studio Code"
    assert presence["window_title"] == "test.py - VS Code"
    assert presence["state"] == "test.py - VS Code"
    assert presence["start"] == engine.current_proc_start_time
    assert presence["payload"] is not None


def test_presence_explicit_window_title_and_state_separation(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.connect() is True
    engine.running = True

    # 1. With show_window_title = True (default)
    state[0] = "Code.exe"
    state[1] = "document.txt - Editor"
    engine.update_once()

    presence = engine.get_current_presence()
    assert presence["window_title"] == "document.txt - Editor"
    assert presence["state"] == "document.txt - Editor"
    assert presence["payload"]["state"] == "document.txt - Editor"

    st = controller.get_state()
    assert st["window_title"] == "document.txt - Editor"
    assert st["state"] == "document.txt - Editor"
    assert st["state_text"] == "document.txt - Editor"

    # 2. With show_window_title = False -> state is None, but window_title is preserved
    controller.save_settings(show_window_title=False)
    engine.last_state = None  # Reset last state to force presence rebuild
    engine.update_once()

    presence = engine.get_current_presence()
    assert presence["window_title"] == "document.txt - Editor"
    assert presence["state"] is None
    assert presence["payload"]["state"] is None

    st = controller.get_state()
    assert st["window_title"] == "document.txt - Editor"
    assert st["state"] is None
    assert st["state_text"] == ""


def test_presence_mapping_with_icon(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.connect() is True
    engine.running = True

    state[0] = "Code.exe"
    state[1] = "main.py"
    engine.update_once()

    presence = engine.get_current_presence()
    assert presence["app_name"] == "Visual Studio Code"
    assert presence["large_image"] == "vscode"
    assert presence["large_text"] == "Visual Studio Code"
    assert presence["payload"]["large_image"] == "vscode"
    assert presence["payload"]["large_text"] == "Visual Studio Code"

    st = controller.get_state()
    assert st["app_name"] == "Visual Studio Code"
    assert st["icon_key"] == "vscode"


def test_presence_mapping_without_icon(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.connect() is True
    engine.running = True

    # Register custom mapping with display name & detail, but NO icon
    controller.save_mapping(
        proc_name="cli_tool",
        display_name="My Custom CLI",
        icon_key="",
        detail_text="Compiling binaries",
    )

    state[0] = "cli_tool"
    state[1] = "Terminal Window"
    engine.update_once()

    presence = engine.get_current_presence()
    assert presence["proc_name"] == "cli_tool"
    assert presence["app_name"] == "My Custom CLI"
    assert presence["details"] == "Compiling binaries"
    assert presence["large_image"] is None
    assert presence["large_text"] is None
    assert "large_image" not in presence["payload"]
    assert "large_text" not in presence["payload"]

    # Verify controller state uses mapped display name even without large_text in payload
    st = controller.get_state()
    assert st["app_name"] == "My Custom CLI"
    assert st["detail"] == "Compiling binaries"
    assert st["icon_key"] is None


def test_presence_idle_and_rpc_disabled_states(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    expected_keys = {
        "proc_name",
        "app_name",
        "details",
        "window_title",
        "state",
        "large_image",
        "large_text",
        "start",
        "payload",
        "active",
    }

    # Case A: RPC Disabled (running = False)
    engine.running = False
    p_disabled = engine.get_current_presence()
    assert set(p_disabled.keys()) == expected_keys
    assert p_disabled["active"] is False
    assert p_disabled["proc_name"] is None
    assert p_disabled["app_name"] == "Idle"
    assert p_disabled["details"] == "No active application"
    assert p_disabled["window_title"] == ""
    assert p_disabled["state"] == "RPC Disabled"
    assert p_disabled["large_image"] is None
    assert p_disabled["large_text"] is None
    assert p_disabled["start"] is None
    assert p_disabled["payload"] is None

    st_disabled = controller.get_state()
    assert st_disabled["running"] is False
    assert st_disabled["app_name"] == "Idle"
    assert st_disabled["state_text"] == "RPC Disabled"

    # Case B: Idle while running (running = True, current_proc = None)
    engine.running = True
    engine.current_proc = None
    p_idle = engine.get_current_presence()
    assert set(p_idle.keys()) == expected_keys
    assert p_idle["active"] is False
    assert p_idle["proc_name"] is None
    assert p_idle["app_name"] == "Idle"
    assert p_idle["details"] == "No active application"
    assert p_idle["window_title"] == ""
    assert p_idle["state"] == "Idle"
    assert p_idle["large_image"] is None
    assert p_idle["large_text"] is None
    assert p_idle["start"] is None
    assert p_idle["payload"] is None

    st_idle = controller.get_state()
    assert st_idle["running"] is True
    assert st_idle["app_name"] == "Idle"
    assert st_idle["state_text"] == "Idle"


def test_controller_timer_derivation_and_app_switch(mock_gui_controller):
    controller, engine, state, cfg_file = mock_gui_controller
    assert engine.connect() is True
    engine.running = True

    state[0] = "Code.exe"
    state[1] = "file1.py"
    engine.update_once()

    s1 = controller.get_state()
    start_ts_initial = s1["start_ts"]
    assert s1["proc_name"] == "Code.exe"
    assert s1["start_ts"] == engine.current_proc_start_time

    # Title-only change preserves start_ts
    state[1] = "file2.py"
    engine.update_once()
    s2 = controller.get_state()
    assert s2["start_ts"] == start_ts_initial

    # App switch resets start_ts
    state[0] = "firefox.exe"
    state[1] = "Mozilla Firefox"
    engine.update_once()
    s3 = controller.get_state()
    assert s3["proc_name"] == "firefox.exe"
    assert s3["app_name"] == "Firefox"
    assert s3["start_ts"] == engine.current_proc_start_time


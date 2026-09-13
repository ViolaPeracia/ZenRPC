import logging
import os
import time
from typing import Callable, Dict, List, Optional

from app.config import DEFAULT_CONFIG, get_config_path, load_config, save_config
from app.presence import PresenceEngine

logger = logging.getLogger("zenrpc.gui")


def format_elapsed_time(seconds: int) -> str:
    """Formats integer seconds into MM:SS or HH:MM:SS string."""
    if seconds < 0:
        seconds = 0
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


class GUIController:
    """
    Decoupled view-model / controller layer connecting the GUI dashboard
    to the underlying PresenceEngine and configuration system.
    """

    def __init__(self, engine: Optional[PresenceEngine] = None, config_path: Optional[str] = None):
        self.config_path = config_path or get_config_path()
        self.engine = engine or PresenceEngine(config_path=self.config_path)
        self._listeners: List[Callable[[Dict], None]] = []
        self._last_state_snapshot: Optional[Dict] = None

    def add_listener(self, listener: Callable[[Dict], None]) -> None:
        """Registers an observer callback invoked when application state updates."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[Dict], None]) -> None:
        """Removes a registered observer callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def notify_listeners(self, state: Dict) -> None:
        """Dispatches state update to all registered observers."""
        for listener in list(self._listeners):
            try:
                listener(state)
            except Exception as e:
                logger.debug("Error in state listener: %s", e)

    def get_state(self) -> Dict:
        """
        Constructs a read-only snapshot of current engine and presence state.
        Consumes public presence state from engine without duplicating presence construction logic.
        Never blocks the background loop.
        """
        engine = self.engine
        running = bool(engine.running)
        connected = bool(engine.connected)
        locked = bool(engine.locked)

        # Consume current presence directly from engine public API
        cur_presence = engine.get_current_presence()

        proc_name = cur_presence.get("proc_name")
        start_ts = cur_presence.get("start")
        window_title = cur_presence.get("window_title", "")
        state_val = cur_presence.get("state")

        elapsed_seconds = 0
        if start_ts and running and proc_name:
            elapsed_seconds = max(0, int(time.time() - start_ts))

        return {
            "running": running,
            "connected": connected,
            "locked": locked,
            "locked_proc": engine.locked_proc,
            "proc_name": proc_name,
            "app_name": cur_presence.get("app_name", "Idle"),
            "detail": cur_presence.get("details", "No active application"),
            "state_text": state_val or "",
            "state": state_val,
            "window_title": window_title,
            "icon_key": cur_presence.get("large_image"),
            "elapsed_seconds": elapsed_seconds,
            "start_ts": start_ts,
            "payload": cur_presence.get("payload"),
            "client_id": engine.config.get("client_id", ""),
            "update_interval": max(15, int(engine.config.get("update_interval", 15))),
            "reconnect_delay": int(engine.config.get("reconnect_delay", 30)),
            "clear_on_idle": bool(engine.config.get("clear_on_idle", True)),
            "show_window_title": bool(engine.config.get("show_window_title", True)),
            "minimize_to_tray": bool(engine.config.get("minimize_to_tray", True)),
        }

    def poll_update(self) -> Dict:
        """
        Called on timer tick by UI thread. Evaluates current state
        and notifies observers if changed.
        """
        current = self.get_state()
        self._last_state_snapshot = current
        self.notify_listeners(current)
        return current

    def toggle_rpc(self) -> bool:
        """Toggles PresenceEngine on/off."""
        if self.engine.running:
            self.engine.stop()
        else:
            self.engine.start()
        return self.engine.running

    def toggle_lock(self) -> bool:
        """Toggles presence lock mode."""
        self.engine.toggle_lock()
        return self.engine.locked

    def reload_config(self) -> None:
        """Reloads configuration from disk into engine."""
        self.engine.reload_config()

    def get_raw_config(self) -> Dict:
        """Reads raw config dictionary directly from disk without default merging."""
        import json
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception as e:
            logger.debug("Failed reading raw config at %s: %s", self.config_path, e)
        return {}

    def get_config(self) -> Dict:
        """Returns validated configuration dictionary with defaults merged."""
        return load_config(self.config_path)

    def save_settings(
        self,
        client_id: Optional[str] = None,
        update_interval: Optional[int] = None,
        reconnect_delay: Optional[int] = None,
        clear_on_idle: Optional[bool] = None,
        show_window_title: Optional[bool] = None,
        minimize_to_tray: Optional[bool] = None,
    ) -> Dict:
        """
        Saves updated core settings while preserving existing custom mappings.
        Enforces minimum 15s interval clamp.
        """
        cfg = self.get_raw_config()

        if client_id is not None:
            cfg["client_id"] = str(client_id).strip()
        if update_interval is not None:
            cfg["update_interval"] = max(15, int(update_interval))
        if reconnect_delay is not None:
            cfg["reconnect_delay"] = max(1, int(reconnect_delay))
        if clear_on_idle is not None:
            cfg["clear_on_idle"] = bool(clear_on_idle)
        if show_window_title is not None:
            cfg["show_window_title"] = bool(show_window_title)
        if minimize_to_tray is not None:
            cfg["minimize_to_tray"] = bool(minimize_to_tray)

        save_config(cfg, self.config_path)
        self.engine.reload_config()
        return self.get_config()

    def get_all_mappings(self) -> Dict[str, Dict]:
        """
        Returns combined dictionary of active mappings:
        built-in defaults merged with user custom mappings.
        """
        cfg = self.get_config()
        combined = dict(DEFAULT_CONFIG["custom_mappings"])
        user_mappings = cfg.get("custom_mappings", {})
        if isinstance(user_mappings, dict):
            combined.update(user_mappings)
        return combined

    def get_user_mappings(self) -> Dict[str, Dict]:
        """Returns only the user's explicit custom mappings from config file."""
        raw = self.get_raw_config()
        mappings = raw.get("custom_mappings", {})
        return dict(mappings) if isinstance(mappings, dict) else {}

    def save_mapping(self, proc_name: str, display_name: str, icon_key: str, detail_text: str) -> None:
        """
        Adds or updates an application mapping in user custom_mappings.
        """
        clean_proc = str(proc_name).strip()
        if not clean_proc:
            raise ValueError("Process name cannot be empty")

        raw = self.get_raw_config()
        if "custom_mappings" not in raw or not isinstance(raw["custom_mappings"], dict):
            raw["custom_mappings"] = {}

        mapping_entry = {
            "name": str(display_name).strip() or clean_proc,
            "detail": str(detail_text).strip() or f"Using {display_name}",
        }
        clean_icon = str(icon_key).strip() if icon_key else ""
        if clean_icon:
            mapping_entry["icon"] = clean_icon

        raw["custom_mappings"][clean_proc] = mapping_entry

        save_config(raw, self.config_path)
        self.engine.reload_config()

    def delete_mapping(self, proc_name: str) -> bool:
        """
        Removes an entry from user custom_mappings.
        Returns True if found and removed, False otherwise.
        """
        clean_proc = str(proc_name).strip()
        raw = self.get_raw_config()
        mappings = raw.get("custom_mappings", {})
        if isinstance(mappings, dict) and clean_proc in mappings:
            del mappings[clean_proc]
            raw["custom_mappings"] = mappings
            save_config(raw, self.config_path)
            self.engine.reload_config()
            return True
        return False

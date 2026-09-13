import logging
import threading
import time
from app.config import load_config
from app.detector import get_active_window_info

logger = logging.getLogger("zenrpc")


def truncate_utf8(text, max_bytes=128):
    """
    Truncates a string so that its encoded UTF-8 representation does not exceed
    max_bytes. Avoids splitting multi-byte Unicode code points.
    """
    if not text:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


class PresenceEngine:
    def __init__(self, config_path=None, detector_fn=None, rpc_factory=None):
        self.config_path = config_path
        self.config = load_config(config_path)
        self.detector_fn = detector_fn or get_active_window_info

        if rpc_factory is not None:
            self.rpc_factory = rpc_factory
        else:
            from pypresence import Presence
            self.rpc_factory = Presence

        self.rpc = None
        self.connected = False
        self.running = False
        self.presence_cleared = False
        self.last_state = None
        self._thread = None
        self._last_reconnect = 0

        # Per-application timing tracking
        self.current_proc = None
        self.current_proc_start_time = int(time.time())

        # Lock mode state
        self.locked = False
        self.locked_proc = None
        self.locked_title = None
        self.locked_since = None

    def reload_config(self):
        """Reloads configuration from disk and resets presence state key."""
        self.config = load_config(self.config_path)
        self.last_state = None
        logger.info("Configuration reloaded.")

    def connect(self):
        """Attempts to establish connection to Discord RPC client."""
        client_id = self.config.get("client_id", "").strip()
        if not client_id or client_id == "YOUR_CLIENT_ID_HERE":
            logger.warning("Client ID not set! Set your client_id in config.json.")
            return False

        try:
            self.rpc = self.rpc_factory(client_id)
            self.rpc.connect()
            self.connected = True
            self._last_reconnect = 0
            logger.info("Connected to Discord RPC successfully.")
            return True
        except Exception as e:
            logger.info("Cannot connect to Discord (%s). Will retry in background.", e)
            self.connected = False
            self._last_reconnect = time.time()
            return False

    def disconnect(self):
        """Safely clears presence and closes RPC socket."""
        if self.connected and self.rpc:
            try:
                self.rpc.clear()
                self.rpc.close()
            except Exception:
                pass
        self.connected = False

    def toggle_lock(self):
        """Toggles lock mode on the currently active application."""
        if not self.locked:
            proc, title = self.detector_fn()
            if proc:
                self.locked = True
                self.locked_proc = proc
                self.locked_title = title
                self.locked_since = int(time.time())
                self.last_state = None
                logger.info("Locked presence to %s", proc)
        else:
            self.locked = False
            self.locked_proc = None
            self.locked_title = None
            self.locked_since = None
            self.last_state = None
            self.current_proc = None
            logger.info("Presence unlocked.")

    def _resolve_mapping(self, proc_name):
        """Resolves process name to display name, detail text, and optional icon key."""
        mappings = self.config.get("custom_mappings", {})
        clean_proc = proc_name[:-4] if proc_name.lower().endswith(".exe") else proc_name

        # Lookup order: exact -> exact clean -> case-insensitive key search
        mapping = (
            mappings.get(proc_name)
            or mappings.get(clean_proc)
            or mappings.get(proc_name.lower())
            or mappings.get(clean_proc.lower())
        )

        if not mapping and isinstance(mappings, dict):
            proc_lower = proc_name.lower()
            clean_lower = clean_proc.lower()
            for key, val in mappings.items():
                if not isinstance(key, str):
                    continue
                k_lower = key.lower()
                k_clean = k_lower[:-4] if k_lower.endswith(".exe") else k_lower
                if k_lower in (proc_lower, clean_lower) or k_clean in (proc_lower, clean_lower):
                    mapping = val
                    break

            if not mapping and (clean_lower.startswith("gimp-") or clean_lower.startswith("gimp_")):
                mapping = mappings.get("gimp")

            if not mapping and (clean_lower in ("discordptb", "discord-ptb", "discord_ptb") or clean_lower.startswith("discordptb")):
                discord_mapping = mappings.get("discord.exe") or mappings.get("discord")
                if discord_mapping and isinstance(discord_mapping, dict):
                    mapping = {
                        "name": "Discord PTB",
                        "icon": discord_mapping.get("icon", "discord"),
                        "detail": discord_mapping.get("detail", "Chatting"),
                    }
                else:
                    mapping = {
                        "name": "Discord PTB",
                        "icon": "discord",
                        "detail": "Chatting",
                    }

        if mapping and isinstance(mapping, dict):
            app_name = mapping.get("name") or clean_proc
            detail = mapping.get("detail") or f"Using {app_name}"
            icon_key = mapping.get("icon")
        else:
            app_name = clean_proc
            detail = f"Using {clean_proc}"
            icon_key = None

        return app_name, detail, icon_key

    def _build_presence(self, proc_name, window_title, start_ts):
        """Constructs and sanitizes the Discord presence payload."""
        app_name, detail, icon_key = self._resolve_mapping(proc_name)

        state = None
        if self.config.get("show_window_title") and window_title:
            state = truncate_utf8(window_title, 128)

        presence = {
            "details": truncate_utf8(detail, 128),
            "state": state,
            "start": start_ts,
            "small_text": "[LOCKED]" if self.locked else "Active",
        }

        if icon_key:
            presence["large_image"] = icon_key
            presence["large_text"] = truncate_utf8(app_name, 128)

        return presence

    def _should_reconnect(self):
        delay = self.config.get("reconnect_delay", 30)
        return (time.time() - self._last_reconnect) >= delay

    def update_once(self):
        """Performs a single presence update cycle."""
        if not self.connected:
            return

        if self.locked and self.locked_proc:
            proc_name = self.locked_proc
            window_title = self.locked_title
            start_ts = self.locked_since
        else:
            proc_name, window_title = self.detector_fn()

            # Idle detection
            if not proc_name:
                if self.config.get("clear_on_idle") and not self.presence_cleared:
                    try:
                        self.rpc.clear()
                        self.presence_cleared = True
                        self.last_state = None
                        self.current_proc = None
                        logger.info("Idle: presence cleared.")
                    except Exception as e:
                        logger.debug("Error clearing presence: %s", e)
                        self.connected = False
                        self._last_reconnect = time.time()
                return

            # Per-application elapsed timer logic:
            # If application changes (e.g. Chrome -> VS Code), reset elapsed timer
            # If only window title changes within same application, PRESERVE timer
            if proc_name != self.current_proc:
                self.current_proc = proc_name
                self.current_proc_start_time = int(time.time())
                logger.debug("Active app changed to %s; timer reset.", proc_name)

            start_ts = self.current_proc_start_time

        state_key = (proc_name, window_title, self.locked)
        if state_key == self.last_state:
            return  # Suppress duplicate update

        presence = self._build_presence(proc_name, window_title, start_ts)
        try:
            self.rpc.update(**presence)
            self.last_state = state_key
            self.presence_cleared = False
            tag = " [LOCKED]" if self.locked else ""
            logger.info("Presence updated%s: %s (%s)", tag, proc_name, (window_title or "")[:40])
        except Exception as e:
            logger.warning("Failed to update presence (%s). Will reconnect.", e)
            self.connected = False
            self._last_reconnect = time.time()

    def _loop(self):
        """Main background loop with interruptible sleep."""
        while self.running:
            if not self.connected:
                if self._should_reconnect():
                    logger.debug("Attempting reconnect to Discord...")
                    self.connect()
            else:
                self.update_once()

            # Interruptible sleep interval
            interval = max(15, int(self.config.get("update_interval", 15)))
            # If disconnected, check reconnect condition every 1 second
            sleep_total = interval if self.connected else 1
            for _ in range(sleep_total):
                if not self.running:
                    break
                time.sleep(1)

    def start(self):
        """
        Starts the background worker thread unconditionally.
        Even if Discord is offline at startup, the thread continues running
        and reconnects automatically when Discord launches.
        """
        if self.running:
            return
        self.running = True
        # Try initial connect non-blocking
        self.connect()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("ZenRPC engine started.")

    def stop(self):
        """Stops the background worker thread and disconnects RPC."""
        self.running = False
        self.disconnect()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("ZenRPC engine stopped.")

    def get_current_presence(self):
        """
        Returns a read-only snapshot dictionary of the current presence state and payload.
        Allows external observers (such as the GUI dashboard) to consume active presence
        information without duplicating detection, timing, or mapping resolution logic.
        """
        if self.locked and self.locked_proc:
            proc_name = self.locked_proc
            window_title = self.locked_title or ""
            start_ts = self.locked_since
        else:
            proc_name = self.current_proc
            last_st = self.last_state
            if last_st and last_st[0] == proc_name:
                window_title = last_st[1] or ""
            else:
                window_title = ""
            start_ts = self.current_proc_start_time

        if not proc_name or not self.running:
            return {
                "active": False,
                "proc_name": None,
                "app_name": "Idle",
                "details": "No active application",
                "window_title": "",
                "state": "Idle" if self.running else "RPC Disabled",
                "large_image": None,
                "large_text": None,
                "start": None,
                "payload": None,
            }

        app_name, detail, icon_key = self._resolve_mapping(proc_name)
        payload = self._build_presence(proc_name, window_title, start_ts or int(time.time()))
        return {
            "active": True,
            "proc_name": proc_name,
            "app_name": app_name,
            "details": payload.get("details", truncate_utf8(detail, 128)),
            "window_title": window_title,
            "state": payload.get("state"),
            "large_image": payload.get("large_image"),
            "large_text": payload.get("large_text"),
            "start": start_ts,
            "payload": payload,
        }


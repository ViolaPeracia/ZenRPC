# Developer Guide — ZenRPC

A practical, lightweight reference for developing, testing, and extending **ZenRPC**.

---

## 1. Codebase Architecture

The project follows a modular, single-responsibility architecture without heavy frameworks or unnecessary abstractions:

```text
ZenRPC/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration loading, validation, and defaults
│   ├── detector.py         # Active-window & process detection (Win32 & X11)
│   └── presence.py         # RPC lifecycle, timer logic, lock mode, and loop
├── tests/
│   ├── conftest.py         # In-memory MockRPC fixture (offline testing)
│   ├── test_config.py      # Configuration tests (merging, clamping, paths)
│   └── test_presence.py    # Presence payload, UTF-8 safety, and timer tests
├── docs/
│   ├── ROADMAP.md          # Living roadmap with milestone & issue checkboxes
│   └── DEVELOPMENT.md      # Developer guide and technical reference
├── main.py                 # Application entry point & pystray system tray loop
├── config.example.json     # Clean configuration template with 28 default rules
├── requirements.txt        # Shared dependencies (pypresence, pystray, Pillow, psutil, pywin32)
└── pytest.ini              # Test runner configuration
```

### Core Execution Flow

```text
[main.py] -> starts PresenceEngine in background daemon thread
          -> enters pystray event loop on main thread (required for OS tray)

[PresenceEngine._loop()]
    │
    ├── Check RPC connection -> connect() / retry with backoff
    │
    └── update_once()
            │
            ├── Check Lock Mode -> use locked app if active
            │
            ├── Call detector_fn() -> get (process_name, window_title)
            │
            ├── Idle check -> clear presence if no window is active
            │
            ├── Timer logic -> reset start_ts if process changes;
            │                  preserve start_ts if title changes within same process
            │
            ├── Dedup check -> skip update if (proc, title, locked) == last_state
            │
            └── rpc.update() -> sanitize strings (truncate_utf8 <= 128 bytes)
```

---

## 2. Local Setup & Testing

### Python Environment

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux:
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running Unit Tests

The test suite runs **100% offline** without requiring a running Discord instance or an interactive desktop session:

```bash
pytest
```

Tests use an in-memory `MockRPC` class defined in `tests/conftest.py` that records presence payloads and simulates connection failures.

---

## 3. Adding Application Mappings

### Built-in Mappings

Built-in mappings are defined in `DEFAULT_CONFIG` inside `app/config.py`. Each entry supports:

```python
"process_name.exe": {
    "name": "Display Name",       # App name shown in Discord tooltip
    "icon": "asset_key",          # Large image key from Discord Developer Portal
    "detail": "Activity text"     # Custom details text (e.g. "Editing code")
}
```

### Matching Semantics

The presence builder (`PresenceEngine._build_presence`) resolves process names using the following priority order:

1. **Exact match:** `mappings.get(proc_name)`
2. **Clean match:** `mappings.get(clean_proc)` (stripping `.exe`)
3. **Lowercase exact:** `mappings.get(proc_name.lower())`
4. **Lowercase clean:** `mappings.get(clean_proc.lower())`
5. **Case-insensitive search:** Iterating user mappings to match case variations.
6. **Fallback:** If no mapping matches, displays `Using <clean_proc>` with active window title and no icon.

---

## 4. Platform Implementation Notes

### Windows (Win32 + psutil)
- **Active Window:** `win32gui.GetForegroundWindow()` retrieves the focused HWND.
- **Process ID:** `win32process.GetWindowThreadProcessId(hwnd)` extracts the thread PID.
- **Process Name:** `psutil.Process(pid).name()` safely resolves the executable name.
- **Silent Launch:** `main.py` hides the console window via `ctypes.windll.user32.ShowWindow(hwnd, 0)` when launched outside an interactive terminal. `run.bat` uses `pythonw.exe`.

### Linux (X11 / XWayland)
- **Active Window & PID:** `xdotool getactivewindow` and `xdotool getwindowpid` run with strict 2-second subprocess timeouts to prevent hanging.
- **Binary Detection:** Process names are parsed directly from `/proc/<pid>/cmdline` to bypass the 15-character truncation limit of `/proc/<pid>/comm`.
- **Wayland Policy:** Due to Wayland security restrictions on querying other clients, pure Wayland sessions gracefully degrade to an idle state (`None, None`) rather than crashing.

---

## 5. Development Workflow & Task Tracking

All active and planned tasks are tracked via GitHub Milestones and mirrored in `docs/ROADMAP.md`:

- **Active Milestone:** `M2.6-W — Windows Stabilization` (Issues #1–#5)
- **Upcoming Milestone:** `M2.7-W — Windows Release Baseline` (Issues #6–#8)
- **Planned Milestone:** `M3-L — Linux Stabilization` (Issues #9–#14)
- **Deferred Milestone:** `M4 — Optional Cross-Platform Features` (Issues #15–#18)

When implementing changes:
1. Always run `pytest` before and after modifying code.
2. Keep platform-specific code strictly inside `app/detector.py`.
3. Preserve all 28 existing process rules and 14 asset keys.
4. Check off completed items in `docs/ROADMAP.md`.

# Discord RPC Watcher — Personal Roadmap

## 1. Project Goal
A small, reliable, lightweight background utility for broadcasting active window context to Discord Rich Presence on the owner's personal Windows and Linux machines.

## 2. Current State
- **Consolidated Implementation:** Unified under `main.py` and `app/` package, eliminating the legacy `Windows/` and `Linux/` split.
- **Reliability:** Background reconnect loop starts unconditionally, active window timer resets on application switch and persists on title-only changes, configuration paths resolve relative to script directory, and presence strings are capped at 128 UTF-8 bytes.
- **Testing:** Offline test suite in `tests/` verifying configuration fallbacks, timer resets, and UTF-8 truncation boundaries.

## 3. Target Architecture
```text
discord-rpc/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration loading, defaults, script-relative paths
│   ├── detector.py         # Active-window detection (Windows Win32 & Linux X11)
│   └── presence.py         # Discord RPC lifecycle, reconnect loop, per-app timers
├── tests/
│   ├── conftest.py         # Mock RPC transport
│   ├── test_config.py      # Config loading and validation tests
│   └── test_presence.py    # Presence payload and timer reset tests
├── docs/
│   └── ROADMAP.md          # Single living roadmap
├── main.py                 # Application entry point & pystray tray UI loop
├── config.example.json     # Tracked default configuration template
├── requirements.txt        # Shared dependencies
├── README.md               # Accurate documentation
├── LICENSE                 # Repository license
└── .gitignore              # Ignores config.json, __pycache__, .venv
```

## 4. Core Reliability Directives
1. **Startup Reconnect:** The worker loop runs unconditionally. If Discord is closed at startup, the watcher stays alive and retries automatically with backoff.
2. **Per-App Timers:** The elapsed timer resets when switching between different applications, but continues running when only the window title changes within the same app.
3. **Predictable Paths:** `config.json` is always resolved relative to the script directory, never the process working directory.
4. **UTF-8 Safety:** String fields are capped at 128 UTF-8 bytes without slicing multi-byte code points.

## 5. Linux & Wayland Policy
- **X11 / XWayland:** Supported via `xdotool` with strict 2-second timeouts and direct `/proc/<pid>/cmdline` reads.
- **Native Wayland:** No generic support due to Wayland's security architecture restricting cross-client window inspection. Sessions degrade gracefully to an idle state without crashing.
- **Compositor IPC (Sway / Hyprland):** Deferred/on-demand. Only implement if the owner actively uses one of these compositors.

## 6. Testing & Verification
Local unit testing via `pytest` (15 offline tests passing without requiring Discord or a GUI):
- `tests/test_config.py`: Config loading, automatic merging of built-in defaults with user custom mappings, malformed JSON fallback, rate-limit clamping (>=15s), script-relative path resolution.
- `tests/test_presence.py`: Per-app timer resets, title-only continuity, UTF-8 byte boundary truncation (ASCII & multi-byte), lock mode semantics, worker thread persistence during Discord downtime, pre-migration process and asset key parity (28 rules across 14 asset keys), and unrecognized process fallback behavior.

## 7. Configuration Strategy
- `config.example.json` is committed as the clean default template with all 28 recognized process rules.
- `config.json` is local-only and ignored via `.gitignore` to avoid committing personal application IDs.
- User mappings in `config.json` are automatically merged with `DEFAULT_CONFIG` so adding or overriding individual apps does not lose built-in mappings.

## 8. Milestones & Status

### Completed Baseline
- **M1 — Consolidation & Core Reliability:** [COMPLETED]
  - Merged Windows & Linux into `app/` and root `main.py`
  - Fixed startup connection stall and automatic reconnect
  - Implemented per-app elapsed timers (persisting on title change)
  - Fixed configuration path resolution relative to script base directory
  - Added offline pytest suite
  - Cleaned launch and install scripts
  - Added tray-controlled "Lock to Current App" mode
- **M2 — Linux & Platform Reliability:** [COMPLETED]
  - Added strict 2-second timeouts to `xdotool` calls
  - Direct `/proc/<pid>/cmdline` parsing for robust binary detection
  - Corrected Wayland documentation and ensured graceful degradation without crashing
- **M2.5 — Post-Migration Process & Asset Parity Audit:** [COMPLETED]
  - Complete inventory of pre-migration process recognition rules (all 28 process rules across 14 asset keys verified)
  - Preserved exact Discord asset keys (`vscode`, `chrome`, `firefox`, `discord`, `notepad`, `explorer`, `photoshop`, `gimp`, `vlc`, `spotify`, `steam`, `obs`, `zed`, `terminal`)
  - Implemented case-insensitive and `.exe`-extension-agnostic matching
  - Maintained identical unrecognized process fallback (`Using <process>`)
  - Added comprehensive automated parity tests in `tests/test_presence.py`

---

### Active Development: Windows Priority (CURRENT FOCUS)

- **M2.6-W — Windows Stabilization:** [ACTIVE / IN PROGRESS]
  - **Windows runtime baseline verification:** Verify on real Windows environment across Discord offline/restart cycles, process switching, title continuity, lock mode, and live reload (#1)
  - **Windows detector reliability:** Harden Win32 foreground window, PID, and `psutil` process resolution against null HWND, vanished PIDs, and access errors (#2)
  - **Windows detector unit tests:** Add offline tests mocking `win32gui`, `win32process`, and `psutil` error branches (#3)
  - **Windows launcher and startup behavior:** Audit `run.bat`, `pythonw.exe`, console suppression, and ensure working-directory independence (#4)
  - **Windows process & asset mapping parity check:** Verify exact parity across all 28 recognized rules and 14 asset keys (#5)

- **M2.7-W — Windows Release Baseline:** [UPCOMING]
  - **Windows end-to-end verification checklist:** Validate full user lifecycle from clean clone and dependency install to tray shutdown (#6)
  - **Windows documentation and usage verification:** Align `README.md` strictly with implemented features and controls (#7)
  - **Windows release baseline:** Final verification gate certifying stable source-based Windows operation (#8)

---

### Planned Development: Linux Follow-up (IMMEDIATE NEXT)

- **M3-L — Linux Stabilization:** [PLANNED — AFTER WINDOWS]
  - **Linux X11/XWayland runtime verification:** Real desktop verification of `xdotool` active window detection, timer resets, and tray controls (#9)
  - **Linux process detection reliability:** Audit `/proc/<pid>/cmdline` parsing to prevent comm 15-character truncation and handle disappearing processes (#10)
  - **Linux subprocess safety tests:** Add offline unit tests for `_run_cmd` covering timeouts, non-zero exits, and missing tools (#11)
  - **Linux desktop launcher verification:** Audit `discord-rpc.desktop` for path, working directory, and desktop menu execution (#12)
  - **Linux native Wayland behavior & documentation:** Document boundary between X11, XWayland, and native Wayland graceful degradation (#13)
  - **Linux release baseline:** Final verification gate certifying stable source-based Linux operation (#14)

---

### Deferred Development: Optional Cross-Platform Features

- **M4 — Optional Cross-Platform Features:** [DEFERRED / POST-STABILIZATION]
  - **Native compositor IPC support:** Optional Hyprland/Sway/Niri IPC modules without contaminating core presence logic (#15)
  - **Privacy filtering:** Local process blacklist, title masking, and tray Private Mode (#16)
  - **Persistent file logging:** Optional rotating local file handler for headless troubleshooting (#17)
  - **Optional standalone packaging:** Evaluate PyInstaller build for source-free distribution (#18)


## 9. Python vs. Rust Decision Gate
- **Decision:** Keep Python. It is simple, easily hackable, and uses negligible resources on a modern desktop.
- **Reconsideration Triggers:** Re-evaluate Rust only if:
  1. Measured memory usage is proven to be a practical problem on the owner's system.
  2. A native Wayland compositor setup requires low-level D-Bus/socket integration that Python cannot handle cleanly.
  3. Multi-machine deployment without Python makes standalone binaries necessary.

## 10. Explicitly Rejected Work
No web/Qt UI, no Electron, no databases, no cloud sync, no accounts, no telemetry, no plugin architecture, no enterprise CI/CD.

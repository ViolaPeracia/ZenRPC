# ZenRPC — Personal Roadmap

## 1. Project Goal
A small, reliable, lightweight background utility for broadcasting active window context to Discord Rich Presence on the owner's personal Windows and Linux machines.

## 2. Current State
- **Consolidated Implementation:** Unified under `main.py` and `app/` package, eliminating the legacy `Windows/` and `Linux/` split.
- **Reliability:** Background reconnect loop starts unconditionally, active window timer resets on application switch and persists on title-only changes, configuration paths resolve relative to script directory, and presence strings are capped at 128 UTF-8 bytes.
- **Testing:** Offline test suite in `tests/` verifying configuration fallbacks, timer resets, and UTF-8 truncation boundaries.

## 3. Target Architecture
```text
ZenRPC/
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
Local unit testing via `pytest` (71 offline tests passing without requiring Discord or a GUI):
- `tests/test_config.py`: Config loading, automatic merging of built-in defaults with user custom mappings, malformed JSON fallback, rate-limit clamping (>=15s), script-relative path resolution, working-directory independence (`test_cwd_independence`, `test_external_cwd_subprocess_resolution`, `test_run_sh_script_cwd_independence`, `test_run_sh_execution_from_external_cwd`, and `test_desktop_entry_syntax_and_exec`).
- `tests/test_detector.py`: Windows active-window detection tests mocking `win32gui`, `win32process`, and `psutil` covering 16+ edge cases (HWND=0/None, invalid PID, `NoSuchProcess`, `AccessDenied`, `ZombieProcess`, empty/whitespace/Unicode titles, recognized/unrecognized mappings).
- `tests/test_linux_detector.py`: Comprehensive Linux subprocess safety and procfs boundary tests (31 tests mocking `_run_cmd`, `subprocess.check_output`, and `/proc` files, covering `xdotool` timeouts, non-zero exits, missing binaries, invalid/missing PIDs, process disappearance before `/proc` read, permission errors, malformed `cmdline`, fallback to `comm`, multibyte Unicode titles, empty titles, Wayland graceful degradation to idle, and public `get_active_window_info()` dispatch).
- `tests/test_presence.py`: Per-app timer resets, title-only continuity, UTF-8 byte boundary truncation (ASCII & multi-byte), lock mode semantics, worker thread persistence during Discord downtime, idle presence clearing/recovery, disconnect recovery, live config reload, tray icon colors, expanded catalog recognition (including Orca and 144 rules across 59 applications), art assets integrity (all 59 512x512 PNGs validated), and unrecognized process fallback behavior.
- `tests/verify_linux_runtime.py`: Live Linux X11/XWayland runtime verification harness validating real foreground-window detection on DISPLAY=:1, 2-second timeouts, multibyte Unicode titles, timer preservation on title changes, timer resets on app switching, window destroy idle clearing, and clean SIGINT/SIGTERM shutdown.

## 7. Configuration Strategy
- `config.example.json` is committed as the clean default template with all 144 recognized process rules.
- `config.json` is local-only and ignored via `.gitignore` to avoid committing personal application IDs.
- User mappings in `config.json` are automatically merged with `DEFAULT_CONFIG` so adding or overriding individual apps does not lose built-in mappings.

## 8. Milestones & Task Tracking

### Completed Milestones
- [x] **M1 — Consolidation & Core Reliability**
  - [x] Merged Windows & Linux into `app/` and root `main.py`
  - [x] Fixed startup connection stall and automatic reconnect
  - [x] Implemented per-app elapsed timers (persisting on title change)
  - [x] Fixed configuration path resolution relative to script base directory
  - [x] Added offline pytest suite
  - [x] Cleaned launch and install scripts
  - [x] Added tray-controlled "Lock to Current App" mode
- [x] **M2 — Linux & Platform Reliability**
  - [x] Added strict 2-second timeouts to `xdotool` calls
  - [x] Direct `/proc/<pid>/cmdline` parsing for robust binary detection
  - [x] Corrected Wayland documentation and ensured graceful degradation without crashing
- [x] **M2.5 — Post-Migration Process & Asset Parity Audit**
  - [x] Complete inventory of pre-migration process recognition rules (all 28 process rules across 14 asset keys verified)
  - [x] Preserved exact Discord asset keys (`vscode`, `chrome`, `firefox`, `discord`, `notepad`, `explorer`, `photoshop`, `gimp`, `vlc`, `spotify`, `steam`, `obs`, `zed`, `terminal`)
  - [x] Implemented case-insensitive and `.exe`-extension-agnostic matching
  - [x] Maintained identical unrecognized process fallback (`Using <process>`)
  - [x] Added comprehensive automated parity tests in `tests/test_presence.py`
- [x] **M2.6-W — Windows Stabilization**
  - [x] **#1** — `[Windows] Windows runtime baseline verification`
    - [x] Discord running before watcher starts
    - [x] Discord offline at startup with automatic background reconnect
    - [x] Discord closing and restarting while watcher stays alive
    - [x] Application switching (timer reset) and window title changes (timer preserved)
    - [x] Process replacement / exit handling
    - [x] Lock and unlock modes via system tray
    - [x] Live configuration reload from tray menu
    - [x] Rate-limit interval handling and clamp (>=15s)
    - [x] Multi-byte UTF-8 window titles
    - [x] Tray icon visual indicator (Blurple active, Red locked)
    - [x] Clean shutdown and presence clearing
  - [x] **#2** — `[Windows] Windows detector reliability`
    - [x] Guard against null / zero HWND (desktop, lock screen)
    - [x] Safe PID validation (`pid <= 0`)
    - [x] Handle process disappearing between PID and name lookup (`NoSuchProcess`)
    - [x] Handle permission and access restrictions (`AccessDenied`)
    - [x] Empty process name and empty title handling
    - [x] Unicode title safety
    - [x] Terminated / zombie process handling
  - [x] **#3** — `[Windows] Windows detector unit tests`
    - [x] Offline test suite mocking `win32gui`, `win32process`, and `psutil`
    - [x] Valid foreground window test
    - [x] Missing HWND / invalid PID test
    - [x] Process disappearing / permission error branch tests
    - [x] Empty and multibyte title tests
    - [x] Recognized and fallback process lookup tests
  - [x] **#4** — `[Windows] Windows launcher and startup behavior`
    - [x] Audit `run.bat` and `install.bat`
    - [x] Console window suppression (`ShowWindow(hwnd, 0)` and `pythonw.exe`)
    - [x] Working-directory-independent `config.json` resolution
    - [x] Windows Startup folder (`shell:startup`) shortcut compatibility
  - [x] **#5** — `[Windows] Windows configuration and process-mapping parity check`
    - [x] Parity validation across all 28 process rules and 14 Discord asset keys
    - [x] Case-insensitive matching (`CHROME.EXE`, `code.exe`)
    - [x] Extension-agnostic matching (`.exe` stripped or present)
    - [x] Custom mapping merge and default preservation
- [x] **M2.7-W — Windows Release Baseline**
  - [x] **#6** — `[Windows] Windows end-to-end verification checklist`
    - [x] Clean clone, dependency install, config creation, tray launch, Discord sync, and exit
    - [x] Record verification evidence
  - [x] **#7** — `[Windows] Windows documentation and usage verification`
    - [x] Audit `README.md` against actual Windows implementation
    - [x] Verify installation, run options, tray controls, and limitations
  - [x] **#8** — `[Windows] Windows release baseline`
    - [x] Final verification gate certifying stable source-based Windows release

---

- [x] **M3-L — Linux Stabilization**
  - [x] **#9** — `[Linux] Linux X11/XWayland runtime verification`
    - [x] `xdotool` active window ID and PID resolution on physical X11/XWayland desktop (`DISPLAY=:1`)
    - [x] Application switching and timer resets
    - [x] Title changes and timer preservation
    - [x] Subprocess timeout enforcement (strict 2s timeout, no hanging calls)
    - [x] Verified via `tests/verify_linux_runtime.py` covering all 10 runtime checks
  - [x] **#10** — `[Linux] Linux process detection reliability`
    - [x] Direct `/proc/<pid>/cmdline` binary parsing extracting argv basename
    - [x] Handle terminated processes, malformed data, and sandboxed `/proc`
    - [x] Secondary fallback to `/proc/<pid>/comm`
    - [x] Return `None` on resolution failure to cleanly isolate from `PresenceEngine`
  - [x] **#11** — `[Linux] Linux subprocess safety tests`
    - [x] 31 offline unit tests in `tests/test_linux_detector.py` mocking `_run_cmd`, subprocess, and `/proc`
    - [x] Subprocess timeout expired, command not found, non-zero exit, and Unicode coverage
  - [x] **#12** — `[Linux] Linux desktop launcher verification`
    - [x] CWD-independent root launcher `run.sh` resolving `APP_DIR` dynamically
    - [x] Validated `zenrpc.desktop` desktop file syntax conforming to FreeDesktop KeyFile specs
    - [x] Automated CWD independence tests in `tests/test_config.py`
  - [x] **#13** — `[Linux] Linux native Wayland behavior and documentation`
    - [x] `is_wayland()` detection via `WAYLAND_DISPLAY` and `XDG_SESSION_TYPE`
    - [x] Graceful degradation to idle on pure Wayland sessions without crashing
    - [x] Support boundary clarification (X11 & XWayland supported; pure Wayland fallback to idle)
  - [x] **#14** — `[Linux] Linux release baseline`
    - [x] Final verification gate certifying stable source-based Linux release across 71 offline tests and 10 live runtime checks

---

### Deferred Development: Optional Cross-Platform Features

#### Milestone: M4 — Optional Cross-Platform Features
- [ ] **#15** — `[Cross-platform] Native compositor IPC support` (Hyprland / Sway / Niri)
- [ ] **#16** — `[Cross-platform] Privacy filtering` (Process/app blacklist, title masking, Private Mode)
- [ ] **#17** — `[Cross-platform] Persistent file logging` (Rotating local log file)
- [ ] **#18** — `[Cross-platform] Optional standalone packaging` (PyInstaller single-file build)

---

### Mini-Milestones & Enhancements

#### Milestone: M-GUI — Lightweight Desktop GUI Dashboard
- [ ] **#20** — `[GUI] Lightweight desktop GUI dashboard for status monitoring and configuration` *(Linux phase complete; Windows phase in progress)*
  - [x] (Linux) Decoupled GUIController view-model with observer pattern (`app/gui/controller.py`)
  - [x] (Linux) CustomTkinter desktop dashboard with real-time Discord presence profile card preview (`app/gui/dashboard.py`)
  - [x] (Linux) Connection status badge (Connected / Reconnecting / RPC Disabled) and lock status indicator
  - [x] (Linux) Quick action controls: Enable/Disable RPC, Lock/Unlock presence, Reload config, Minimize to Tray
  - [x] (Linux) Visual application mapping manager with search filtering, add/edit form, delete actions, and pagination
  - [x] (Linux) Visual settings configuration (Client ID, interval slider with $\ge$ 15s rate-limit clamp, reconnect delay, idle & title toggles)
  - [x] (Linux) Window minimize-to-tray lifecycle with capability-based fallback and restore
  - [x] (Linux) Multi-mode CLI (`main.py` default GUI, `--tray`, `--headless`, `--config`)
  - [x] (Linux) Measured lightweight memory footprint (31.9 MB private anonymous RAM, ~55 MB VmRSS)
  - [ ] (Windows) Windows runtime GUI verification and packaging

#### Assets & Application Recognition
- [x] **#19** — `[Assets & Catalog] Missing application logos in Rich Presence and expanding recognized applications catalog`
  - [x] Document Discord Art Assets requirement (uploading named image assets to Developer Portal)
  - [x] Provide asset naming guide and bundled art asset pack (58 normalized 512x512 PNGs in `assets/art_assets/`)
  - [x] Expand recognized default application catalog (144 process rules across 58 applications including full Linux desktop support in `app/config.py` and `config.example.json`)
  - [x] Automated unit and integrity tests verifying all 144 process mappings and 58 asset files



## 9. Python vs. Rust Decision Gate
- **Decision:** Keep Python. It is simple, easily hackable, and uses negligible resources on a modern desktop.
- **Reconsideration Triggers:** Re-evaluate Rust only if:
  1. Measured memory usage is proven to be a practical problem on the owner's system.
  2. A native Wayland compositor setup requires low-level D-Bus/socket integration that Python cannot handle cleanly.
  3. Multi-machine deployment without Python makes standalone binaries necessary.

## 10. Explicitly Rejected Work
No web/Qt UI, no Electron, no databases, no cloud sync, no accounts, no telemetry, no plugin architecture, no enterprise CI/CD.

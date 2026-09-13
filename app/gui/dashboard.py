import logging
import os
import sys
import time
from typing import Optional

# Ensure Tk library path is found if installed in user local
if "TK_LIBRARY" not in os.environ:
    user_tk = os.path.expanduser("~/.local/lib/tk8.6")
    if os.path.isdir(user_tk):
        os.environ["TK_LIBRARY"] = user_tk

import customtkinter as ctk
from PIL import Image

from app.gui.controller import GUIController, format_elapsed_time
from app.gui.platform import BasePlatformAdapter, get_platform_adapter

logger = logging.getLogger("zenrpc.gui")


class ZenRPCDashboard(ctk.CTk):
    """
    Lightweight desktop GUI dashboard for ZenRPC built with CustomTkinter.
    Provides live Discord Rich Presence preview, quick controls, mapping manager,
    and settings configuration while remaining completely decoupled from PresenceEngine.
    """

    def __init__(
        self,
        controller: Optional[GUIController] = None,
        tray_icon=None,
        assets_dir: Optional[str] = None,
        platform_adapter: Optional[BasePlatformAdapter] = None,
    ):
        super().__init__()

        self.controller = controller or GUIController()
        self.tray_icon = tray_icon
        self.platform_adapter = platform_adapter or get_platform_adapter()
        self.assets_dir = assets_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets",
            "art_assets",
        )

        self.title("ZenRPC Dashboard")
        self.geometry("780x600")
        self.minsize(720, 520)

        # Set Appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # State tracking for UI caching
        self._last_state = {}
        self._cached_icon_key = None
        self._cached_icon_image = None
        self._status_filter_text = ""
        self._mapping_page = 0
        self._mapping_page_size = 25

        # Build UI layout
        self._create_widgets()

        # Subscribe to controller
        self.controller.add_listener(self._on_controller_update)

        # Start periodic tick (every 1 second)
        self._tick_timer = self.after(500, self._periodic_tick)

    def _create_widgets(self):
        # Navigation / Tabview
        self.tabview = ctk.CTkTabview(self, width=740, height=560)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tab_dashboard = self.tabview.add("Activity Dashboard")
        self.tab_mappings = self.tabview.add("Mapping Manager")
        self.tab_settings = self.tabview.add("Settings")

        self._build_dashboard_tab()
        self._build_mappings_tab()
        self._build_settings_tab()

    def _build_dashboard_tab(self):
        # Top Status Bar
        self.status_bar = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        self.status_bar.pack(fill="x", padx=10, pady=(5, 15))

        self.status_badge = ctk.CTkLabel(
            self.status_bar,
            text="● Connecting...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#f1c40f",
        )
        self.status_badge.pack(side="left", padx=5)

        self.lock_badge = ctk.CTkLabel(
            self.status_bar,
            text="[UNLOCKED]",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#95a5a6",
        )
        self.lock_badge.pack(side="left", padx=15)

        # Discord Activity Card (Profile Preview)
        self.card_frame = ctk.CTkFrame(self.tab_dashboard, corner_radius=12, fg_color=("#2b2d31", "#1e1f22"))
        self.card_frame.pack(fill="x", padx=10, pady=10)

        card_title = ctk.CTkLabel(
            self.card_frame,
            text="LIVE DISCORD ACTIVITY PREVIEW",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#b5bac1",
        )
        card_title.pack(anchor="w", padx=18, pady=(14, 6))

        # Inner Content Box
        self.inner_card = ctk.CTkFrame(self.card_frame, fg_color="transparent")
        self.inner_card.pack(fill="x", padx=18, pady=(0, 16))

        # Left: Application Icon
        self.icon_label = ctk.CTkLabel(self.inner_card, text="", width=80, height=80)
        self.icon_label.pack(side="left", padx=(0, 18), pady=5)
        self._set_default_icon()

        # Right: Activity Details
        self.details_frame = ctk.CTkFrame(self.inner_card, fg_color="transparent")
        self.details_frame.pack(side="left", fill="both", expand=True)

        self.app_name_label = ctk.CTkLabel(
            self.details_frame,
            text="ZenRPC",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        self.app_name_label.pack(fill="x", pady=(2, 2))

        self.detail_label = ctk.CTkLabel(
            self.details_frame,
            text="Initializing...",
            font=ctk.CTkFont(size=13),
            text_color="#dbdee1",
            anchor="w",
        )
        self.detail_label.pack(fill="x", pady=(1, 2))

        self.state_label = ctk.CTkLabel(
            self.details_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#949ba4",
            anchor="w",
        )
        self.state_label.pack(fill="x", pady=(1, 2))

        self.timer_label = ctk.CTkLabel(
            self.details_frame,
            text="00:00 elapsed",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#5865F2",
            anchor="w",
        )
        self.timer_label.pack(fill="x", pady=(2, 2))

        # Quick Controls Frame
        controls_label = ctk.CTkLabel(
            self.tab_dashboard,
            text="QUICK CONTROLS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#b5bac1",
        )
        controls_label.pack(anchor="w", padx=15, pady=(20, 6))

        self.controls_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        self.controls_frame.pack(fill="x", padx=10, pady=5)

        self.btn_toggle_rpc = ctk.CTkButton(
            self.controls_frame,
            text="Disable RPC",
            command=self._on_toggle_rpc_click,
            width=150,
            height=36,
            fg_color="#5865f2",
            hover_color="#4752c4",
        )
        self.btn_toggle_rpc.pack(side="left", padx=5)

        self.btn_toggle_lock = ctk.CTkButton(
            self.controls_frame,
            text="Lock Current App",
            command=self._on_toggle_lock_click,
            width=160,
            height=36,
            fg_color="#3ba55d",
            hover_color="#2d7d46",
        )
        self.btn_toggle_lock.pack(side="left", padx=5)

        self.btn_reload = ctk.CTkButton(
            self.controls_frame,
            text="Reload Config",
            command=self._on_reload_config_click,
            width=140,
            height=36,
            fg_color="#4f545c",
            hover_color="#5d6269",
        )
        self.btn_reload.pack(side="left", padx=5)

        if self.tray_icon is not None:
            self.btn_min_tray = ctk.CTkButton(
                self.controls_frame,
                text="Minimize to Tray",
                command=self.minimize_to_tray,
                width=140,
                height=36,
                fg_color="#36393f",
                hover_color="#40444b",
            )
            self.btn_min_tray.pack(side="left", padx=5)

    def _build_mappings_tab(self):
        # Header / Search bar
        top_bar = ctk.CTkFrame(self.tab_mappings, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=5)

        search_lbl = ctk.CTkLabel(top_bar, text="Search:")
        search_lbl.pack(side="left", padx=5)

        self.search_entry = ctk.CTkEntry(top_bar, placeholder_text="Filter process name...", width=220)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_filter_changed)

        btn_refresh = ctk.CTkButton(top_bar, text="Refresh", width=90, command=self._refresh_mappings_list)
        btn_refresh.pack(side="left", padx=10)

        # Mapping Add / Edit Form Frame
        form_frame = ctk.CTkFrame(self.tab_mappings, corner_radius=8)
        form_frame.pack(fill="x", padx=10, pady=8)

        form_title = ctk.CTkLabel(
            form_frame,
            text="Add or Override Application Mapping",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        form_title.pack(anchor="w", padx=12, pady=(8, 4))

        fields_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        fields_row.pack(fill="x", padx=10, pady=5)

        # Process input
        p_col = ctk.CTkFrame(fields_row, fg_color="transparent")
        p_col.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(p_col, text="Process Name (e.g. orca-ide):", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.entry_map_proc = ctk.CTkEntry(p_col, placeholder_text="my_app")
        self.entry_map_proc.pack(fill="x", pady=2)

        # Name input
        n_col = ctk.CTkFrame(fields_row, fg_color="transparent")
        n_col.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(n_col, text="Display Name:", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.entry_map_name = ctk.CTkEntry(n_col, placeholder_text="My Application")
        self.entry_map_name.pack(fill="x", pady=2)

        # Icon input
        i_col = ctk.CTkFrame(fields_row, fg_color="transparent")
        i_col.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(i_col, text="Icon Key:", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.entry_map_icon = ctk.CTkEntry(i_col, placeholder_text="vscode / discord")
        self.entry_map_icon.pack(fill="x", pady=2)

        # Detail input
        d_col = ctk.CTkFrame(fields_row, fg_color="transparent")
        d_col.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(d_col, text="Activity Detail:", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.entry_map_detail = ctk.CTkEntry(d_col, placeholder_text="Working on project")
        self.entry_map_detail.pack(fill="x", pady=2)

        # Bottom action bar of form
        form_bottom = ctk.CTkFrame(form_frame, fg_color="transparent")
        form_bottom.pack(fill="x", padx=14, pady=(2, 10))

        self.lbl_mapping_status = ctk.CTkLabel(form_bottom, text="", font=ctk.CTkFont(size=12))
        self.lbl_mapping_status.pack(side="left")

        # Save Mapping button
        btn_save_map = ctk.CTkButton(
            form_bottom,
            text="Save Custom Mapping",
            command=self._on_save_mapping_click,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            width=160,
        )
        btn_save_map.pack(side="right")

        # Scrollable Mappings List
        self.mappings_scroll = ctk.CTkScrollableFrame(self.tab_mappings, width=720, height=260)
        self.mappings_scroll.pack(fill="both", expand=True, padx=10, pady=(5, 2))

        # Pagination bar
        self.pagination_bar = ctk.CTkFrame(self.tab_mappings, fg_color="transparent")
        self.pagination_bar.pack(fill="x", padx=10, pady=(2, 6))

        self.btn_prev_page = ctk.CTkButton(
            self.pagination_bar,
            text="< Previous",
            width=80,
            command=self._on_prev_page,
            fg_color="#4f545c",
            hover_color="#5d6269",
        )
        self.btn_prev_page.pack(side="left", padx=5)

        self.lbl_page_info = ctk.CTkLabel(
            self.pagination_bar,
            text="Page 1 of 1",
            font=ctk.CTkFont(size=12),
        )
        self.lbl_page_info.pack(side="left", padx=10)

        self.btn_next_page = ctk.CTkButton(
            self.pagination_bar,
            text="Next >",
            width=80,
            command=self._on_next_page,
            fg_color="#4f545c",
            hover_color="#5d6269",
        )
        self.btn_next_page.pack(side="left", padx=5)

        self._refresh_mappings_list()

    def _build_settings_tab(self):
        settings_scroll = ctk.CTkScrollableFrame(self.tab_settings, width=720, height=480)
        settings_scroll.pack(fill="both", expand=True, padx=10, pady=5)

        # Discord Client ID
        lbl_cid = ctk.CTkLabel(settings_scroll, text="Discord Client ID:", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_cid.pack(anchor="w", padx=10, pady=(10, 2))
        self.entry_client_id = ctk.CTkEntry(settings_scroll, placeholder_text="Enter Discord Application ID", width=380)
        self.entry_client_id.pack(anchor="w", padx=10, pady=(0, 15))

        # Update Interval
        lbl_interval = ctk.CTkLabel(
            settings_scroll,
            text="Presence Update Interval (seconds, min 15s):",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_interval.pack(anchor="w", padx=10, pady=(5, 2))

        interval_row = ctk.CTkFrame(settings_scroll, fg_color="transparent")
        interval_row.pack(anchor="w", padx=10, pady=(0, 15))

        self.slider_interval = ctk.CTkSlider(
            interval_row,
            from_=15,
            to=120,
            number_of_steps=105,
            width=260,
            command=self._on_interval_slider_move,
        )
        self.slider_interval.pack(side="left", padx=(0, 15))

        self.lbl_interval_val = ctk.CTkLabel(interval_row, text="15s", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_interval_val.pack(side="left")

        # Reconnect Delay
        lbl_recon = ctk.CTkLabel(
            settings_scroll,
            text="Reconnect Retry Delay (seconds):",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        lbl_recon.pack(anchor="w", padx=10, pady=(5, 2))
        self.entry_recon = ctk.CTkEntry(settings_scroll, placeholder_text="30", width=120)
        self.entry_recon.pack(anchor="w", padx=10, pady=(0, 15))

        # Behavior Toggles
        self.chk_clear_idle = ctk.CTkCheckBox(settings_scroll, text="Clear presence when idle or no active window")
        self.chk_clear_idle.pack(anchor="w", padx=10, pady=8)

        self.chk_show_title = ctk.CTkCheckBox(settings_scroll, text="Show active window title in Discord state")
        self.chk_show_title.pack(anchor="w", padx=10, pady=8)

        self.chk_min_tray = ctk.CTkCheckBox(
            settings_scroll,
            text="Minimize to system tray on window close (X)",
        )
        self.chk_min_tray.pack(anchor="w", padx=10, pady=8)

        # Save Button
        self.btn_save_settings = ctk.CTkButton(
            settings_scroll,
            text="Save Settings",
            command=self._on_save_settings_click,
            width=160,
            height=36,
            fg_color="#5865f2",
            hover_color="#4752c4",
        )
        self.btn_save_settings.pack(anchor="w", padx=10, pady=(20, 10))

        self.lbl_settings_status = ctk.CTkLabel(settings_scroll, text="", text_color="#2ecc71")
        self.lbl_settings_status.pack(anchor="w", padx=10, pady=(0, 10))

        # Load initial values
        self._load_settings_values()

    def _load_settings_values(self):
        cfg = self.controller.get_config()
        self.entry_client_id.delete(0, "end")
        self.entry_client_id.insert(0, str(cfg.get("client_id", "")))

        val = max(15, int(cfg.get("update_interval", 15)))
        self.slider_interval.set(val)
        self.lbl_interval_val.configure(text=f"{val}s")

        self.entry_recon.delete(0, "end")
        self.entry_recon.insert(0, str(cfg.get("reconnect_delay", 30)))

        if cfg.get("clear_on_idle", True):
            self.chk_clear_idle.select()
        else:
            self.chk_clear_idle.deselect()

        if cfg.get("show_window_title", True):
            self.chk_show_title.select()
        else:
            self.chk_show_title.deselect()

        if cfg.get("minimize_to_tray", True):
            self.chk_min_tray.select()
        else:
            self.chk_min_tray.deselect()

    def _on_interval_slider_move(self, val):
        self.lbl_interval_val.configure(text=f"{int(val)}s")

    def _on_save_settings_click(self):
        try:
            cid = self.entry_client_id.get().strip()
            interval = int(self.slider_interval.get())
            recon = int(self.entry_recon.get().strip() or "30")
            clear_idle = bool(self.chk_clear_idle.get())
            show_title = bool(self.chk_show_title.get())
            min_tray = bool(self.chk_min_tray.get())

            self.controller.save_settings(
                client_id=cid,
                update_interval=interval,
                reconnect_delay=recon,
                clear_on_idle=clear_idle,
                show_window_title=show_title,
                minimize_to_tray=min_tray,
            )
            self.lbl_settings_status.configure(text="✓ Settings saved and applied.", text_color="#2ecc71")
            self.after(3000, lambda: self.lbl_settings_status.configure(text=""))
        except Exception as e:
            self.lbl_settings_status.configure(text=f"Error: {e}", text_color="#e74c3c")

    def _on_save_mapping_click(self):
        proc = self.entry_map_proc.get().strip()
        name = self.entry_map_name.get().strip()
        icon = self.entry_map_icon.get().strip()
        detail = self.entry_map_detail.get().strip()

        if not proc:
            self.lbl_mapping_status.configure(
                text="Please enter a process name (e.g. 'orca-ide' or 'code')",
                text_color="#e74c3c",
            )
            return

        try:
            self.controller.save_mapping(proc, name, icon, detail)
            self.entry_map_proc.delete(0, "end")
            self.entry_map_name.delete(0, "end")
            self.entry_map_icon.delete(0, "end")
            self.entry_map_detail.delete(0, "end")
            self._refresh_mappings_list()
            self.lbl_mapping_status.configure(text=f"✓ Mapping '{proc}' saved successfully.", text_color="#2ecc71")
            self.after(3000, lambda: self.lbl_mapping_status.configure(text=""))
        except Exception as e:
            logger.warning("Error saving mapping: %s", e)
            self.lbl_mapping_status.configure(text=f"Error: {e}", text_color="#e74c3c")

    def _on_search_filter_changed(self, event=None):
        self._status_filter_text = self.search_entry.get().strip().lower()
        self._mapping_page = 0
        self._refresh_mappings_list()

    def _on_prev_page(self):
        if self._mapping_page > 0:
            self._mapping_page -= 1
            self._refresh_mappings_list()

    def _on_next_page(self):
        self._mapping_page += 1
        self._refresh_mappings_list()

    def _on_edit_mapping(self, proc: str, info: dict):
        self.entry_map_proc.delete(0, "end")
        self.entry_map_proc.insert(0, proc)
        self.entry_map_name.delete(0, "end")
        self.entry_map_name.insert(0, info.get("name", ""))
        self.entry_map_icon.delete(0, "end")
        self.entry_map_icon.insert(0, info.get("icon", ""))
        self.entry_map_detail.delete(0, "end")
        self.entry_map_detail.insert(0, info.get("detail", ""))

    def _refresh_mappings_list(self):
        # Clear existing items
        for child in self.mappings_scroll.winfo_children():
            child.destroy()

        user_maps = self.controller.get_user_mappings()
        all_maps = self.controller.get_all_mappings()
        filter_text = getattr(self, "_status_filter_text", "").lower()

        # Sort: custom mappings first, then alphabetical by process name
        sorted_items = sorted(all_maps.items(), key=lambda x: (x[0] not in user_maps, x[0].lower()))

        filtered = []
        for proc, info in sorted_items:
            if filter_text and filter_text not in proc.lower() and filter_text not in info.get("name", "").lower():
                continue
            filtered.append((proc, info, proc in user_maps))

        total_items = len(filtered)
        page_size = self._mapping_page_size
        max_pages = max(1, (total_items + page_size - 1) // page_size)

        if self._mapping_page >= max_pages:
            self._mapping_page = max_pages - 1
        if self._mapping_page < 0:
            self._mapping_page = 0

        self.lbl_page_info.configure(
            text=f"Page {self._mapping_page + 1} of {max_pages} ({total_items} mappings)"
        )
        self.btn_prev_page.configure(state="normal" if self._mapping_page > 0 else "disabled")
        self.btn_next_page.configure(state="normal" if self._mapping_page < max_pages - 1 else "disabled")

        start = self._mapping_page * page_size
        end = start + page_size
        page_items = filtered[start:end]

        for proc, info, is_custom in page_items:
            row = ctk.CTkFrame(self.mappings_scroll, fg_color=("#3a3c42" if is_custom else "transparent"))
            row.pack(fill="x", padx=4, pady=2)

            name_text = info.get("name", proc)
            icon_text = info.get("icon", "none")
            detail_text = info.get("detail", "")

            tag = "[Custom] " if is_custom else "[Default] "
            ctk.CTkLabel(
                row,
                text=f"{tag}{proc}",
                font=ctk.CTkFont(size=12, weight="bold" if is_custom else "normal"),
                width=170,
                anchor="w",
            ).pack(side="left", padx=6)

            ctk.CTkLabel(row, text=name_text, width=140, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=f"icon: {icon_text}", width=110, anchor="w", text_color="#95a5a6").pack(
                side="left", padx=4
            )
            ctk.CTkLabel(row, text=detail_text, anchor="w", text_color="#bdc3c7").pack(
                side="left", fill="x", expand=True, padx=4
            )

            actions_f = ctk.CTkFrame(row, fg_color="transparent")
            actions_f.pack(side="right", padx=4)

            btn_edit = ctk.CTkButton(
                actions_f,
                text="Edit",
                width=45,
                height=24,
                fg_color="#3498db",
                hover_color="#2980b9",
                command=lambda p=proc, inf=info: self._on_edit_mapping(p, inf),
            )
            btn_edit.pack(side="left", padx=2)

            if is_custom:
                btn_del = ctk.CTkButton(
                    actions_f,
                    text="Delete",
                    width=50,
                    height=24,
                    fg_color="#e74c3c",
                    hover_color="#c0392b",
                    command=lambda p=proc: self._on_delete_mapping(p),
                )
                btn_del.pack(side="left", padx=2)

        if total_items == 0:
            ctk.CTkLabel(
                self.mappings_scroll,
                text="No mappings matching search query.",
                text_color="#7f8c8d",
            ).pack(pady=20)

    def _on_delete_mapping(self, proc: str):
        try:
            self.controller.delete_mapping(proc)
            self._refresh_mappings_list()
            self.lbl_mapping_status.configure(text=f"✓ Custom mapping '{proc}' removed.", text_color="#e67e22")
            self.after(3000, lambda: self.lbl_mapping_status.configure(text=""))
        except Exception as e:
            logger.warning("Error deleting mapping: %s", e)
            self.lbl_mapping_status.configure(text=f"Error deleting mapping: {e}", text_color="#e74c3c")

    def _set_default_icon(self):
        # Create a blank 80x80 dark placeholder
        img = Image.new("RGBA", (80, 80), (45, 52, 54, 255))
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
        self.icon_label.configure(image=ctk_img)
        self._cached_icon_image = ctk_img

    def _update_icon_image(self, icon_key: Optional[str]):
        if icon_key == self._cached_icon_key:
            return

        self._cached_icon_key = icon_key

        if not icon_key:
            self._set_default_icon()
            return

        png_file = os.path.join(self.assets_dir, f"{icon_key}.png")
        if os.path.isfile(png_file):
            try:
                pil_img = Image.open(png_file).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
                self.icon_label.configure(image=ctk_img)
                self._cached_icon_image = ctk_img
                return
            except Exception as e:
                logger.debug("Failed loading icon asset %s: %s", png_file, e)

        # Fallback icon
        self._set_default_icon()

    def _on_toggle_rpc_click(self):
        self.controller.toggle_rpc()
        self.controller.poll_update()

    def _on_toggle_lock_click(self):
        self.controller.toggle_lock()
        self.controller.poll_update()

    def _on_reload_config_click(self):
        self.controller.reload_config()
        self._load_settings_values()
        self._refresh_mappings_list()
        self.controller.poll_update()

    def _on_controller_update(self, state: dict):
        """Observer callback receiving state updates."""
        # Update connection badge
        running = state.get("running", False)
        connected = state.get("connected", False)
        locked = state.get("locked", False)
        locked_proc = state.get("locked_proc")

        if not running:
            self.status_badge.configure(text="● RPC Disabled", text_color="#7f8c8d")
            self.btn_toggle_rpc.configure(text="Enable RPC", fg_color="#2ecc71", hover_color="#27ae60")
        elif connected:
            self.status_badge.configure(text="● Connected to Discord", text_color="#2ecc71")
            self.btn_toggle_rpc.configure(text="Disable RPC", fg_color="#e74c3c", hover_color="#c0392b")
        else:
            self.status_badge.configure(text="● Reconnecting to Discord...", text_color="#f39c12")
            self.btn_toggle_rpc.configure(text="Disable RPC", fg_color="#e74c3c", hover_color="#c0392b")

        # Update lock badge & button
        if locked:
            proc_disp = (locked_proc or "?").replace(".exe", "")
            self.lock_badge.configure(text=f"[LOCKED: {proc_disp}]", text_color="#e74c3c")
            self.btn_toggle_lock.configure(text="Unlock Presence", fg_color="#e67e22", hover_color="#d35400")
        else:
            self.lock_badge.configure(text="[UNLOCKED]", text_color="#95a5a6")
            self.btn_toggle_lock.configure(text="Lock Current App", fg_color="#3ba55d", hover_color="#2d7d46")

        # Update Live Card Details
        app_name = state.get("app_name") or "Idle"
        detail = state.get("detail") or "No active application"
        state_text = state.get("state_text") or ""
        icon_key = state.get("icon_key")
        elapsed = state.get("elapsed_seconds", 0)

        self.app_name_label.configure(text=app_name)
        self.detail_label.configure(text=detail)
        self.state_label.configure(text=state_text)

        if running and state.get("proc_name"):
            self.timer_label.configure(text=f"{format_elapsed_time(elapsed)} elapsed")
        else:
            self.timer_label.configure(text="")

        self._update_icon_image(icon_key)

        if self.tray_icon:
            self.platform_adapter.update_tray_state(
                self.tray_icon,
                locked=locked,
                running=running,
            )

    def _periodic_tick(self):
        """Called every second by Tkinter event loop."""
        try:
            self.controller.poll_update()
        except Exception as e:
            logger.debug("Error in periodic tick: %s", e)
        finally:
            self._tick_timer = self.after(1000, self._periodic_tick)

    def minimize_to_tray(self):
        """Minimizes dashboard window to system tray using platform adapter."""
        logger.info("Minimizing ZenRPC Dashboard to system tray.")
        self.platform_adapter.minimize_to_tray(self)

    def on_closing(self):
        """Handles window [X] close button click."""
        cfg = self.controller.get_config()
        min_to_tray = cfg.get("minimize_to_tray", True)

        # If minimize_to_tray enabled AND tray is available, withdraw window to tray
        if min_to_tray and self.tray_icon is not None:
            self.minimize_to_tray()
        else:
            self.quit_app()

    def restore_window(self):
        """Restores dashboard window from tray minimization using platform adapter."""
        self.platform_adapter.restore_and_focus(self)

    def quit_app(self):
        """Gracefully shuts down engine and closes dashboard."""
        logger.info("Shutting down ZenRPC Dashboard...")
        if self._tick_timer:
            self.after_cancel(self._tick_timer)
            self._tick_timer = None

        self.controller.engine.stop()

        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass

        self.destroy()

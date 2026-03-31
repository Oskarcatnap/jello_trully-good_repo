import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from core import system_ops


class BaseTab(ctk.CTkFrame):
    def __init__(self, master, font_family: str):
        super().__init__(master, fg_color="transparent")
        self.font_family = font_family

        self.main = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=12)
        self.main.pack(fill="both", expand=True, padx=10, pady=10)

        self.content = ctk.CTkFrame(self.main, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=14, pady=(14, 8))

        self.log_box = ctk.CTkTextbox(self.main, height=140, fg_color="#111111")
        self.log_box.pack(fill="x", padx=14, pady=(0, 14))
        self.log_box.configure(font=(self.font_family, 12))
        self.log("[INFO] Ready")

    def log(self, message: str) -> None:
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")


class DashboardTab(BaseTab):
    def __init__(self, master, font_family: str):
        super().__init__(master, font_family)
        self.sys_info = system_ops.get_system_info()

        title = ctk.CTkLabel(
            self.content,
            text="Dashboard",
            font=(self.font_family, 26, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        self.windows_label = ctk.CTkLabel(
            self.content,
            text=f"Windows: {self.sys_info['windows_version']}",
            font=(self.font_family, 14),
        )
        self.windows_label.pack(anchor="w", pady=4)

        self.pc_label = ctk.CTkLabel(
            self.content,
            text=f"PC Name: {self.sys_info['pc_name']}",
            font=(self.font_family, 14),
        )
        self.pc_label.pack(anchor="w", pady=4)

        self.cpu_label = ctk.CTkLabel(self.content, text="CPU: ...", font=(self.font_family, 14))
        self.cpu_label.pack(anchor="w", pady=4)

        self.ram_label = ctk.CTkLabel(self.content, text="RAM: ...", font=(self.font_family, 14))
        self.ram_label.pack(anchor="w", pady=4)

        btn = ctk.CTkButton(
            self.content,
            text="Quick Restart Explorer",
            command=lambda: system_ops.restart_explorer(self.log),
            font=(self.font_family, 13, "bold"),
        )
        btn.pack(anchor="w", pady=(12, 0))

        self._update_stats()

    def _update_stats(self):
        usage = system_ops.get_realtime_usage()
        self.cpu_label.configure(text=f"CPU: {usage['cpu']}")
        self.ram_label.configure(text=f"RAM: {usage['ram']}")
        self.after(1000, self._update_stats)


class PrivacyTab(BaseTab):
    def __init__(self, master, font_family: str):
        super().__init__(master, font_family)
        title = ctk.CTkLabel(
            self.content,
            text="Privacy & Security",
            font=(self.font_family, 26, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        ctk.CTkButton(
            self.content,
            text="Disable Microsoft Telemetry",
            command=lambda: system_ops.disable_telemetry(self.log),
            font=(self.font_family, 13, "bold"),
        ).pack(anchor="w", pady=6)

        ctk.CTkButton(
            self.content,
            text="Disable Start Ads + Promo Notifications",
            command=lambda: system_ops.disable_ads_and_suggestions(self.log),
            font=(self.font_family, 13, "bold"),
        ).pack(anchor="w", pady=6)

        defender_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        defender_frame.pack(anchor="w", pady=6)
        ctk.CTkButton(
            defender_frame,
            text="Enable Defender",
            command=lambda: system_ops.set_defender_enabled(True, self.log),
            font=(self.font_family, 13, "bold"),
            width=150,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            defender_frame,
            text="Disable Defender",
            command=lambda: system_ops.set_defender_enabled(False, self.log),
            font=(self.font_family, 13, "bold"),
            width=150,
        ).pack(side="left")


class PerformanceTab(BaseTab):
    def __init__(self, master, font_family: str):
        super().__init__(master, font_family)
        title = ctk.CTkLabel(
            self.content,
            text="Performance",
            font=(self.font_family, 26, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        ctk.CTkButton(
            self.content,
            text="Enable Ultimate Performance",
            command=lambda: system_ops.enable_ultimate_performance(self.log),
            font=(self.font_family, 13, "bold"),
        ).pack(anchor="w", pady=6)

        ctk.CTkButton(
            self.content,
            text="Quick System Cache Cleanup",
            command=lambda: system_ops.clean_system_cache_and_temp(self.log),
            font=(self.font_family, 13, "bold"),
        ).pack(anchor="w", pady=6)

        ctk.CTkButton(
            self.content,
            text="Optimize Visual Effects",
            command=lambda: system_ops.optimize_visual_effects(self.log),
            font=(self.font_family, 13, "bold"),
        ).pack(anchor="w", pady=6)


class AdvancedTab(BaseTab):
    def __init__(self, master, font_family: str):
        super().__init__(master, font_family)
        title = ctk.CTkLabel(
            self.content,
            text="Advanced Settings",
            font=(self.font_family, 26, "bold"),
        )
        title.pack(anchor="w", pady=(0, 10))

        rename_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        rename_frame.pack(fill="x", pady=(0, 8))
        self.new_name_entry = ctk.CTkEntry(rename_frame, placeholder_text="New Computer Name")
        self.new_name_entry.pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            rename_frame,
            text="Rename",
            command=self._rename_pc,
            font=(self.font_family, 12, "bold"),
            width=110,
        ).pack(side="left")

        env_title = ctk.CTkLabel(self.content, text="Environment Variables (User)", font=(self.font_family, 14, "bold"))
        env_title.pack(anchor="w", pady=(8, 4))

        self.env_table = ttk.Treeview(self.content, columns=("name", "value"), show="headings", height=8)
        self.env_table.heading("name", text="Name")
        self.env_table.heading("value", text="Value")
        self.env_table.column("name", width=220, anchor="w")
        self.env_table.column("value", width=400, anchor="w")
        self.env_table.pack(fill="x", pady=(0, 8))
        self.env_table.bind("<<TreeviewSelect>>", self._on_env_select)

        env_edit = ctk.CTkFrame(self.content, fg_color="transparent")
        env_edit.pack(fill="x")
        self.env_name = ctk.CTkEntry(env_edit, placeholder_text="Variable Name", width=220)
        self.env_name.pack(side="left", padx=(0, 6))
        self.env_value = ctk.CTkEntry(env_edit, placeholder_text="Variable Value")
        self.env_value.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(env_edit, text="Save", width=90, command=self._save_env).pack(side="left", padx=(0, 6))
        ctk.CTkButton(env_edit, text="Delete", width=90, command=self._delete_env).pack(side="left")

        tools = ctk.CTkFrame(self.content, fg_color="transparent")
        tools.pack(anchor="w", pady=(12, 0))
        ctk.CTkButton(
            tools,
            text="Regedit",
            width=120,
            command=lambda: system_ops.open_system_tool("regedit", self.log),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            tools,
            text="GPEdit",
            width=120,
            command=lambda: system_ops.open_system_tool("gpedit", self.log),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            tools,
            text="Services",
            width=120,
            command=lambda: system_ops.open_system_tool("services", self.log),
        ).pack(side="left")

        self._refresh_env_table()

    def _rename_pc(self):
        system_ops.rename_computer(self.new_name_entry.get(), self.log)

    def _refresh_env_table(self):
        for row in self.env_table.get_children():
            self.env_table.delete(row)
        vars_map = system_ops.get_user_env_vars()
        for name, value in vars_map.items():
            self.env_table.insert("", "end", values=(name, value))
        self.log("[OK] Environment variables list refreshed")

    def _on_env_select(self, _event):
        selected = self.env_table.selection()
        if not selected:
            return
        name, value = self.env_table.item(selected[0], "values")
        self.env_name.delete(0, "end")
        self.env_name.insert(0, name)
        self.env_value.delete(0, "end")
        self.env_value.insert(0, value)

    def _save_env(self):
        system_ops.set_user_env_var(self.env_name.get(), self.env_value.get(), self.log)
        self._refresh_env_table()

    def _delete_env(self):
        system_ops.delete_user_env_var(self.env_name.get(), self.log)
        self._refresh_env_table()

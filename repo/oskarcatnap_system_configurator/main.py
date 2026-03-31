import ctypes
import tkinter as tk
from tkinter import font as tkfont

import customtkinter as ctk

from core.admin import is_admin, relaunch_as_admin
from ui.tabs import AdvancedTab, DashboardTab, PerformanceTab, PrivacyTab


def choose_font_family() -> str:
    root = tk.Tk()
    root.withdraw()
    available = set(tkfont.families(root))
    root.destroy()
    if "Minecraft" in available:
        return "Minecraft"
    if "Consolas" in available:
        return "Consolas"
    return "Segoe UI"


class SystemConfiguratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("oskarcatnap's System Configurator")
        self.geometry("1220x760")
        self.minsize(980, 620)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.font_family = choose_font_family()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#101010")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        logo = ctk.CTkLabel(
            self.sidebar,
            text="oskarcatnap's\nSystem Configurator",
            font=(self.font_family, 20, "bold"),
            justify="left",
        )
        logo.pack(anchor="w", padx=18, pady=(20, 25))

        self.content = ctk.CTkFrame(self, fg_color="#0d0d0d", corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.frames = {
            "dashboard": DashboardTab(self.content, self.font_family),
            "privacy": PrivacyTab(self.content, self.font_family),
            "performance": PerformanceTab(self.content, self.font_family),
            "advanced": AdvancedTab(self.content, self.font_family),
        }
        for frame in self.frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "🖥 Dashboard"),
            ("privacy", "🛡 Privacy & Security"),
            ("performance", "🚀 Performance"),
            ("advanced", "⚙ Advanced Settings"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=42,
                corner_radius=10,
                font=(self.font_family, 13, "bold"),
                command=lambda tab=key: self.show_tab(tab),
            )
            btn.pack(fill="x", padx=14, pady=5)
            self.nav_buttons[key] = btn

        footer = ctk.CTkLabel(
            self.sidebar,
            text="Administrator mode required",
            font=(self.font_family, 11),
            text_color="#999999",
        )
        footer.pack(side="bottom", anchor="w", padx=16, pady=14)

        self.show_tab("dashboard")

    def show_tab(self, key: str):
        self.frames[key].tkraise()
        for k, button in self.nav_buttons.items():
            button.configure(fg_color="#1f538d" if k == key else "#2b2b2b")


def ensure_admin_or_exit() -> None:
    if is_admin():
        return

    relaunch_ok = relaunch_as_admin()
    if not relaunch_ok:
        ctypes.windll.user32.MessageBoxW(
            0,
            "This application requires administrator privileges.",
            "Permission Required",
            0x10,
        )
    raise SystemExit


if __name__ == "__main__":
    ensure_admin_or_exit()
    app = SystemConfiguratorApp()
    app.mainloop()

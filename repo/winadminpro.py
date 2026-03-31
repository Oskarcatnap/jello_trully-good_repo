"""
WinAdmin Pro — Professional Windows Administration Tool
Requires: customtkinter, psutil, pillow
Install: pip install customtkinter psutil pillow
"""

import sys
import os
import ctypes
import subprocess
import threading
import winreg
import json
import re
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "customtkinter", "psutil", "pillow"], check=True)
    import customtkinter as ctk
    from PIL import Image, ImageTk

try:
    import psutil
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil"], check=True)
    import psutil

# ─── Admin Check ──────────────────────────────────────────────────────────────
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join([f'"{a}"' for a in sys.argv]), None, 1
        )
        sys.exit()

# ─── Registry Helper ──────────────────────────────────────────────────────────
def reg_set(hive, path, name, value, reg_type=winreg.REG_DWORD):
    try:
        key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, reg_type, value)
        winreg.CloseKey(key)
        return True
    except PermissionError:
        return False, "Access Denied — требуются права администратора"
    except Exception as e:
        return False, str(e)

def reg_get(hive, path, name, default=None):
    try:
        key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return val
    except:
        return default

def run_cmd(cmd, capture=False):
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout.strip(), result.returncode
        else:
            subprocess.Popen(cmd, shell=True)
            return True
    except Exception as e:
        return str(e), -1

# ─── Color Theme ──────────────────────────────────────────────────────────────
COLORS = {
    "bg_deep":      "#090c12",
    "bg_dark":      "#0d1117",
    "bg_card":      "#111827",
    "bg_elevated":  "#161e2e",
    "sidebar_bg":   "#0a0f18",
    "border":       "#1e2d40",
    "border_bright":"#2a3f5a",
    "accent":       "#00d4ff",
    "accent2":      "#0ea5e9",
    "accent_dim":   "#0c4a6e",
    "accent_glow":  "#38bdf8",
    "green":        "#22d3a5",
    "green_dim":    "#065f46",
    "red":          "#f43f5e",
    "red_dim":      "#4c0519",
    "yellow":       "#fbbf24",
    "purple":       "#a78bfa",
    "text":         "#e2e8f0",
    "text_muted":   "#64748b",
    "text_dim":     "#94a3b8",
    "white":        "#f8fafc",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Custom Widgets ───────────────────────────────────────────────────────────
class NeonButton(ctk.CTkButton):
    def __init__(self, parent, text, command=None, variant="primary", **kwargs):
        colors = {
            "primary":  (COLORS["accent"],     COLORS["accent2"],   COLORS["bg_deep"]),
            "success":  (COLORS["green"],      "#16a085",           COLORS["bg_deep"]),
            "danger":   (COLORS["red"],        "#be123c",           COLORS["white"]),
            "ghost":    (COLORS["border"],     COLORS["border_bright"], COLORS["text"]),
            "warning":  (COLORS["yellow"],     "#d97706",           COLORS["bg_deep"]),
        }
        fg, hover, txt = colors.get(variant, colors["primary"])
        super().__init__(parent, text=text, command=command,
                         fg_color=fg, hover_color=hover, text_color=txt,
                         corner_radius=6, font=ctk.CTkFont("Consolas", 12, "bold"),
                         height=34, **kwargs)

class StatusBadge(ctk.CTkLabel):
    def __init__(self, parent, text, status="info", **kwargs):
        colors = {"ok": COLORS["green"], "warn": COLORS["yellow"],
                  "error": COLORS["red"], "info": COLORS["accent"]}
        c = colors.get(status, COLORS["accent"])
        super().__init__(parent, text=f"  {text}  ",
                         fg_color=c, text_color=COLORS["bg_deep"],
                         corner_radius=4, font=ctk.CTkFont("Consolas", 10, "bold"),
                         **kwargs)

class SectionCard(ctk.CTkFrame):
    def __init__(self, parent, title="", **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_card"],
                         corner_radius=10, border_width=1,
                         border_color=COLORS["border"], **kwargs)
        if title:
            ctk.CTkLabel(self, text=title,
                         font=ctk.CTkFont("Consolas", 13, "bold"),
                         text_color=COLORS["accent"]).pack(anchor="w", padx=16, pady=(12, 4))
            ctk.CTkFrame(self, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=12, pady=(0, 8))

class LogConsole(ctk.CTkTextbox):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=COLORS["bg_deep"],
                         text_color=COLORS["green"],
                         font=ctk.CTkFont("Consolas", 11),
                         **kwargs)
        self.configure(state="disabled")

    def log(self, msg, level="info"):
        colors_map = {"info": COLORS["accent"], "ok": COLORS["green"],
                      "error": COLORS["red"], "warn": COLORS["yellow"]}
        prefix = {"info": "[INFO]", "ok": "[OK]  ", "error": "[ERR] ", "warn": "[WARN]"}
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts} {prefix.get(level,'[LOG]')} {msg}\n"
        self.configure(state="normal")
        self.insert("end", line)
        # color tagging via tag_config would need tk.Text; use plain insert
        self.see("end")
        self.configure(state="disabled")

# ─── Panels ───────────────────────────────────────────────────────────────────
class BaseSettingsPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, log, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.log = log
        self._build()

    def _build(self):
        # PC Name
        card = SectionCard(self, "🖥  Имя компьютера и рабочая группа")
        card.pack(fill="x", padx=4, pady=(0, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row, text="Имя ПК:", text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Consolas", 12), width=100).pack(side="left")
        self.pc_name = ctk.CTkEntry(row, fg_color=COLORS["bg_elevated"],
                                    border_color=COLORS["border_bright"],
                                    text_color=COLORS["text"],
                                    font=ctk.CTkFont("Consolas", 12), width=220)
        current = reg_get(winreg.HKEY_LOCAL_MACHINE,
                          r"SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName",
                          "ComputerName", "UNKNOWN")
        self.pc_name.insert(0, current)
        self.pc_name.pack(side="left", padx=(0, 8))
        NeonButton(row, "Применить", self._set_pc_name, "primary", width=100).pack(side="left")

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(row2, text="Рабочая группа:", text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Consolas", 12), width=100).pack(side="left")
        self.workgroup = ctk.CTkEntry(row2, fg_color=COLORS["bg_elevated"],
                                      border_color=COLORS["border_bright"],
                                      text_color=COLORS["text"],
                                      font=ctk.CTkFont("Consolas", 12), width=220)
        wg = reg_get(winreg.HKEY_LOCAL_MACHINE,
                     r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
                     "Domain", "WORKGROUP")
        self.workgroup.insert(0, wg or "WORKGROUP")
        self.workgroup.pack(side="left", padx=(0, 8))
        NeonButton(row2, "Применить", self._set_workgroup, "primary", width=100).pack(side="left")

        # Time
        card2 = SectionCard(self, "🕐  Управление временем")
        card2.pack(fill="x", padx=4, pady=(0, 10))

        row3 = ctk.CTkFrame(card2, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=4)
        NeonButton(row3, "⟳ Синхронизировать время", self._sync_time, "primary").pack(side="left", padx=(0, 8))
        NeonButton(row3, "📅 Открыть дату/время", lambda: run_cmd("timedate.cpl"), "ghost").pack(side="left")

        row4 = ctk.CTkFrame(card2, fg_color="transparent")
        row4.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(row4, text="Часовой пояс:", text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Consolas", 12)).pack(side="left", padx=(0, 8))
        timezones = ["UTC", "Russian Standard Time", "W. Europe Standard Time",
                     "Eastern Standard Time", "Pacific Standard Time", "China Standard Time"]
        self.tz_var = ctk.StringVar(value="Russian Standard Time")
        ctk.CTkOptionMenu(card2, values=timezones, variable=self.tz_var,
                          fg_color=COLORS["bg_elevated"],
                          button_color=COLORS["accent_dim"],
                          button_hover_color=COLORS["accent2"],
                          text_color=COLORS["text"],
                          font=ctk.CTkFont("Consolas", 11)).pack(anchor="w", padx=16, pady=(0,4))
        NeonButton(card2, "Применить часовой пояс", self._set_timezone, "primary", width=180).pack(anchor="w", padx=16, pady=(0, 12))

        # Power
        card3 = SectionCard(self, "⚡  Настройки питания")
        card3.pack(fill="x", padx=4, pady=(0, 10))

        schemes = [
            ("🚀 Максимальная производительность", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"),
            ("⚖️  Сбалансированный",                "381b4222-f694-41f0-9685-ff5bb260df2e"),
            ("🔋 Экономия энергии",                  "a1841308-3541-4fab-bc81-f71556f20b4a"),
        ]
        for label, guid in schemes:
            btn = NeonButton(card3, label, lambda g=guid: self._set_power(g), "ghost")
            btn.pack(anchor="w", padx=16, pady=3)

        NeonButton(card3, "🔧 Открыть электропитание", lambda: run_cmd("powercfg.cpl"), "ghost").pack(anchor="w", padx=16, pady=(3, 12))

    def _set_pc_name(self):
        name = self.pc_name.get().strip()
        if not name:
            return
        try:
            reg_set(winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName",
                    "ComputerName", name, winreg.REG_SZ)
            reg_set(winreg.HKEY_LOCAL_MACHINE,
                    r"SYSTEM\CurrentControlSet\Control\ComputerName\ActiveComputerName",
                    "ComputerName", name, winreg.REG_SZ)
            self.log(f"Имя ПК изменено на: {name} (требуется перезагрузка)", "ok")
        except Exception as e:
            self.log(f"Ошибка изменения имени ПК: {e}", "error")

    def _set_workgroup(self):
        wg = self.workgroup.get().strip().upper()
        if not wg:
            return
        out, code = run_cmd(f'wmic computersystem where name="%computername%" call joindomainorworkgroup FJoinOptions=0 Name="{wg}"', capture=True)
        self.log(f"Рабочая группа: {wg} — {'OK' if code == 0 else 'Ошибка'}", "ok" if code == 0 else "error")

    def _sync_time(self):
        out, code = run_cmd("w32tm /resync /force", capture=True)
        self.log("Время синхронизировано" if code == 0 else f"Ошибка синхронизации: {out}",
                 "ok" if code == 0 else "error")

    def _set_timezone(self):
        tz = self.tz_var.get()
        out, code = run_cmd(f'tzutil /s "{tz}"', capture=True)
        self.log(f"Часовой пояс: {tz}", "ok" if code == 0 else "error")

    def _set_power(self, guid):
        out, code = run_cmd(f"powercfg /setactive {guid}", capture=True)
        self.log(f"Схема питания применена: {guid}", "ok" if code == 0 else "error")


class SecurityPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, log, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.log = log
        self._build()

    def _build(self):
        # Telemetry
        card = SectionCard(self, "📡  Телеметрия и сбор данных Microsoft")
        card.pack(fill="x", padx=4, pady=(0, 10))

        ctk.CTkLabel(card, text="⚠  Отключение телеметрии влияет на обновления Windows",
                     text_color=COLORS["yellow"],
                     font=ctk.CTkFont("Consolas", 11)).pack(anchor="w", padx=16, pady=(0, 6))

        actions = [
            ("🚫 Отключить телеметрию (уровень 0)", self._disable_telemetry),
            ("🚫 Отключить DiagTrack службу",       self._disable_diagtrack),
            ("🚫 Отключить CEIP",                   self._disable_ceip),
            ("🚫 Отключить рекламный ID",            self._disable_adid),
            ("✅ Восстановить настройки телеметрии", self._restore_telemetry),
        ]
        for label, cmd in actions:
            variant = "danger" if "Отключить" in label else "success"
            NeonButton(card, label, cmd, variant).pack(anchor="w", padx=16, pady=3)
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

        # Defender
        card2 = SectionCard(self, "🛡  Windows Defender")
        card2.pack(fill="x", padx=4, pady=(0, 10))

        ctk.CTkLabel(card2,
                     text="⚠  ВНИМАНИЕ: Отключение Defender снижает защиту системы!",
                     text_color=COLORS["red"], font=ctk.CTkFont("Consolas", 11, "bold")).pack(anchor="w", padx=16, pady=(0, 6))

        row = ctk.CTkFrame(card2, fg_color="transparent")
        row.pack(anchor="w", padx=16, pady=(0, 8))
        NeonButton(row, "✅ Включить Defender",  self._enable_defender,  "success").pack(side="left", padx=(0, 8))
        NeonButton(row, "❌ Отключить Defender", self._disable_defender, "danger").pack(side="left")

        row2 = ctk.CTkFrame(card2, fg_color="transparent")
        row2.pack(anchor="w", padx=16, pady=(0, 12))
        NeonButton(row2, "🔄 Обновить базы Defender", self._update_defender, "primary").pack(side="left", padx=(0,8))
        NeonButton(row2, "🔍 Быстрое сканирование", lambda: run_cmd("start ms-settings:windowsdefender"), "ghost").pack(side="left")

        # Activity
        card3 = SectionCard(self, "🗑  Очистка истории и диагностики")
        card3.pack(fill="x", padx=4, pady=(0, 10))

        cleans = [
            ("🧹 Очистить историю активности", self._clear_activity),
            ("🧹 Очистить диагностические данные", self._clear_diag),
            ("🧹 Очистить историю поиска", self._clear_search_history),
        ]
        for label, cmd in cleans:
            NeonButton(card3, label, cmd, "warning").pack(anchor="w", padx=16, pady=3)
        ctk.CTkFrame(card3, height=8, fg_color="transparent").pack()

    def _disable_telemetry(self):
        ops = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", 0),
        ]
        for hive, path, name, val in ops:
            try:
                key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, val)
                winreg.CloseKey(key)
            except Exception as e:
                self.log(f"Ошибка: {e}", "error")
                return
        self.log("Телеметрия отключена (уровень 0)", "ok")

    def _disable_diagtrack(self):
        run_cmd("sc stop DiagTrack && sc config DiagTrack start= disabled")
        self.log("Служба DiagTrack остановлена и отключена", "ok")

    def _disable_ceip(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\SQMClient\Windows", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "CEIPEnable", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self.log("CEIP отключён", "ok")
        except Exception as e:
            self.log(f"Ошибка CEIP: {e}", "error")

    def _disable_adid(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\AdvertisingInfo", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "Enabled", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self.log("Рекламный ID отключён", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _restore_telemetry(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AllowTelemetry", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log("Телеметрия восстановлена", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _enable_defender(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows Defender", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DisableAntiSpyware", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            run_cmd('powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $false"')
            self.log("Windows Defender включён", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _disable_defender(self):
        if not messagebox.askyesno("⚠ Предупреждение",
                "Отключение Windows Defender снижает защиту системы!\n\nВы уверены?"):
            return
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Policies\Microsoft\Windows Defender", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "DisableAntiSpyware", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            run_cmd('powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true"')
            self.log("Windows Defender отключён", "warn")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _update_defender(self):
        run_cmd('powershell -Command "Update-MpSignature"')
        self.log("Обновление баз Defender запущено...", "info")

    def _clear_activity(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RunMRU", 0, winreg.KEY_SET_VALUE)
            winreg.CloseKey(key)
            run_cmd('powershell -Command "Clear-EventLog -LogName Application,System,Security -ErrorAction SilentlyContinue"')
            self.log("История активности очищена", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _clear_diag(self):
        run_cmd("del /f /q /s %LOCALAPPDATA%\\DiagnosticsHub\\*.* 2>nul")
        self.log("Диагностические данные очищены", "ok")

    def _clear_search_history(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\WordWheelQuery", 0, winreg.KEY_SET_VALUE)
            winreg.CloseKey(key)
            self.log("История поиска очищена", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")


class CustomizationPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, log, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.log = log
        self._build()

    def _build(self):
        # Theme
        card = SectionCard(self, "🎨  Тема и прозрачность")
        card.pack(fill="x", padx=4, pady=(0, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        self.dark_var = ctk.IntVar(value=reg_get(winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            "AppsUseLightTheme", 1))

        ctk.CTkLabel(row, text="Тема приложений:", text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Consolas", 12), width=160).pack(side="left")
        NeonButton(row, "🌑 Тёмная",  lambda: self._set_theme(0), "primary").pack(side="left", padx=(0, 6))
        NeonButton(row, "☀️ Светлая", lambda: self._set_theme(1), "ghost").pack(side="left")

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row2, text="Системная тема:", text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Consolas", 12), width=160).pack(side="left")
        NeonButton(row2, "🌑 Тёмная",  lambda: self._set_sys_theme(0), "primary").pack(side="left", padx=(0, 6))
        NeonButton(row2, "☀️ Светлая", lambda: self._set_sys_theme(1), "ghost").pack(side="left")

        # Blur/Transparency
        card2 = SectionCard(self, "💎  Эффекты прозрачности (Acrylic/Mica)")
        card2.pack(fill="x", padx=4, pady=(0, 10))

        effects = [
            ("✅ Включить прозрачность",  self._enable_transparency),
            ("❌ Отключить прозрачность", self._disable_transparency),
            ("✅ Включить Mica эффект",   self._enable_mica),
            ("✅ Включить Acrylic панель задач", self._enable_acrylic),
        ]
        for label, cmd in effects:
            v = "success" if "Включить" in label else "danger"
            NeonButton(card2, label, cmd, v).pack(anchor="w", padx=16, pady=3)
        ctk.CTkFrame(card2, height=8, fg_color="transparent").pack()

        # Desktop Icons
        card3 = SectionCard(self, "🖥  Системные значки рабочего стола")
        card3.pack(fill="x", padx=4, pady=(0, 10))

        icons = [
            ("Этот компьютер",    "{20D04FE0-3AEA-1069-A2D8-08002B30309D}", 0),
            ("Корзина",           "{645FF040-5081-101B-9F08-00AA002F954E}", 0),
            ("Сеть",              "{F02C1A0D-BE21-4350-88B0-7367FC96EF3C}", 0),
            ("Панель управления", "{5399E694-6CE5-4D6C-8FCE-1D8870FDCBA0}", 0),
        ]
        for label, guid, val in icons:
            row = ctk.CTkFrame(card3, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=label, text_color=COLORS["text"],
                         font=ctk.CTkFont("Consolas", 12), width=180).pack(side="left")
            NeonButton(row, "Показать", lambda g=guid: self._show_icon(g), "success", width=90).pack(side="left", padx=(0,6))
            NeonButton(row, "Скрыть",   lambda g=guid: self._hide_icon(g), "ghost", width=90).pack(side="left")
        ctk.CTkFrame(card3, height=8, fg_color="transparent").pack()

        # Cursors / Sounds
        card4 = SectionCard(self, "🖱  Курсоры и системные звуки")
        card4.pack(fill="x", padx=4, pady=(0, 10))

        row = ctk.CTkFrame(card4, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        NeonButton(row, "🖱 Настройки курсора", lambda: run_cmd("main.cpl"), "ghost").pack(side="left", padx=(0, 8))
        NeonButton(row, "🔊 Системные звуки",   lambda: run_cmd("mmsys.cpl"), "ghost").pack(side="left")
        ctk.CTkFrame(card4, height=8, fg_color="transparent").pack()

    def _set_theme(self, val):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
            self.log(f"Тема приложений: {'Светлая' if val else 'Тёмная'}", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _set_sys_theme(self, val):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)
            winreg.CloseKey(key)
            self.log(f"Системная тема: {'Светлая' if val else 'Тёмная'}", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _enable_transparency(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log("Прозрачность включена", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _disable_transparency(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "EnableTransparency", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self.log("Прозрачность отключена", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _enable_mica(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\DWM", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "MicaEffect", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log("Mica эффект включён (требуется перезапуск)", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _enable_acrylic(self):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "UseOLEDTaskbar", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log("Acrylic панель задач включена", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _show_icon(self, guid):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, f"{{{guid}}}" if not guid.startswith("{") else guid, 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self.log(f"Значок показан: {guid[:20]}...", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _hide_icon(self, guid):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\HideDesktopIcons\NewStartPanel",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, f"{{{guid}}}" if not guid.startswith("{") else guid, 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log(f"Значок скрыт: {guid[:20]}...", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")


class PerformancePanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, log, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.log = log
        self._build()

    def _build(self):
        # Cleanup
        card = SectionCard(self, "🧹  Очистка временных файлов")
        card.pack(fill="x", padx=4, pady=(0, 10))

        self.progress = ctk.CTkProgressBar(card, fg_color=COLORS["bg_elevated"],
                                           progress_color=COLORS["accent"])
        self.progress.set(0)
        self.progress.pack(fill="x", padx=16, pady=(4, 8))

        targets = [
            ("📁 %TEMP%",         "%TEMP%"),
            ("📁 Windows Temp",    "%WINDIR%\\Temp"),
            ("📁 Prefetch",        "%WINDIR%\\Prefetch"),
            ("📁 Thumbnails cache",""),
        ]
        for label, path in targets:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=label, text_color=COLORS["text_dim"],
                         font=ctk.CTkFont("Consolas", 12), width=200).pack(side="left")
            NeonButton(row, "Очистить", lambda p=path: self._clean(p), "warning", width=90).pack(side="left")

        NeonButton(card, "🗑 Очистить всё одним кликом", self._clean_all, "danger").pack(
            anchor="w", padx=16, pady=(8, 12))

        # Visual Effects
        card2 = SectionCard(self, "🎭  Визуальные эффекты")
        card2.pack(fill="x", padx=4, pady=(0, 10))

        perf_opts = [
            ("🚀 Максимальная производительность (отключить все эффекты)", self._max_performance),
            ("✨ Максимальная красота (включить все эффекты)",              self._max_visual),
            ("⚖️  Выбор Windows (оптимально)",                             self._windows_choice),
        ]
        for label, cmd in perf_opts:
            NeonButton(card2, label, cmd, "ghost").pack(anchor="w", padx=16, pady=3)
        ctk.CTkFrame(card2, height=8, fg_color="transparent").pack()

        # Services
        card3 = SectionCard(self, "⚙️  Управление службами Windows")
        card3.pack(fill="x", padx=4, pady=(0, 10))

        search_row = ctk.CTkFrame(card3, fg_color="transparent")
        search_row.pack(fill="x", padx=16, pady=(4, 8))
        self.svc_search = ctk.CTkEntry(search_row, fg_color=COLORS["bg_elevated"],
                                       border_color=COLORS["border_bright"],
                                       text_color=COLORS["text"],
                                       font=ctk.CTkFont("Consolas", 12),
                                       placeholder_text="Поиск службы...", width=260)
        self.svc_search.pack(side="left", padx=(0, 8))
        NeonButton(search_row, "🔍 Найти", self._search_services, "primary", width=90).pack(side="left")

        self.svc_frame = ctk.CTkScrollableFrame(card3, fg_color=COLORS["bg_deep"],
                                                height=180, corner_radius=6)
        self.svc_frame.pack(fill="x", padx=16, pady=(0, 8))

        self._load_services()

        row = ctk.CTkFrame(card3, fg_color="transparent")
        row.pack(anchor="w", padx=16, pady=(0, 12))
        NeonButton(row, "🛑 Остановить выбранную", self._stop_service, "danger").pack(side="left", padx=(0, 8))
        NeonButton(row, "▶️ Запустить выбранную", self._start_service, "success").pack(side="left", padx=(0, 8))
        NeonButton(row, "🚫 Отключить", self._disable_service, "ghost").pack(side="left")

    def _load_services(self, filter_text=""):
        for w in self.svc_frame.winfo_children():
            w.destroy()
        self.selected_service = tk.StringVar()
        try:
            import win32service
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
            services = win32service.EnumServicesStatus(scm, win32service.SERVICE_WIN32,
                                                        win32service.SERVICE_STATE_ALL)
            win32service.CloseServiceHandle(scm)
            svc_list = [(s[0], s[1], s[2][1]) for s in services]
        except:
            # Fallback to sc query
            out, _ = run_cmd("sc query type= all state= all", capture=True)
            svc_list = []
            current = {}
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("SERVICE_NAME:"):
                    current["name"] = line.split(":", 1)[1].strip()
                elif line.startswith("DISPLAY_NAME:"):
                    current["display"] = line.split(":", 1)[1].strip()
                elif line.startswith("STATE"):
                    state_str = line.split(":", 1)[1].strip() if ":" in line else ""
                    current["state"] = 4 if "RUNNING" in state_str else 1
                    if "name" in current:
                        svc_list.append((current.get("name",""), current.get("display",""),
                                         current.get("state", 1)))
                    current = {}

        if filter_text:
            ft = filter_text.lower()
            svc_list = [s for s in svc_list if ft in s[0].lower() or ft in s[1].lower()]

        svc_list = svc_list[:80]  # limit for performance

        for name, display, state in svc_list:
            row = ctk.CTkFrame(self.svc_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            rb = ctk.CTkRadioButton(row, text="", variable=self.selected_service, value=name,
                                     fg_color=COLORS["accent"], border_color=COLORS["border_bright"])
            rb.pack(side="left")
            status_color = COLORS["green"] if state == 4 else COLORS["text_muted"]
            status_text = "▶ Работает" if state == 4 else "■ Остановлена"
            ctk.CTkLabel(row, text=f"{name[:30]:<30} {display[:35]:<35}",
                         text_color=COLORS["text"], font=ctk.CTkFont("Consolas", 10),
                         width=450).pack(side="left", padx=(4, 8))
            ctk.CTkLabel(row, text=status_text, text_color=status_color,
                         font=ctk.CTkFont("Consolas", 10), width=90).pack(side="left")

    def _search_services(self):
        self._load_services(self.svc_search.get())

    def _clean(self, path):
        if not path:
            run_cmd('ie4uinit.exe -show && RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess 8')
            self.log("Кэш миниатюр очищен", "ok")
            return
        cmd = f'cmd /c "del /f /q /s "{path}\\*.*" 2>nul"'
        threading.Thread(target=self._do_clean, args=(cmd, path), daemon=True).start()

    def _do_clean(self, cmd, path):
        self.progress.set(0.3)
        run_cmd(cmd)
        self.progress.set(1.0)
        self.log(f"Очищено: {path}", "ok")
        import time; time.sleep(1)
        self.progress.set(0)

    def _clean_all(self):
        def _worker():
            paths = ["%TEMP%", "%WINDIR%\\Temp", "%WINDIR%\\Prefetch"]
            for i, p in enumerate(paths):
                self.progress.set((i + 1) / len(paths))
                run_cmd(f'cmd /c "del /f /q /s "{p}\\*.*" 2>nul"')
            run_cmd("cleanmgr /sagerun:1")
            self.progress.set(1.0)
            self.log("Полная очистка завершена", "ok")
        threading.Thread(target=_worker, daemon=True).start()

    def _max_performance(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 2)
            winreg.CloseKey(key)
            self.log("Визуальные эффекты: максимальная производительность", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _max_visual(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.log("Визуальные эффекты: максимальная красота", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _windows_choice(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "VisualFXSetting", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self.log("Визуальные эффекты: выбор Windows", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _stop_service(self):
        svc = self.selected_service.get() if hasattr(self, "selected_service") else ""
        if not svc:
            self.log("Выберите службу!", "warn"); return
        run_cmd(f"sc stop {svc}")
        self.log(f"Служба остановлена: {svc}", "ok")

    def _start_service(self):
        svc = self.selected_service.get() if hasattr(self, "selected_service") else ""
        if not svc:
            self.log("Выберите службу!", "warn"); return
        run_cmd(f"sc start {svc}")
        self.log(f"Служба запущена: {svc}", "ok")

    def _disable_service(self):
        svc = self.selected_service.get() if hasattr(self, "selected_service") else ""
        if not svc:
            self.log("Выберите службу!", "warn"); return
        run_cmd(f"sc config {svc} start= disabled")
        self.log(f"Служба отключена: {svc}", "warn")


class DevToolsPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, log, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.log = log
        self._build()

    def _build(self):
        # Quick Access
        card = SectionCard(self, "🔧  Быстрый доступ к инструментам")
        card.pack(fill="x", padx=4, pady=(0, 10))

        tools = [
            ("📝 Редактор реестра",             "regedit"),
            ("🛡 Групповые политики",            "gpedit.msc"),
            ("🔵 PowerShell (Admin)",            'powershell -Command "Start-Process powershell -Verb RunAs"'),
            ("⬛ CMD (Admin)",                   'powershell -Command "Start-Process cmd -Verb RunAs"'),
            ("⚙️ Диспетчер устройств",           "devmgmt.msc"),
            ("💻 Управление компьютером",        "compmgmt.msc"),
            ("📊 Монитор ресурсов",              "resmon"),
            ("📈 Диспетчер задач",               "taskmgr"),
            ("🌐 Сетевые подключения",           "ncpa.cpl"),
            ("🔥 Брандмауэр Windows",            "wf.msc"),
            ("👥 Управление пользователями",     "lusrmgr.msc"),
            ("💾 Управление дисками",            "diskmgmt.msc"),
        ]

        for i in range(0, len(tools), 2):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            for label, cmd in tools[i:i+2]:
                NeonButton(row, label, lambda c=cmd: (run_cmd(c), self.log(f"Запущено: {c[:40]}", "info")),
                           "ghost", width=290).pack(side="left", padx=(0, 6))
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

        # Env Variables
        card2 = SectionCard(self, "📦  Переменные окружения")
        card2.pack(fill="x", padx=4, pady=(0, 10))

        row = ctk.CTkFrame(card2, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        NeonButton(row, "🔍 Открыть редактор", lambda: run_cmd(
            'rundll32 sysdm.cpl,EditEnvironmentVariables'), "primary").pack(side="left", padx=(0, 8))
        NeonButton(row, "📋 Просмотр PATH", self._show_path, "ghost").pack(side="left")

        self.env_text = ctk.CTkTextbox(card2, fg_color=COLORS["bg_deep"],
                                        text_color=COLORS["accent"],
                                        font=ctk.CTkFont("Consolas", 10),
                                        height=120)
        self.env_text.pack(fill="x", padx=16, pady=(4, 4))

        row2 = ctk.CTkFrame(card2, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row2, text="Имя:", text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Consolas", 12), width=50).pack(side="left")
        self.env_name = ctk.CTkEntry(row2, fg_color=COLORS["bg_elevated"],
                                      border_color=COLORS["border_bright"],
                                      text_color=COLORS["text"],
                                      font=ctk.CTkFont("Consolas", 11), width=150)
        self.env_name.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(row2, text="Значение:", text_color=COLORS["text_dim"],
                     font=ctk.CTkFont("Consolas", 12)).pack(side="left")
        self.env_val = ctk.CTkEntry(row2, fg_color=COLORS["bg_elevated"],
                                     border_color=COLORS["border_bright"],
                                     text_color=COLORS["text"],
                                     font=ctk.CTkFont("Consolas", 11), width=200)
        self.env_val.pack(side="left", padx=(0, 8))
        NeonButton(row2, "Добавить", self._add_env, "success", width=90).pack(side="left")
        ctk.CTkFrame(card2, height=8, fg_color="transparent").pack()

        # PowerShell Runner
        card3 = SectionCard(self, "💻  PowerShell консоль")
        card3.pack(fill="x", padx=4, pady=(0, 10))

        self.ps_input = ctk.CTkEntry(card3, fg_color=COLORS["bg_elevated"],
                                      border_color=COLORS["border_bright"],
                                      text_color=COLORS["text"],
                                      font=ctk.CTkFont("Consolas", 12),
                                      placeholder_text="Введите PowerShell команду...")
        self.ps_input.pack(fill="x", padx=16, pady=4)
        self.ps_input.bind("<Return>", lambda e: self._run_ps())

        row = ctk.CTkFrame(card3, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        NeonButton(row, "▶ Выполнить", self._run_ps, "primary").pack(side="left", padx=(0, 8))
        NeonButton(row, "🗑 Очистить вывод", self._clear_ps_out, "ghost").pack(side="left")

        self.ps_out = ctk.CTkTextbox(card3, fg_color=COLORS["bg_deep"],
                                      text_color=COLORS["green"],
                                      font=ctk.CTkFont("Consolas", 10),
                                      height=140)
        self.ps_out.pack(fill="x", padx=16, pady=(0, 12))

    def _show_path(self):
        path = os.environ.get("PATH", "")
        self.env_text.delete("1.0", "end")
        for p in path.split(";"):
            self.env_text.insert("end", p.strip() + "\n")

    def _add_env(self):
        name = self.env_name.get().strip()
        val  = self.env_val.get().strip()
        if not name:
            self.log("Введите имя переменной", "warn"); return
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, val)
            winreg.CloseKey(key)
            os.environ[name] = val
            self.log(f"Переменная добавлена: {name}={val[:30]}", "ok")
        except Exception as e:
            self.log(f"Ошибка: {e}", "error")

    def _run_ps(self):
        cmd = self.ps_input.get().strip()
        if not cmd:
            return
        def _worker():
            out, code = run_cmd(f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{cmd}"', capture=True)
            ts = datetime.now().strftime("%H:%M:%S")
            self.ps_out.configure(state="normal")
            self.ps_out.insert("end", f"\n{ts} PS> {cmd}\n{out}\n")
            self.ps_out.see("end")
            self.ps_out.configure(state="disabled")
            self.log(f"PS команда выполнена: {cmd[:40]}", "ok" if code == 0 else "error")
        threading.Thread(target=_worker, daemon=True).start()

    def _clear_ps_out(self):
        self.ps_out.configure(state="normal")
        self.ps_out.delete("1.0", "end")
        self.ps_out.configure(state="disabled")


# ─── Main Application ─────────────────────────────────────────────────────────
class WinAdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WinAdmin Pro")
        self.geometry("1280x800")
        self.minsize(960, 640)
        self.configure(fg_color=COLORS["bg_deep"])

        # Search index
        self.search_index = {}

        self._build_ui()

    def _build_ui(self):
        # Top bar
        topbar = ctk.CTkFrame(self, fg_color=COLORS["sidebar_bg"], height=52, corner_radius=0)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="⬡  WinAdmin Pro",
                     font=ctk.CTkFont("Consolas", 18, "bold"),
                     text_color=COLORS["accent"]).pack(side="left", padx=20)

        # Status info
        info_row = ctk.CTkFrame(topbar, fg_color="transparent")
        info_row.pack(side="left", padx=20)
        try:
            import socket
            hostname = socket.gethostname()
        except:
            hostname = "UNKNOWN"
        ctk.CTkLabel(info_row, text=f"🖥 {hostname}",
                     font=ctk.CTkFont("Consolas", 11), text_color=COLORS["text_muted"]).pack(side="left", padx=8)
        admin_badge = StatusBadge(topbar, "ADMIN" if is_admin() else "USER",
                                   "ok" if is_admin() else "warn")
        admin_badge.pack(side="left", padx=4)

        # Search
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)
        search = ctk.CTkEntry(topbar, textvariable=self.search_var,
                               fg_color=COLORS["bg_elevated"],
                               border_color=COLORS["border"],
                               text_color=COLORS["text"],
                               placeholder_text="🔍  Поиск по настройкам...",
                               font=ctk.CTkFont("Consolas", 12), width=260)
        search.pack(side="right", padx=16, pady=10)

        ctk.CTkLabel(topbar, text=datetime.now().strftime("%d.%m.%Y  %H:%M"),
                     font=ctk.CTkFont("Consolas", 11), text_color=COLORS["text_muted"]).pack(side="right", padx=8)

        # Main area
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True)

        # Sidebar
        sidebar = ctk.CTkFrame(main, fg_color=COLORS["sidebar_bg"], width=210,
                                corner_radius=0, border_width=1,
                                border_color=COLORS["border"])
        sidebar.pack(fill="y", side="left")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="НАВИГАЦИЯ",
                     font=ctk.CTkFont("Consolas", 10, "bold"),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=16, pady=(16, 6))

        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=12, pady=(0, 10))

        self.nav_buttons = {}
        self.active_tab = tk.StringVar(value="base")
        nav_items = [
            ("base",    "⚙️  Основные"),
            ("security","🛡  Безопасность"),
            ("custom",  "🎨  Персонализация"),
            ("perf",    "🚀  Оптимизация"),
            ("dev",     "🛠  Dev Tools"),
        ]

        for tab_id, label in nav_items:
            btn = ctk.CTkButton(sidebar, text=label,
                                command=lambda t=tab_id: self._switch_tab(t),
                                fg_color="transparent",
                                hover_color=COLORS["bg_elevated"],
                                text_color=COLORS["text_dim"],
                                anchor="w",
                                corner_radius=6,
                                font=ctk.CTkFont("Consolas", 13),
                                height=40)
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[tab_id] = btn

        # Log at bottom of sidebar
        ctk.CTkFrame(sidebar, height=1, fg_color=COLORS["border"]).pack(fill="x", padx=12, pady=(20, 8))
        ctk.CTkLabel(sidebar, text="КОНСОЛЬ",
                     font=ctk.CTkFont("Consolas", 10, "bold"),
                     text_color=COLORS["text_muted"]).pack(anchor="w", padx=16, pady=(0, 4))
        self.log_console = LogConsole(sidebar, height=200, width=190)
        self.log_console.pack(fill="x", padx=8, pady=(0, 8))

        # Content area
        self.content = ctk.CTkFrame(main, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.content.pack(fill="both", expand=True)

        # Build panels
        self.panels = {}
        self.panels["base"]     = BaseSettingsPanel(self.content, self.log)
        self.panels["security"] = SecurityPanel(self.content, self.log)
        self.panels["custom"]   = CustomizationPanel(self.content, self.log)
        self.panels["perf"]     = PerformancePanel(self.content, self.log)
        self.panels["dev"]      = DevToolsPanel(self.content, self.log)

        self._switch_tab("base")

        # System stats bar
        statsbar = ctk.CTkFrame(self, fg_color=COLORS["sidebar_bg"], height=26, corner_radius=0)
        statsbar.pack(fill="x", side="bottom")
        statsbar.pack_propagate(False)
        self.stats_label = ctk.CTkLabel(statsbar, text="",
                                         font=ctk.CTkFont("Consolas", 10),
                                         text_color=COLORS["text_muted"])
        self.stats_label.pack(side="left", padx=16)
        self._update_stats()

    def _switch_tab(self, tab_id):
        for tid, panel in self.panels.items():
            panel.pack_forget()

        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(fg_color=COLORS["accent_dim"], text_color=COLORS["accent"])
            else:
                btn.configure(fg_color="transparent", text_color=COLORS["text_dim"])

        panel = self.panels[tab_id]
        panel.pack(fill="both", expand=True, padx=8, pady=8)
        self.active_tab.set(tab_id)

    def log(self, msg, level="info"):
        self.log_console.log(msg, level)

    def _on_search(self, *args):
        query = self.search_var.get().strip().lower()
        if not query:
            return
        # Map keywords to tabs
        keywords = {
            "base":     ["имя", "компьютер", "время", "питание", "пк", "синхрон", "пояс"],
            "security": ["телеметр", "defender", "безопас", "история", "диагн", "конфиден"],
            "custom":   ["тема", "курсор", "звук", "прозрач", "значок", "рабочий стол", "mica"],
            "perf":     ["очист", "служб", "эффект", "temp", "prefetch", "производ"],
            "dev":      ["реестр", "powershell", "перемен", "политик", "среда", "cmd"],
        }
        for tab, keys in keywords.items():
            if any(k in query for k in keys):
                self._switch_tab(tab)
                self.log(f"Поиск: '{query}' → {tab}", "info")
                break

    def _update_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            self.stats_label.configure(
                text=f"CPU: {cpu:>5.1f}%   RAM: {mem.percent:>5.1f}%  ({mem.used//1024//1024:,} МБ)   "
                     f"Диск C: {disk.percent:.1f}%  ({disk.free//1024//1024//1024:.1f} ГБ свободно)"
            )
        except:
            pass
        self.after(3000, self._update_stats)


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if sys.platform != "win32":
        print("WinAdmin Pro работает только на Windows!")
        sys.exit(1)

    run_as_admin()

    app = WinAdminApp()
    app.mainloop()

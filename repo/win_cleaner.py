"""
win_cleaner.py — Системный менеджер Windows v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Вкладки: Дашборд · Темы · Приложения · Файлы · Политики
Требует прав администратора.
Зависимости: pip install psutil customtkinter
"""

# ╔══════════════════════════════════════════════════════════════╗
# ║                        ИМПОРТЫ                               ║
# ╚══════════════════════════════════════════════════════════════╝
import sys, os, ctypes, subprocess, threading, winreg
import time, shutil, logging, datetime
from pathlib import Path
from tkinter import messagebox, ttk, filedialog, simpledialog
import tkinter as tk

import psutil
import customtkinter as ctk

# ╔══════════════════════════════════════════════════════════════╗
# ║                     ЛОГИРОВАНИЕ                              ║
# ╚══════════════════════════════════════════════════════════════╝
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("win_cleaner.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ╔══════════════════════════════════════════════════════════════╗
# ║                  ЦВЕТОВАЯ ПАЛИТРА                            ║
# ╚══════════════════════════════════════════════════════════════╝
C = {
    "bg":          "#0f1117",   # основной фон
    "surface":     "#16191f",   # поверхность карточек
    "surface2":    "#1e222b",   # чуть светлее
    "border":      "#2a2f3d",   # рамки
    "accent":      "#3b82f6",   # синий акцент
    "accent_h":    "#60a5fa",   # hover акцента
    "danger":      "#ef4444",   # красный
    "danger_h":    "#f87171",
    "success":     "#22c55e",   # зелёный
    "success_h":   "#4ade80",
    "warn":        "#f59e0b",   # жёлтый
    "warn_h":      "#fbbf24",
    "purple":      "#8b5cf6",
    "purple_h":    "#a78bfa",
    "text":        "#e2e8f0",   # основной текст
    "text_dim":    "#64748b",   # приглушённый
    "text_bright": "#f8fafc",
}

FONT_MONO   = ("JetBrains Mono", 11)
FONT_MONO_B = ("JetBrains Mono", 11, "bold")
FONT_UI     = ("Segoe UI", 11)
FONT_UI_B   = ("Segoe UI", 11, "bold")
FONT_TITLE  = ("Segoe UI", 13, "bold")
FONT_H1     = ("Segoe UI", 16, "bold")


# ╔══════════════════════════════════════════════════════════════╗
# ║            МОДУЛЬ 1 — UAC ELEVATION                          ║
# ╚══════════════════════════════════════════════════════════════╝
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def elevate_if_needed():
    """Перезапускает скрипт с правами администратора через UAC."""
    if not is_admin():
        params = " ".join(f'"{a}"' for a in sys.argv)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1)
        if ret <= 32:
            log.error("UAC: не удалось повысить привилегии.")
        sys.exit(0)


# ╔══════════════════════════════════════════════════════════════╗
# ║         МОДУЛЬ 2 — ОЧИСТКА РЕЕСТРА (POLICIES)                ║
# ╚══════════════════════════════════════════════════════════════╝
POLICY_ROOTS = [
    (winreg.HKEY_CURRENT_USER,  r"Software\Policies"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies"),
    (winreg.HKEY_CURRENT_USER,
     r"Software\Microsoft\Windows\CurrentVersion\Policies"),
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies"),
]

# Значения, блокирующие экран персонализации
PERSONALIZATION_LOCKS = [
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Policies\Microsoft\Windows\Personalization",
     ["NoChangingLockScreen", "NoLockScreen",
      "PreventChangingTheme", "NoColorChoice"]),
    (winreg.HKEY_CURRENT_USER,
     r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
     ["NoThemesTab", "NoDispBackgroundPage",
      "NoDispScrSavPage", "NoDispCPL"]),
]

def _delete_key_recursive(hive, path: str) -> int:
    """Рекурсивно удаляет ключ реестра со всеми подключами."""
    deleted = 0
    try:
        with winreg.OpenKey(hive, path, 0,
                            winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    sub = winreg.EnumKey(key, 0)
                    deleted += _delete_key_recursive(hive, f"{path}\\{sub}")
                except OSError:
                    break
    except FileNotFoundError:
        return 0
    except PermissionError as e:
        log.warning(f"Нет доступа: {path} — {e}")
        return 0
    try:
        parent_path, _, key_name = path.rpartition("\\")
        with winreg.OpenKey(hive, parent_path, 0, winreg.KEY_WRITE) as p:
            winreg.DeleteKey(p, key_name)
        deleted += 1
    except (FileNotFoundError, PermissionError):
        pass
    return deleted

def clean_policy_registry(cb=None) -> str:
    """Удаляет политики реестра, блокирующие персонализацию."""
    total, lines = 0, []
    for hive, path, vals in PERSONALIZATION_LOCKS:
        for v in vals:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.DeleteValue(k, v)
                    lines.append(f"  ✓ Удалено значение: {v}")
                    total += 1
            except FileNotFoundError:
                pass
            except PermissionError as e:
                log.warning(f"Нет доступа к {v}: {e}")
    for hive, path in POLICY_ROOTS:
        if cb:
            h = "HKCU" if hive == winreg.HKEY_CURRENT_USER else "HKLM"
            cb(f"  Сканирую {h}\\{path}...")
        n = _delete_key_recursive(hive, path)
        if n:
            lines.append(f"  ✓ Удалено {n} ключей из ...\\{path.split(chr(92))[-1]}")
            total += n
    if lines:
        return (f"Очистка завершена. Удалено объектов: {total}\n"
                + "\n".join(lines))
    return "Политики не найдены — реестр уже чист."


# ╔══════════════════════════════════════════════════════════════╗
# ║         МОДУЛЬ 3 — EXPLORER + КЭШ                            ║
# ╚══════════════════════════════════════════════════════════════╝
def _kill_explorer():
    subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"],
                   capture_output=True)
    time.sleep(1.2)

def _clear_icon_cache():
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    deleted = []
    for pat in ["IconCache.db", "iconcache_*.db"]:
        for f in local.glob(pat):
            try:
                f.unlink()
                deleted.append(str(f))
            except Exception:
                pass
    return deleted

def _clear_theme_cache():
    td = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Themes"
    deleted = []
    if td.exists():
        for f in (list(td.glob("TranscodedWallpaper*"))
                  + list(td.glob("CachedFiles"))):
            try:
                if f.is_dir():
                    shutil.rmtree(f, ignore_errors=True)
                else:
                    f.unlink()
                deleted.append(str(f))
            except Exception:
                pass
    return deleted

def restart_explorer(cb=None) -> str:
    steps = []
    if cb: cb("  Завершаем explorer.exe…")
    _kill_explorer()
    steps.append("  ✓ explorer.exe остановлен")
    if cb: cb("  Очищаем кэш иконок…")
    icons = _clear_icon_cache()
    steps.append(f"  ✓ Иконки: удалено {len(icons)} файлов")
    if cb: cb("  Очищаем кэш тем…")
    themes = _clear_theme_cache()
    steps.append(f"  ✓ Темы: удалено {len(themes)} файлов")
    if cb: cb("  Запускаем explorer.exe…")
    subprocess.Popen(["explorer.exe"])
    steps.append("  ✓ explorer.exe запущен")
    return "\n".join(steps)


# ╔══════════════════════════════════════════════════════════════╗
# ║              МОДУЛЬ 4 — GPO RESET                            ║
# ╚══════════════════════════════════════════════════════════════╝
def reset_gpo(cb=None) -> str:
    results = []
    sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    for d in [sys32 / "GroupPolicy", sys32 / "GroupPolicyUsers"]:
        if d.exists():
            try:
                shutil.rmtree(d)
                results.append(f"  ✓ Удалена папка: {d.name}")
            except Exception as e:
                results.append(f"  ✗ Ошибка удаления {d.name}: {e}")
        else:
            results.append(f"  — Папка отсутствует: {d.name}")
    if cb: cb("  Выполняем gpupdate /force…")
    try:
        p = subprocess.run(["gpupdate", "/force"], capture_output=True,
                           text=True, timeout=120)
        out = (p.stdout or p.stderr or "").strip().split("\n")[0]
        results.append(f"  ✓ gpupdate: {out}")
    except subprocess.TimeoutExpired:
        results.append("  ✗ gpupdate завис — прерван по таймауту")
    except FileNotFoundError:
        results.append("  — gpupdate не найден (Home-редакция?)")
    return "\n".join(results)


# ╔══════════════════════════════════════════════════════════════╗
# ║         МОДУЛЬ 5 — ТЕМЫ И ПЕРСОНАЛИЗАЦИЯ                     ║
# ╚══════════════════════════════════════════════════════════════╝
_PERSONALIZE_KEY = (r"SOFTWARE\Microsoft\Windows"
                    r"\CurrentVersion\Themes\Personalize")

def get_system_theme() -> str:
    """Читает текущую тему Windows из реестра."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            _PERSONALIZE_KEY) as k:
            val, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
            return "light" if val == 1 else "dark"
    except Exception:
        return "unknown"

def set_system_theme(mode: str) -> bool:
    """Переключает тему Windows через реестр (AppsUseLightTheme)."""
    val = 1 if mode == "light" else 0
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            _PERSONALIZE_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "AppsUseLightTheme",    0,
                              winreg.REG_DWORD, val)
            winreg.SetValueEx(k, "SystemUsesLightTheme", 0,
                              winreg.REG_DWORD, val)
        log.info(f"Тема изменена: {mode}")
        return True
    except Exception as e:
        log.error(f"Ошибка смены темы: {e}")
        return False

def set_wallpaper(path: str) -> bool:
    """Устанавливает обои через WinAPI SystemParametersInfo."""
    try:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
        log.info(f"Обои установлены: {path}")
        return True
    except Exception as e:
        log.error(f"Ошибка установки обоев: {e}")
        return False


# ╔══════════════════════════════════════════════════════════════╗
# ║       МОДУЛЬ 6 — СПИСОК УСТАНОВЛЕННЫХ ПРИЛОЖЕНИЙ             ║
# ╚══════════════════════════════════════════════════════════════╝
_UNINSTALL_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

def get_installed_apps() -> list:
    """Читает список установленных программ из реестра."""
    apps, seen = [], set()
    for hive, base_path in _UNINSTALL_PATHS:
        try:
            with winreg.OpenKey(hive, base_path) as base:
                i = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(base, i)
                        i += 1
                        try:
                            with winreg.OpenKey(
                                    hive, f"{base_path}\\{sub_name}") as sub:
                                def _get(nm, df=""):
                                    try:
                                        v, _ = winreg.QueryValueEx(sub, nm)
                                        return str(v).strip()
                                    except Exception:
                                        return df
                                name = _get("DisplayName")
                                if not name or name in seen:
                                    continue
                                seen.add(name)
                                sz_kb = _get("EstimatedSize", "0")
                                try:
                                    sz_mb = (f"{int(sz_kb)//1024} МБ"
                                             if int(sz_kb) > 0 else "—")
                                except Exception:
                                    sz_mb = "—"
                                apps.append({
                                    "name":      name,
                                    "version":   _get("DisplayVersion", "—"),
                                    "publisher": _get("Publisher", "—"),
                                    "size":      sz_mb,
                                    "uninstall": _get("UninstallString"),
                                    "location":  _get("InstallLocation"),
                                })
                        except Exception:
                            pass
                    except OSError:
                        break
        except Exception:
            pass
    return sorted(apps, key=lambda a: a["name"].lower())


# ╔══════════════════════════════════════════════════════════════╗
# ║                   TTK-СТИЛИ (ТЁМНАЯ ТЕМА)                    ║
# ╚══════════════════════════════════════════════════════════════╝
def apply_dark_styles(style: ttk.Style):
    style.theme_use("clam")
    # Treeview
    style.configure("Treeview",
        background=C["surface2"], foreground=C["text"],
        rowheight=24, fieldbackground=C["surface2"],
        font=FONT_UI, borderwidth=0, relief="flat")
    style.configure("Treeview.Heading",
        background=C["surface"], foreground=C["text_dim"],
        font=FONT_UI_B, relief="flat", borderwidth=0)
    style.map("Treeview",
        background=[("selected", C["accent"])],
        foreground=[("selected", C["text_bright"])])
    # Notebook
    style.configure("Dark.TNotebook",
        background=C["bg"], borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("Dark.TNotebook.Tab",
        background=C["surface"], foreground=C["text_dim"],
        padding=[20, 9], font=FONT_UI_B, borderwidth=0)
    style.map("Dark.TNotebook.Tab",
        background=[("selected", C["surface2"]), ("active", C["surface2"])],
        foreground=[("selected", C["text_bright"]), ("active", C["text"])])
    # Scrollbars
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"Dark.{orient}.TScrollbar",
            background=C["surface2"], troughcolor=C["surface"],
            bordercolor=C["surface"], arrowcolor=C["text_dim"],
            relief="flat", borderwidth=0)


# ╔══════════════════════════════════════════════════════════════╗
# ║               ПЕРЕИСПОЛЬЗУЕМЫЕ КОМПОНЕНТЫ                    ║
# ╚══════════════════════════════════════════════════════════════╝
def make_btn(parent, text, cmd, color=None, hover=None, icon="", **kw):
    lbl = f"{icon}  {text}" if icon else text
    return ctk.CTkButton(
        parent, text=lbl, command=cmd,
        fg_color=color or C["accent"],
        hover_color=hover or C["accent_h"],
        text_color=C["text_bright"],
        corner_radius=6, height=34, font=FONT_UI_B, **kw)

def make_label(parent, text, font=None, color=None, **kw):
    return ctk.CTkLabel(parent, text=text,
                        font=font or FONT_UI,
                        text_color=color or C["text"], **kw)

def make_card(parent, **kw):
    return ctk.CTkFrame(
        parent,
        fg_color=kw.pop("fg_color", C["surface"]),
        corner_radius=kw.pop("corner_radius", 8),
        border_color=C["border"],
        border_width=kw.pop("border_width", 1),
        **kw)

def scrolled_tree(parent, columns, headings_widths, height=18):
    """Создаёт Treeview с вертикальным и горизонтальным скроллбарами."""
    frame = ctk.CTkFrame(parent, fg_color=C["surface2"],
                         corner_radius=6, border_width=0)
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    tree = ttk.Treeview(frame, columns=columns, show="headings",
                        selectmode="browse", height=height)
    for col, (heading, width, anchor) in zip(columns, headings_widths):
        tree.heading(col, text=heading,
                     command=lambda c=col, t=tree: _sort_tree(t, c, False))
        tree.column(col, width=width, anchor=anchor, minwidth=30)

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview,
                        style="Dark.Vertical.TScrollbar")
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview,
                        style="Dark.Horizontal.TScrollbar")
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    return frame, tree

def _sort_tree(tree: ttk.Treeview, col: str, desc: bool):
    """Сортировка колонки по клику на заголовок."""
    data = [(tree.set(iid, col), iid) for iid in tree.get_children("")]
    try:
        data.sort(
            key=lambda x: float(
                x[0].replace(" МБ","").replace(" КБ","")
                    .replace(" Б","").replace(",",".")),
            reverse=desc)
    except ValueError:
        data.sort(key=lambda x: x[0].lower(), reverse=desc)
    for idx, (_, iid) in enumerate(data):
        tree.move(iid, "", idx)
    tree.heading(col, command=lambda: _sort_tree(tree, col, not desc))


# ╔══════════════════════════════════════════════════════════════╗
# ║                    ГЛАВНОЕ ОКНО                              ║
# ╚══════════════════════════════════════════════════════════════╝
class App(ctk.CTk):
    REFRESH_MS = 1800   # интервал обновления метрик (мс)

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=C["bg"])
        self.title("Windows System Manager  v2.0")
        self.geometry("1120x760")
        self.minsize(920, 640)

        self._style = ttk.Style()
        apply_dark_styles(self._style)

        self._build_header()
        self._build_notebook()
        self._schedule_metrics()

    # ─────────────────────────────── ХЕДЕР ──
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=C["surface"],
                           corner_radius=0, border_width=0, height=52)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)

        make_label(hdr, "⚙  Windows System Manager",
                   font=FONT_H1, color=C["text_bright"]).pack(
            side="left", padx=20, pady=10)

        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.pack(side="right", padx=16)
        adm_text  = "🔐  Администратор" if is_admin() else "⚠  Без прав адм."
        adm_color = C["success"] if is_admin() else C["warn"]
        make_label(right, adm_text, color=adm_color,
                   font=FONT_UI_B).pack(side="right", padx=(14, 0))
        self._clock_lbl = make_label(right, "", color=C["text_dim"])
        self._clock_lbl.pack(side="right")
        self._tick_clock()

    def _tick_clock(self):
        self._clock_lbl.configure(
            text=datetime.datetime.now().strftime("%d.%m.%Y  %H:%M:%S"))
        self.after(1000, self._tick_clock)

    # ─────────────────────────── NOTEBOOK ──
    def _build_notebook(self):
        self._nb = ttk.Notebook(self, style="Dark.TNotebook")
        self._nb.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        tabs = [
            ("  📊  Дашборд",          self._build_tab_dashboard),
            ("  🎨  Темы",             self._build_tab_themes),
            ("  📦  Приложения",       self._build_tab_apps),
            ("  📁  Файловый менеджер",self._build_tab_files),
            ("  🛡  Политики",         self._build_tab_policies),
        ]
        for title, builder in tabs:
            frame = ctk.CTkFrame(self._nb, fg_color=C["bg"],
                                 corner_radius=0, border_width=0)
            self._nb.add(frame, text=title)
            builder(frame)

    # ══════════════════════════════════════
    # ВКЛАДКА 1 — ДАШБОРД
    # ══════════════════════════════════════
    def _build_tab_dashboard(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # ── Блок метрик ──
        metrics = make_card(parent, fg_color=C["surface"])
        metrics.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        metrics.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def metric_block(col, label, bar_color):
            f = ctk.CTkFrame(metrics, fg_color=C["surface2"],
                             corner_radius=6, border_width=0)
            f.grid(row=0, column=col, padx=8, pady=10, sticky="ew")
            make_label(f, label, color=C["text_dim"],
                       font=FONT_UI).pack(padx=12, pady=(8, 2), anchor="w")
            bar = ctk.CTkProgressBar(f, height=8, corner_radius=4,
                                     progress_color=bar_color,
                                     fg_color=C["border"])
            bar.pack(padx=12, pady=4, fill="x")
            bar.set(0)
            lbl = make_label(f, "—", color=C["text_bright"],
                             font=FONT_MONO_B)
            lbl.pack(padx=12, pady=(2, 10), anchor="w")
            return bar, lbl

        self.cpu_bar,  self.cpu_lbl  = metric_block(0, "CPU",  C["accent"])
        self.ram_bar,  self.ram_lbl  = metric_block(1, "RAM",  C["accent"])
        self.disk_bar, self.disk_lbl = metric_block(2, "Диск C:", C["warn"])

        # Аптайм
        f_up = ctk.CTkFrame(metrics, fg_color=C["surface2"],
                            corner_radius=6, border_width=0)
        f_up.grid(row=0, column=3, padx=8, pady=10, sticky="ew")
        make_label(f_up, "Аптайм", color=C["text_dim"],
                   font=FONT_UI).pack(padx=12, pady=(8, 2), anchor="w")
        self.uptime_lbl = make_label(f_up, "—", color=C["success"],
                                     font=FONT_MONO_B)
        self.uptime_lbl.pack(padx=12, pady=(14, 10), anchor="w")

        # ── Список процессов ──
        proc_card = make_card(parent)
        proc_card.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        proc_card.grid_rowconfigure(1, weight=1)
        proc_card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(proc_card, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="ew")
        make_label(hdr, "Активные процессы",
                   font=FONT_TITLE, color=C["text_bright"]).pack(side="left")
        make_btn(hdr, "Завершить процесс", self._kill_selected,
                 color=C["danger"], hover=C["danger_h"], icon="⛔").pack(
            side="right", padx=4)
        make_btn(hdr, "Обновить", self._refresh_proc_list,
                 color=C["surface2"], hover=C["border"], icon="🔄").pack(
            side="right", padx=4)

        cols = ("pid", "name", "cpu", "mem", "status")
        hw   = [("PID", 65, "center"), ("Процесс", 220, "w"),
                ("CPU %", 70, "center"), ("RAM МБ", 85, "center"),
                ("Статус", 95, "center")]
        tf, self.proc_tree = scrolled_tree(proc_card, cols, hw, height=22)
        tf.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def _update_metrics(self):
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        self.cpu_bar.set(cpu / 100)
        self.cpu_bar.configure(
            progress_color=C["danger"] if cpu > 80
            else C["warn"] if cpu > 50 else C["accent"])
        self.cpu_lbl.configure(text=f"{cpu:.1f}%")

        # RAM
        ram = psutil.virtual_memory()
        self.ram_bar.set(ram.percent / 100)
        self.ram_bar.configure(
            progress_color=C["danger"] if ram.percent > 85
            else C["warn"] if ram.percent > 65 else C["accent"])
        used = ram.used / 1024**3
        total = ram.total / 1024**3
        self.ram_lbl.configure(
            text=f"{ram.percent:.0f}%  ({used:.1f}/{total:.1f} ГБ)")

        # Disk
        try:
            disk = psutil.disk_usage("C:\\")
            self.disk_bar.set(disk.percent / 100)
            free = disk.free / 1024**3
            total_d = disk.total / 1024**3
            self.disk_lbl.configure(
                text=f"{disk.percent:.0f}%  (своб. {free:.0f}/{total_d:.0f} ГБ)")
        except Exception:
            pass

        # Uptime
        try:
            delta = int(time.time() - psutil.boot_time())
            d, r = divmod(delta, 86400)
            h, r = divmod(r, 3600)
            m, s = divmod(r, 60)
            self.uptime_lbl.configure(
                text=f"{d}д  {h:02d}:{m:02d}:{s:02d}")
        except Exception:
            pass

        self._refresh_proc_list()

    def _refresh_proc_list(self):
        # Сохраняем текущий выбор
        sel_pid = None
        sel = self.proc_tree.selection()
        if sel:
            sel_pid = self.proc_tree.item(sel[0])["values"][0]

        self.proc_tree.delete(*self.proc_tree.get_children())
        try:
            procs = sorted(
                psutil.process_iter(
                    ["pid", "name", "cpu_percent", "memory_info", "status"]),
                key=lambda p: p.info["cpu_percent"] or 0,
                reverse=True)[:100]
        except Exception:
            return
        for p in procs:
            try:
                mem = (p.info["memory_info"].rss / 1024**2
                       if p.info["memory_info"] else 0)
                iid = self.proc_tree.insert("", "end", values=(
                    p.info["pid"],
                    p.info["name"] or "—",
                    f"{p.info['cpu_percent'] or 0:.1f}",
                    f"{mem:.1f}",
                    p.info.get("status", "—"),
                ))
                if p.info["pid"] == sel_pid:
                    self.proc_tree.selection_set(iid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def _kill_selected(self):
        sel = self.proc_tree.selection()
        if not sel:
            messagebox.showinfo("Выбор", "Выберите процесс в списке.")
            return
        v = self.proc_tree.item(sel[0])["values"]
        pid, name = v[0], v[1]
        if messagebox.askyesno("Завершить",
                               f"Завершить '{name}' (PID {pid})?"):
            try:
                psutil.Process(int(pid)).kill()
                self._log(f"⛔ Процесс {name} (PID {pid}) завершён.")
            except psutil.AccessDenied:
                self._log(f"✗ Нет доступа к PID {pid}.")
            except psutil.NoSuchProcess:
                self._log(f"— PID {pid} уже не существует.")
            except Exception as e:
                self._log(f"✗ Ошибка: {e}")

    def _schedule_metrics(self):
        self._update_metrics()
        self.after(self.REFRESH_MS, self._schedule_metrics)

    # ══════════════════════════════════════
    # ВКЛАДКА 2 — ТЕМЫ
    # ══════════════════════════════════════
    def _build_tab_themes(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # ── Системная тема ──
        card1 = make_card(parent)
        card1.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="ew")
        card1.grid_columnconfigure(0, weight=1)

        top1 = ctk.CTkFrame(card1, fg_color="transparent")
        top1.pack(fill="x", padx=14, pady=(12, 8))
        make_label(top1, "Системная тема Windows",
                   font=FONT_TITLE, color=C["text_bright"]).pack(side="left")

        btn_row1 = ctk.CTkFrame(top1, fg_color="transparent")
        btn_row1.pack(side="right")
        make_btn(btn_row1, "Тёмная тема",
                 lambda: self._apply_theme("dark"),
                 color="#1e293b", hover="#334155", icon="🌙").pack(
            side="left", padx=4)
        make_btn(btn_row1, "Светлая тема",
                 lambda: self._apply_theme("light"),
                 color="#475569", hover="#64748b", icon="☀").pack(
            side="left", padx=4)

        self._theme_status = make_label(card1, "Определяю текущую тему…",
                                        color=C["text_dim"], font=FONT_UI)
        self._theme_status.pack(padx=14, pady=(0, 12), anchor="w")
        self._refresh_theme_status()

        # ── Обои ──
        card2 = make_card(parent)
        card2.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        card2.grid_columnconfigure(0, weight=1)

        top2 = ctk.CTkFrame(card2, fg_color="transparent")
        top2.pack(fill="x", padx=14, pady=(12, 8))
        make_label(top2, "Обои рабочего стола",
                   font=FONT_TITLE, color=C["text_bright"]).pack(side="left")

        btn_row2 = ctk.CTkFrame(top2, fg_color="transparent")
        btn_row2.pack(side="right")
        make_btn(btn_row2, "Выбрать файл…", self._pick_wallpaper,
                 color=C["surface2"], hover=C["border"], icon="🖼").pack(
            side="left", padx=4)
        make_btn(btn_row2, "Установить", self._apply_wallpaper,
                 color=C["accent"], hover=C["accent_h"], icon="✔").pack(
            side="left", padx=4)

        self._wallpaper_path = ctk.StringVar(value="Файл не выбран")
        ctk.CTkEntry(card2, textvariable=self._wallpaper_path,
                     fg_color=C["surface2"], border_color=C["border"],
                     text_color=C["text"], font=FONT_MONO,
                     state="readonly").pack(
            fill="x", padx=14, pady=(0, 12))

        # ── Быстрые действия ──
        card3 = make_card(parent)
        card3.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="nsew")
        make_label(card3, "Быстрые действия",
                   font=FONT_TITLE, color=C["text_bright"]).pack(
            padx=14, pady=(12, 8), anchor="w")
        act = ctk.CTkFrame(card3, fg_color="transparent")
        act.pack(padx=10, pady=(0, 12), anchor="w")
        for text, cmd, col, hov, icon in [
            ("Перезапустить Explorer",
             self._run_restart_explorer, "#1e3a5f", C["accent"], "🔄"),
            ("Открыть Персонализацию",
             lambda: self._open_ms("ms-settings:personalization-background"),
             C["surface2"], C["border"], "🎨"),
            ("Открыть настройки тем",
             lambda: self._open_ms("ms-settings:themes"),
             C["surface2"], C["border"], "🪄"),
        ]:
            make_btn(act, text, cmd, color=col, hover=hov,
                     icon=icon).pack(side="left", padx=6)

    def _refresh_theme_status(self):
        theme = get_system_theme()
        labels = {"dark":  "🌙  Текущая тема: Тёмная",
                  "light": "☀  Текущая тема: Светлая",
                  "unknown": "?  Тема не определена"}
        colors = {"dark": C["purple"], "light": C["warn"],
                  "unknown": C["text_dim"]}
        self._theme_status.configure(
            text=labels.get(theme, theme),
            text_color=colors.get(theme, C["text_dim"]))

    def _apply_theme(self, mode: str):
        if set_system_theme(mode):
            self._refresh_theme_status()
            self._log(f"✓ Тема: {'тёмная' if mode=='dark' else 'светлая'}")
            messagebox.showinfo("Тема изменена",
                "Тема применена.\nДля полного эффекта может потребоваться\n"
                "перезапуск Explorer или выход из системы.")
        else:
            self._log("✗ Не удалось изменить тему.")

    def _pick_wallpaper(self):
        f = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.bmp *.gif"),
                       ("Все файлы", "*.*")])
        if f:
            self._wallpaper_path.set(f)

    def _apply_wallpaper(self):
        p = self._wallpaper_path.get()
        if p == "Файл не выбран" or not os.path.isfile(p):
            messagebox.showwarning("Обои", "Сначала выберите файл.")
            return
        if set_wallpaper(p):
            self._log(f"✓ Обои: {Path(p).name}")
        else:
            self._log("✗ Не удалось установить обои.")

    def _open_ms(self, uri: str):
        try:
            subprocess.Popen(["explorer.exe", uri])
        except Exception as e:
            self._log(f"✗ Ошибка: {e}")

    # ══════════════════════════════════════
    # ВКЛАДКА 3 — ПРИЛОЖЕНИЯ
    # ══════════════════════════════════════
    def _build_tab_apps(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Тулбар
        toolbar = make_card(parent, fg_color=C["surface"])
        toolbar.grid(row=0, column=0, padx=12, pady=(12, 0), sticky="ew")
        toolbar.grid_columnconfigure(1, weight=1)

        make_label(toolbar, "Установленные программы",
                   font=FONT_TITLE, color=C["text_bright"]).grid(
            row=0, column=0, padx=14, pady=10, sticky="w")

        self._app_search = ctk.StringVar()
        self._app_search.trace_add("write", lambda *_: self._filter_apps())
        ctk.CTkEntry(toolbar, textvariable=self._app_search,
                     placeholder_text="🔍  Поиск по названию…",
                     fg_color=C["surface2"], border_color=C["border"],
                     text_color=C["text"], font=FONT_UI,
                     width=260).grid(row=0, column=1, padx=10, pady=10)

        btn_r = ctk.CTkFrame(toolbar, fg_color="transparent")
        btn_r.grid(row=0, column=2, padx=10, pady=10)
        make_btn(btn_r, "Обновить",
                 lambda: self._run_in_thread(self._load_apps_bg),
                 color=C["surface2"], hover=C["border"], icon="🔄").pack(
            side="left", padx=4)
        make_btn(btn_r, "Запустить", self._launch_app,
                 color=C["success"], hover=C["success_h"], icon="▶").pack(
            side="left", padx=4)
        make_btn(btn_r, "Деинсталлировать", self._uninstall_app,
                 color=C["danger"], hover=C["danger_h"], icon="🗑").pack(
            side="left", padx=4)

        # Список
        card = make_card(parent)
        card.grid(row=1, column=0, padx=12, pady=(6, 12), sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        cols = ("name", "version", "publisher", "size")
        hw   = [("Название", 300, "w"), ("Версия", 110, "center"),
                ("Издатель", 200, "w"), ("Размер", 90, "center")]
        tf, self.app_tree = scrolled_tree(card, cols, hw, height=24)
        tf.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        self._all_apps: list = []
        self._apps_hint = make_label(card, "Загрузка…", color=C["text_dim"])
        self._apps_hint.grid(row=1, column=0, pady=4)
        self._run_in_thread(self._load_apps_bg)

    def _load_apps_bg(self):
        apps = get_installed_apps()
        self._all_apps = apps
        self.after(0, self._populate_apps)

    def _populate_apps(self):
        self.app_tree.delete(*self.app_tree.get_children())
        q = self._app_search.get().lower()
        shown = ([a for a in self._all_apps if q in a["name"].lower()]
                 if q else self._all_apps)
        for a in shown:
            self.app_tree.insert("", "end", values=(
                a["name"], a["version"], a["publisher"], a["size"]))
        self._apps_hint.configure(
            text=f"Показано {len(shown)} из {len(self._all_apps)} программ")

    def _filter_apps(self):
        self._populate_apps()

    def _selected_app(self):
        sel = self.app_tree.selection()
        if not sel:
            messagebox.showinfo("Выбор", "Выберите приложение.")
            return None
        name = self.app_tree.item(sel[0])["values"][0]
        return next((a for a in self._all_apps if a["name"] == name), None)

    def _launch_app(self):
        app = self._selected_app()
        if not app:
            return
        loc = app.get("location", "")
        if loc and os.path.isdir(loc):
            try:
                exes = list(Path(loc).glob("*.exe"))
                if exes:
                    subprocess.Popen([str(exes[0])])
                    self._log(f"▶ Запущено: {exes[0].name}")
                    return
                os.startfile(loc)
                self._log(f"▶ Открыта папка: {loc}")
                return
            except Exception as e:
                self._log(f"✗ Ошибка запуска: {e}")
        messagebox.showinfo("Запуск",
            f"Путь не найден для: {app['name']}\n\n"
            "Откройте приложение из меню «Пуск».")

    def _uninstall_app(self):
        app = self._selected_app()
        if not app:
            return
        ucmd = app.get("uninstall", "")
        if not ucmd:
            messagebox.showwarning("Деинсталляция",
                f"Строка удаления не найдена:\n{app['name']}")
            return
        if messagebox.askyesno("Деинсталляция",
                f"Удалить?\n\n{app['name']} {app['version']}\n\n"
                "Запустится стандартный деинсталлятор."):
            try:
                subprocess.Popen(ucmd, shell=True)
                self._log(f"🗑 Деинсталляция: {app['name']}")
            except Exception as e:
                self._log(f"✗ Ошибка деинсталляции: {e}")

    # ══════════════════════════════════════
    # ВКЛАДКА 4 — ФАЙЛОВЫЙ МЕНЕДЖЕР
    # ══════════════════════════════════════
    def _build_tab_files(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        self._fm_path = ctk.StringVar(value=str(Path.home()))
        self._fm_current: Path = Path.home()

        # ── Навигация ──
        nav = make_card(parent, fg_color=C["surface"])
        nav.grid(row=0, column=0, padx=12, pady=(12, 0), sticky="ew")
        nav.grid_columnconfigure(3, weight=1)

        # Кнопки навигации
        make_btn(nav, "", self._fm_go_up,
                 color=C["surface2"], hover=C["border"],
                 icon="⬆", width=40).grid(row=0, column=0,
                                          padx=(10, 2), pady=6)
        make_btn(nav, "", self._fm_go_home,
                 color=C["surface2"], hover=C["border"],
                 icon="🏠", width=40).grid(row=0, column=1,
                                          padx=2, pady=6)

        path_e = ctk.CTkEntry(nav, textvariable=self._fm_path,
                              fg_color=C["surface2"],
                              border_color=C["border"],
                              text_color=C["text"], font=FONT_MONO)
        path_e.grid(row=0, column=3, padx=6, pady=6, sticky="ew")
        path_e.bind("<Return>",
                    lambda e: self._fm_navigate(self._fm_path.get()))

        make_btn(nav, "Перейти",
                 lambda: self._fm_navigate(self._fm_path.get()),
                 color=C["accent"], hover=C["accent_h"]).grid(
            row=0, column=4, padx=(4, 10), pady=6)

        # ── Операции ──
        ops = make_card(parent, fg_color=C["surface"])
        ops.grid(row=0, column=0, padx=12, pady=(60, 0), sticky="ew")
        ops_inner = ctk.CTkFrame(ops, fg_color="transparent")
        ops_inner.pack(padx=8, pady=7, anchor="w")
        for text, cmd, col, hov, icon in [
            ("Новая папка",  self._fm_mkdir,   C["success"],  C["success_h"], "📁"),
            ("Новый файл",   self._fm_mkfile,  C["accent"],   C["accent_h"],  "📄"),
            ("Переименовать",self._fm_rename,  C["warn"],     C["warn_h"],    "✏"),
            ("Удалить",      self._fm_delete,  C["danger"],   C["danger_h"],  "🗑"),
            ("Открыть",      self._fm_open,    C["surface2"], C["border"],    "🔎"),
        ]:
            make_btn(ops_inner, text, cmd, color=col,
                     hover=hov, icon=icon).pack(side="left", padx=4)

        # ── Список файлов ──
        card = make_card(parent)
        card.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="nsew")
        card.grid_rowconfigure(0, weight=1)
        card.grid_columnconfigure(0, weight=1)

        cols = ("icon", "name", "type", "size", "modified")
        hw   = [("", 28, "center"), ("Имя", 320, "w"),
                ("Тип", 80, "center"), ("Размер", 90, "center"),
                ("Изменён", 155, "center")]
        tf, self.fm_tree = scrolled_tree(card, cols, hw, height=26)
        self.fm_tree.column("icon", width=30, minwidth=30, stretch=False)
        tf.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        self.fm_tree.bind("<Double-1>", self._fm_on_dbl)
        self.fm_tree.bind("<BackSpace>", lambda e: self._fm_go_up())
        self._fm_navigate(str(self._fm_current))

    def _fm_navigate(self, path: str):
        p = Path(path)
        if not p.exists() or not p.is_dir():
            messagebox.showwarning("Навигация", f"Путь не найден:\n{path}")
            return
        self._fm_path.set(str(p))
        self._fm_current = p
        self._fm_reload()

    def _fm_reload(self):
        self.fm_tree.delete(*self.fm_tree.get_children())
        try:
            entries = sorted(self._fm_current.iterdir(),
                             key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            messagebox.showwarning("Доступ",
                                   f"Нет доступа к:\n{self._fm_current}")
            return
        for e in entries:
            try:
                if e.is_dir():
                    icon, ftype, size = "📁", "Папка", "—"
                else:
                    ext = e.suffix.lower()
                    icon = ("🖼" if ext in {".jpg",".png",".bmp",
                                            ".gif",".webp",".jpeg"}
                            else "📝" if ext in {".txt",".log",
                                                 ".md",".ini",".cfg"}
                            else "⚙" if ext in {".exe",".msi",
                                                 ".bat",".cmd",".ps1"}
                            else "🗜" if ext in {".zip",".rar",
                                                 ".7z",".tar"}
                            else "📄")
                    ftype = ext.lstrip(".").upper() or "Файл"
                    try:
                        sz = e.stat().st_size
                        size = (f"{sz/1024**2:.1f} МБ" if sz > 1024**2
                                else f"{sz/1024:.1f} КБ" if sz > 1024
                                else f"{sz} Б")
                    except Exception:
                        size = "—"
                try:
                    mtime = datetime.datetime.fromtimestamp(
                        e.stat().st_mtime).strftime("%d.%m.%Y  %H:%M")
                except Exception:
                    mtime = "—"
                self.fm_tree.insert("", "end",
                    values=(icon, e.name, ftype, size, mtime),
                    tags=("dir",) if e.is_dir() else ("file",))
            except Exception:
                pass
        self.fm_tree.tag_configure("dir",  foreground=C["accent_h"])
        self.fm_tree.tag_configure("file", foreground=C["text"])

    def _fm_sel_path(self):
        sel = self.fm_tree.selection()
        if not sel:
            return None
        return self._fm_current / self.fm_tree.item(sel[0])["values"][1]

    def _fm_on_dbl(self, _):
        p = self._fm_sel_path()
        if p and p.is_dir():
            self._fm_navigate(str(p))

    def _fm_go_up(self):
        par = self._fm_current.parent
        if par != self._fm_current:
            self._fm_navigate(str(par))

    def _fm_go_home(self):
        self._fm_navigate(str(Path.home()))

    def _fm_open(self):
        p = self._fm_sel_path()
        if p:
            try:
                os.startfile(str(p))
            except Exception as e:
                self._log(f"✗ Открытие: {e}")

    def _fm_mkdir(self):
        name = simpledialog.askstring("Новая папка", "Имя папки:", parent=self)
        if not name:
            return
        try:
            (self._fm_current / name).mkdir(exist_ok=False)
            self._log(f"📁 Создана папка: {name}")
            self._fm_reload()
        except FileExistsError:
            messagebox.showwarning("Ошибка", f"Уже существует: {name}")
        except Exception as e:
            self._log(f"✗ {e}")

    def _fm_mkfile(self):
        name = simpledialog.askstring("Новый файл", "Имя файла:", parent=self)
        if not name:
            return
        try:
            (self._fm_current / name).touch(exist_ok=False)
            self._log(f"📄 Создан файл: {name}")
            self._fm_reload()
        except FileExistsError:
            messagebox.showwarning("Ошибка", f"Уже существует: {name}")
        except Exception as e:
            self._log(f"✗ {e}")

    def _fm_rename(self):
        p = self._fm_sel_path()
        if not p:
            messagebox.showinfo("Выбор", "Выберите файл или папку.")
            return
        new = simpledialog.askstring("Переименовать", "Новое имя:",
                                     initialvalue=p.name, parent=self)
        if not new or new == p.name:
            return
        try:
            p.rename(p.parent / new)
            self._log(f"✏ {p.name} → {new}")
            self._fm_reload()
        except Exception as e:
            self._log(f"✗ {e}")

    def _fm_delete(self):
        p = self._fm_sel_path()
        if not p:
            messagebox.showinfo("Выбор", "Выберите файл или папку.")
            return
        kind = "папку" if p.is_dir() else "файл"
        if not messagebox.askyesno("Удалить",
                f"Удалить {kind}?\n\n{p.name}\n\n⚠ Необратимо!"):
            return
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            self._log(f"🗑 Удалено: {p.name}")
            self._fm_reload()
        except PermissionError:
            self._log(f"✗ Нет доступа: {p.name}")
        except Exception as e:
            self._log(f"✗ {e}")

    # ══════════════════════════════════════
    # ВКЛАДКА 5 — ПОЛИТИКИ
    # ══════════════════════════════════════
    def _build_tab_policies(self, parent):
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Кнопки
        card_btns = make_card(parent, fg_color=C["surface"])
        card_btns.grid(row=0, column=0, padx=12, pady=(12, 0), sticky="ew")
        make_label(card_btns, "Управление групповыми политиками",
                   font=FONT_TITLE, color=C["text_bright"]).pack(
            padx=14, pady=(12, 8), anchor="w")

        row = ctk.CTkFrame(card_btns, fg_color="transparent")
        row.pack(padx=10, pady=(0, 12), anchor="w")
        for text, cmd, col, hov, icon in [
            ("Очистить политики реестра",
             self._run_registry_clean, "#14532d", C["success"], "🧹"),
            ("Перезапустить Explorer",
             self._run_restart_explorer, "#1e3a5f", C["accent"], "🔄"),
            ("Сбросить GPO (gpupdate /force)",
             self._run_reset_gpo, "#7f1d1d", C["danger"], "🔒"),
        ]:
            make_btn(row, text, cmd, color=col,
                     hover=hov, icon=icon).pack(side="left", padx=6)

        # Журнал
        log_card = make_card(parent)
        log_card.grid(row=1, column=0, padx=12, pady=(6, 12), sticky="nsew")
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=10, pady=(10, 4), sticky="ew")
        make_label(hdr, "Журнал операций",
                   font=FONT_TITLE, color=C["text_bright"]).pack(side="left")
        make_btn(hdr, "Очистить", self._clear_log,
                 color=C["surface2"], hover=C["border"],
                 icon="🗑").pack(side="right")

        self.status_box = ctk.CTkTextbox(
            log_card, font=FONT_MONO,
            fg_color=C["surface2"], text_color=C["text"],
            border_width=0,
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"])
        self.status_box.grid(row=1, column=0, padx=10, pady=(0, 10),
                             sticky="nsew")
        self.status_box.configure(state="disabled")

        self._log("─────── Системный менеджер v2.0 запущен ───────")
        self._log(f"    Права администратора: {'✓ Да' if is_admin() else '✗ Нет'}")
        self._log(f"    Windows: {os.environ.get('OS','—')} / "
                  f"{os.environ.get('PROCESSOR_ARCHITECTURE','—')}")

    # ═══════════════════ ЛОГ ══════════════
    def _log(self, text: str):
        """Потокобезопасная запись в журнал."""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        def _w():
            try:
                self.status_box.configure(state="normal")
                self.status_box.insert("end", f"[{ts}]  {text}\n")
                self.status_box.see("end")
                self.status_box.configure(state="disabled")
            except Exception:
                pass
        self.after(0, _w)

    def _clear_log(self):
        self.status_box.configure(state="normal")
        self.status_box.delete("1.0", "end")
        self.status_box.configure(state="disabled")

    # ═══════════════ ФОНОВЫЕ ОПЕРАЦИИ ═════
    def _run_in_thread(self, func, *args):
        threading.Thread(target=func, args=args, daemon=True).start()

    def _run_registry_clean(self):
        self._log("▶ Запуск очистки реестра…")
        self._run_in_thread(self._do_registry_clean)

    def _do_registry_clean(self):
        result = clean_policy_registry(cb=self._log)
        self._log(result)
        messagebox.showinfo("Готово",
            "Очистка политик завершена.\n"
            "Рекомендуется перезагрузить Windows.")

    def _run_restart_explorer(self):
        if messagebox.askyesno("Перезапуск Explorer",
                "Рабочий стол кратковременно исчезнет.\nПродолжить?"):
            self._log("▶ Перезапуск Explorer…")
            self._run_in_thread(self._do_restart_explorer)

    def _do_restart_explorer(self):
        self._log(restart_explorer(cb=self._log))

    def _run_reset_gpo(self):
        if messagebox.askyesno("Сброс GPO",
                "Удалить все локальные политики\n"
                "и выполнить gpupdate /force?"):
            self._log("▶ Сброс GPO…")
            self._run_in_thread(self._do_reset_gpo)

    def _do_reset_gpo(self):
        result = reset_gpo(cb=self._log)
        self._log(result)
        messagebox.showinfo("Готово",
            "Сброс GPO завершён.\nРекомендуется перезагрузить Windows.")


# ╔══════════════════════════════════════════════════════════════╗
# ║                      ТОЧКА ВХОДА                             ║
# ╚══════════════════════════════════════════════════════════════╝
if __name__ == "__main__":
    elevate_if_needed()
    app = App()
    app.mainloop()

import os
import platform
import shutil
import socket
import subprocess
import tempfile
import winreg
from typing import Callable, Dict, List, Tuple

try:
    import psutil
except Exception:
    psutil = None


LogFn = Callable[[str], None]


def run_cmd(command: str, use_powershell: bool = False) -> Tuple[bool, str]:
    try:
        if use_powershell:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                capture_output=True,
                text=True,
                shell=False,
            )
        else:
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
        ok = result.returncode == 0
        output = (result.stdout or result.stderr or "").strip()
        return ok, output
    except Exception as exc:
        return False, str(exc)


def set_reg_dword(root, path: str, name: str, value: int) -> Tuple[bool, str]:
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
        winreg.CloseKey(key)
        return True, f"{name} = {value}"
    except Exception as exc:
        return False, str(exc)


def set_reg_string(root, path: str, name: str, value: str) -> Tuple[bool, str]:
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True, f"{name} = {value}"
    except Exception as exc:
        return False, str(exc)


def delete_reg_value(root, path: str, name: str) -> Tuple[bool, str]:
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        return True, f"Deleted {name}"
    except FileNotFoundError:
        return True, f"{name} did not exist"
    except Exception as exc:
        return False, str(exc)


def get_system_info() -> Dict[str, str]:
    windows_version = f"{platform.system()} {platform.release()} ({platform.version()})"
    return {
        "windows_version": windows_version,
        "pc_name": socket.gethostname(),
    }


def get_realtime_usage() -> Dict[str, str]:
    if psutil is None:
        return {"cpu": "N/A (install psutil)", "ram": "N/A (install psutil)"}
    cpu = f"{psutil.cpu_percent(interval=None):.0f}%"
    memory = psutil.virtual_memory()
    ram = f"{memory.percent:.0f}% ({memory.used // (1024**3)} / {memory.total // (1024**3)} GB)"
    return {"cpu": cpu, "ram": ram}


def restart_explorer(log: LogFn) -> None:
    ok1, out1 = run_cmd("taskkill /f /im explorer.exe")
    ok2, out2 = run_cmd("start explorer.exe")
    if ok1 and ok2:
        log("[OK] Explorer restarted")
    else:
        log(f"[ERR] Explorer restart failed: {out1 or out2}")


def disable_telemetry(log: LogFn) -> None:
    ok, msg = set_reg_dword(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
        "AllowTelemetry",
        0,
    )
    if ok:
        log("[OK] Telemetry disabled (AllowTelemetry = 0)")
    else:
        log(f"[ERR] Failed to disable telemetry: {msg}")


def disable_ads_and_suggestions(log: LogFn) -> None:
    results: List[Tuple[bool, str]] = []
    results.append(
        set_reg_dword(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
            "SubscribedContent-338388Enabled",
            0,
        )
    )
    results.append(
        set_reg_dword(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
            "SubscribedContent-353694Enabled",
            0,
        )
    )
    results.append(
        set_reg_dword(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings\Windows.SystemToast.SecurityAndMaintenance",
            "Enabled",
            0,
        )
    )
    failures = [msg for ok, msg in results if not ok]
    if failures:
        log(f"[ERR] Ads/notifications update partially failed: {' | '.join(failures)}")
    else:
        log("[OK] Start menu ads and promo notifications disabled")


def set_defender_enabled(enabled: bool, log: LogFn) -> None:
    value = 0 if enabled else 1
    ok, msg = set_reg_dword(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Policies\Microsoft\Windows Defender",
        "DisableAntiSpyware",
        value,
    )
    if not ok:
        log(f"[ERR] Defender policy update failed: {msg}")
        return

    ps_script = (
        "Set-MpPreference -DisableRealtimeMonitoring $false"
        if enabled
        else "Set-MpPreference -DisableRealtimeMonitoring $true"
    )
    ps_ok, ps_out = run_cmd(ps_script, use_powershell=True)
    if ps_ok:
        state = "enabled" if enabled else "disabled"
        log(f"[OK] Windows Defender {state} (policy + realtime monitoring)")
    else:
        log(f"[ERR] Policy written, but Defender realtime command failed: {ps_out}")


def enable_ultimate_performance(log: LogFn) -> None:
    guid = "e9a42b02-d5df-448d-aa00-03f14749eb61"
    ok, out = run_cmd(f"powercfg /setactive {guid}")
    if ok:
        log("[OK] Ultimate Performance power plan activated")
        return

    dup_ok, dup_out = run_cmd(f"powercfg /duplicatescheme {guid}")
    if not dup_ok:
        log(f"[ERR] Could not enable Ultimate Performance: {out or dup_out}")
        return
    ok2, out2 = run_cmd(f"powercfg /setactive {guid}")
    if ok2:
        log("[OK] Ultimate Performance unlocked and activated")
    else:
        log(f"[ERR] Plan unlocked but activation failed: {out2}")


def clean_system_cache_and_temp(log: LogFn) -> None:
    targets = [tempfile.gettempdir(), os.environ.get("TEMP", ""), os.environ.get("TMP", "")]
    removed = 0
    failed = 0
    seen = set()

    for path in targets:
        if not path or path in seen or not os.path.exists(path):
            continue
        seen.add(path)
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    os.remove(item_path)
                removed += 1
            except Exception:
                failed += 1

    run_cmd("ipconfig /flushdns")
    log(f"[OK] Temp cleanup completed: removed {removed}, failed {failed}; DNS cache flushed")


def optimize_visual_effects(log: LogFn) -> None:
    results = [
        set_reg_dword(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
            "VisualFXSetting",
            2,
        ),
        set_reg_string(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop\WindowMetrics",
            "MinAnimate",
            "0",
        ),
        set_reg_dword(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "TaskbarAnimations",
            0,
        ),
    ]
    failures = [msg for ok, msg in results if not ok]
    if failures:
        log(f"[ERR] Visual optimization partially failed: {' | '.join(failures)}")
    else:
        log("[OK] Visual effects optimized for performance")


def rename_computer(new_name: str, log: LogFn) -> None:
    if not new_name.strip():
        log("[ERR] New computer name is empty")
        return
    cmd = f"Rename-Computer -NewName '{new_name}' -Force"
    ok, out = run_cmd(cmd, use_powershell=True)
    if ok:
        log("[OK] Computer rename request applied. Restart required.")
    else:
        log(f"[ERR] Failed to rename computer: {out}")


def get_user_env_vars() -> Dict[str, str]:
    vars_map: Dict[str, str] = {}
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ)
        idx = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, idx)
                vars_map[name] = str(value)
                idx += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except Exception:
        return {}
    return dict(sorted(vars_map.items(), key=lambda x: x[0].lower()))


def set_user_env_var(name: str, value: str, log: LogFn) -> None:
    if not name.strip():
        log("[ERR] Variable name cannot be empty")
        return
    ok, msg = set_reg_string(winreg.HKEY_CURRENT_USER, r"Environment", name.strip(), value)
    if ok:
        log(f"[OK] Environment variable '{name}' saved")
    else:
        log(f"[ERR] Failed to set env var '{name}': {msg}")


def delete_user_env_var(name: str, log: LogFn) -> None:
    if not name.strip():
        log("[ERR] Variable name cannot be empty")
        return
    ok, msg = delete_reg_value(winreg.HKEY_CURRENT_USER, r"Environment", name.strip())
    if ok:
        log(f"[OK] Environment variable '{name}' removed")
    else:
        log(f"[ERR] Failed to delete env var '{name}': {msg}")


def open_system_tool(tool: str, log: LogFn) -> None:
    mapping = {
        "regedit": "regedit",
        "gpedit": "gpedit.msc",
        "services": "services.msc",
    }
    target = mapping.get(tool)
    if not target:
        log(f"[ERR] Unknown tool: {tool}")
        return
    ok, out = run_cmd(f"start {target}")
    if ok:
        log(f"[OK] Opened {target}")
    else:
        log(f"[ERR] Failed to open {target}: {out}")

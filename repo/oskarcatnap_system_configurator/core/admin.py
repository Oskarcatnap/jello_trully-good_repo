import ctypes
import os
import sys


def is_admin() -> bool:
    """Return True if current process has admin rights."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """Request elevation via UAC and relaunch current script."""
    try:
        params = " ".join([f'"{arg}"' for arg in sys.argv])
        rc = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            params,
            os.getcwd(),
            1,
        )
        return rc > 32
    except Exception:
        return False

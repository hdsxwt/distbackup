"""Windows-specific helpers (no-op on other platforms)."""

import os
import sys


def hide_dir(path: str) -> None:
    """Mark a directory as hidden on Windows. Does nothing on other OS."""
    if sys.platform != "win32":
        return
    if not os.path.isdir(path):
        return
    import ctypes
    FILE_ATTRIBUTE_HIDDEN = 0x2
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass

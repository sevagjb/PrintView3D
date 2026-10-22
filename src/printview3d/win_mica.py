"""Windows 11 "Mica": the window background takes a soft tint of the desktop wallpaper.

Windows draws the effect itself (DWM, on the graphics card); PrintView3D only asks for it and
leaves the background of the toolbar, side panel and status bar transparent (see
ui.theme.apply_theme(..., mica=True)). The 3D view always stays solid.

Needs Windows 11 22H2 or newer (build 22621). Elsewhere supported() is False and nothing changes.
Windows turns Mica off by itself when "Transparency effects" is off in Windows Settings, in
battery saver, and while the window is not active (it then shows a plain colour).
"""

from __future__ import annotations

import sys

MIN_BUILD = 22621                     # Windows 11 22H2: DWMWA_SYSTEMBACKDROP_TYPE

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_MAINWINDOW = 2                 # Mica
DWMSBT_TRANSIENTWINDOW = 3            # Acrylic (blur of what lies behind the window)
DWMSBT_TABBEDWINDOW = 4               # Mica Alt (stronger wallpaper tint)
BACKDROPS = {"mica": DWMSBT_MAINWINDOW, "acrylic": DWMSBT_TRANSIENTWINDOW, "mica-alt": DWMSBT_TABBEDWINDOW}


CHOICES = ("off", "mica", "acrylic")   # what Settings -> Appearance offers


def choice(settings) -> str:
    """The transparency chosen in Settings: "off", "mica" or "acrylic".
    0.15 only had an on/off switch for Mica ("mica": true); that still counts as "mica"."""
    value = settings.get("backdrop", "") or ("mica" if settings.get("mica", False) else "off")
    return value if value in CHOICES else "off"


def supported() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return sys.getwindowsversion().build >= MIN_BUILD
    except Exception:  # noqa: BLE001
        return False


def _set_int(hwnd: int, attr: int, value: int) -> bool:
    import ctypes
    v = ctypes.c_int(value)
    return ctypes.windll.dwmapi.DwmSetWindowAttribute(
        ctypes.c_void_p(hwnd), ctypes.c_uint(attr), ctypes.byref(v), ctypes.sizeof(v)) == 0


_kinds: dict[int, int] = {}            # hwnd -> backdrop type asked for (to ask again on a theme change)


def _refresh_frame(hwnd: int) -> None:
    """Windows keeps showing the old title bar and backdrop after a dark/light change until the
    window is deactivated or resized. Ask it to redraw the frame now."""
    import ctypes
    user32 = ctypes.windll.user32
    SWP = 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020      # NOSIZE NOMOVE NOZORDER NOACTIVATE FRAMECHANGED
    user32.SetWindowPos(ctypes.c_void_p(hwnd), None, 0, 0, 0, 0, SWP)
    RDW = 0x0001 | 0x0080 | 0x0100 | 0x0400               # INVALIDATE ALLCHILDREN UPDATENOW FRAME
    user32.RedrawWindow(ctypes.c_void_p(hwnd), None, None, RDW)


def set_dark(hwnd: int, dark: bool) -> bool:
    """Dark or light Mica (and title bar), to match the theme."""
    if not supported():
        return False
    try:
        ok = _set_int(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)
        if hwnd in _kinds:                                 # backdrop already on: ask again, then redraw
            _set_int(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, _kinds[hwnd])
            _refresh_frame(hwnd)
        return ok
    except Exception:  # noqa: BLE001
        return False


def apply(hwnd: int, dark: bool, kind: str = "mica") -> bool:
    """Ask Windows for Mica (or kind: "mica-alt", "acrylic") behind the whole window.
    True when Windows accepted it."""
    if not supported():
        return False
    try:
        import ctypes

        class MARGINS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_int), ("r", ctypes.c_int), ("t", ctypes.c_int), ("b", ctypes.c_int)]

        set_dark(hwnd, dark)
        # The "glass" frame covers the whole window, so the backdrop shows behind our content.
        ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(ctypes.c_void_p(hwnd), ctypes.byref(MARGINS(-1, -1, -1, -1)))
        value = BACKDROPS.get(kind, DWMSBT_MAINWINDOW)
        ok = _set_int(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, value)
        if ok:
            _kinds[hwnd] = value
        return ok
    except Exception:  # noqa: BLE001 - never let a visual effect break the program
        return False


def dark_mode(hwnd: int) -> int:
    """1 when Windows draws the window's title bar and backdrop dark, 0 light, -1 unknown (CI)."""
    try:
        import ctypes
        v = ctypes.c_int(-1)
        ok = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.c_void_p(hwnd), ctypes.c_uint(DWMWA_USE_IMMERSIVE_DARK_MODE), ctypes.byref(v), ctypes.sizeof(v)) == 0
        return v.value if ok else -1
    except Exception:  # noqa: BLE001
        return -1


def backdrop(hwnd: int) -> int:
    """The backdrop type Windows reports for the window (for the CI self-test); -1 if unknown."""
    try:
        import ctypes
        v = ctypes.c_int(-1)
        ok = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.c_void_p(hwnd), ctypes.c_uint(DWMWA_SYSTEMBACKDROP_TYPE), ctypes.byref(v), ctypes.sizeof(v)) == 0
        return v.value if ok else -1
    except Exception:  # noqa: BLE001
        return -1

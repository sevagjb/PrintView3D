"""The keyboard shortcuts of the main window: their defaults, the ones the user set
(Settings -> Keyboard and mouse), and which keys may not be used.

Keys are stored as Qt's portable text ("Ctrl+Shift+T", "F", "PgUp"). Only the keys that differ
from the default are saved, in the setting "shortcuts" ({id: key}); "" means no key. Qt writes
Ctrl as Cmd on a Mac, so the same text works there.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

from ..i18n import tr

# (id, default key), in the order of the list in Settings.
DEFAULTS: list[tuple[str, str]] = [
    ("open", "Ctrl+O"),
    ("home", "Ctrl+W"),
    ("slicer", "Ctrl+P"),
    ("export", "Ctrl+E"),
    ("settings", "S"),
    ("screenshot", "Ctrl+Shift+S"),
    ("next_theme", "Ctrl+T"),
    ("light_dark", "Ctrl+Shift+T"),
    ("fit", "F"),
    ("iso", "1"),
    ("top", "2"),
    ("front", "3"),
    ("right", "4"),
    ("plate", "P"),
    ("check", "C"),
    ("view", "V"),
    ("wireframe", "W"),
    ("xray", "X"),
    ("clip_top", "T"),
    ("clip_face", "Y"),
    ("lock_face", "L"),
    ("reset_view", "R"),
    ("measure", "M"),
    ("distance", "D"),
    ("angle", "A"),
    ("circle", "O"),
    ("measure_clear", "K"),
    ("next", "Up"),
    ("previous", "Down"),
    ("up10", "PgUp"),
    ("down10", "PgDown"),
    ("first", "Home"),
    ("last", "End"),
]
DEFAULT = dict(DEFAULTS)
IDS = [i for i, _ in DEFAULTS]


def descriptions() -> dict[str, str]:
    """What each key does, as the list in Settings says it."""
    view = tr("{view} view")
    return {
        "open": tr("Open a file"),
        "home": tr("Close the file (back to the start page)"),
        "slicer": tr("Open the file in your slicer"),
        "export": tr("Export STL (3MF, FreeCAD and STEP)"),
        "settings": tr("Settings"),
        "screenshot": tr("Save a screenshot of the 3D view"),
        "next_theme": tr("Next theme style"),
        "light_dark": tr("Switch between light and dark"),
        "fit": view.format(view=tr("Fit")),
        "iso": view.format(view=tr("Iso")),
        "top": view.format(view=tr("Top")),
        "front": view.format(view=tr("Front")),
        "right": view.format(view=tr("Right")),
        "plate": tr("Build plate on / off"),
        "check": tr("Check model on / off (models)"),
        "view": tr("View section on / off (models)"),
        "wireframe": tr("Wireframe on / off (models)"),
        "xray": tr("X-ray (see-through) on / off (models)"),
        "clip_top": tr("Clip from the top on / off (models)"),
        "clip_face": tr("Clip facing you on / off (models)"),
        "lock_face": tr("Lock the facing cut: it stops turning with the view (models)"),
        "reset_view": tr("Reset view: all of the above off, model fitted (models)"),
        "measure": tr("Measure on / off (models)"),
        "distance": tr("Measure a distance"),
        "measure_clear": tr("Remove all measurements (Measure stays on)"),
        "angle": tr("Measure an angle"),
        "circle": tr("Measure a circle"),
        "next": tr("Next layer (G-code), or the file above in the list (ZIP or folder)"),
        "previous": tr("Previous layer (G-code), or the file below in the list (ZIP or folder)"),
        "up10": tr("10 layers up"),
        "down10": tr("10 layers down"),
        "first": tr("First layer"),
        "last": tr("Last layer"),
    }


def normalize(seq: str) -> str:
    """One key in Qt's portable text ("ctrl+shift+t" -> "Ctrl+Shift+T"); "" for none or junk."""
    ks = QKeySequence(seq or "")
    if ks.isEmpty():
        return ""
    return QKeySequence(ks[0]).toString(QKeySequence.PortableText)


def current(settings) -> dict[str, str]:
    """{id: key} with the user's keys in place of the defaults."""
    saved = settings.get("shortcuts", {}) or {}
    out = {}
    for i, default in DEFAULTS:
        out[i] = normalize(saved[i]) if isinstance(saved.get(i), str) else default
    return out


def save(settings, keys: dict[str, str]) -> None:
    """Keep only the keys that differ from the default."""
    settings.set("shortcuts", {i: k for i, k in ((i, normalize(keys.get(i, DEFAULT[i]))) for i in IDS)
                               if k != DEFAULT[i]})


def native(seq: str) -> str:
    """A key as the system writes it (Ctrl+O on Windows and Linux, ⌘O on a Mac)."""
    return QKeySequence(seq).toString(QKeySequence.NativeText) if seq else ""


def with_key(text: str, seq: str) -> str:
    """'Measure (M)'; just 'Measure' when it has no key."""
    return f"{text} ({native(seq)})" if seq else text


# ------------------------------------------------------------------ keys the system keeps
_MOD_KEYS = {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr, Qt.Key_Super_L,
             Qt.Key_Super_R, Qt.Key_Hyper_L, Qt.Key_Hyper_R, Qt.Key_CapsLock, Qt.Key_NumLock,
             Qt.Key_ScrollLock}
# Keys that move the focus, confirm or cancel, or reach the system: never a shortcut.
_NEVER_KEYS = {Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Print,
               Qt.Key_SysReq, Qt.Key_Menu, Qt.Key_Sleep, Qt.Key_PowerOff, Qt.Key_WakeUp}

# Combinations the system uses, per platform (as Qt writes them; on a Mac Qt's "Ctrl" is ⌘ and
# "Meta" is the Control key).
_RESERVED = {
    "win32": ["Alt+Tab", "Alt+Shift+Tab", "Alt+F4", "Alt+Esc", "Alt+Space", "Ctrl+Esc",
              "Ctrl+Alt+Del", "Ctrl+Shift+Esc", "Ctrl+Alt+Tab", "Alt+Print"],
    "linux": ["Alt+Tab", "Alt+Shift+Tab", "Alt+F4", "Alt+F1", "Alt+F2", "Alt+F7", "Alt+F8",
              "Alt+F10", "Alt+Space", "Alt+Esc", "Ctrl+Alt+Del", "Ctrl+Alt+T", "Ctrl+Alt+L",
              "Ctrl+Alt+Backspace", "Ctrl+Alt+Left", "Ctrl+Alt+Right", "Ctrl+Alt+Up", "Ctrl+Alt+Down",
              "Ctrl+Alt+D", *[f"Ctrl+Alt+F{n}" for n in range(1, 13)]],
    "darwin": ["Ctrl+Q", "Ctrl+H", "Ctrl+Alt+H", "Ctrl+M", "Ctrl+Tab", "Ctrl+Shift+Tab", "Ctrl+Space",
               "Ctrl+Alt+Space", "Ctrl+`", "Ctrl+Alt+Esc", "Ctrl+Shift+3", "Ctrl+Shift+4",
               "Ctrl+Shift+5", "Ctrl+Alt+D", "Ctrl+Shift+Q", "Ctrl+Alt+Q", "Ctrl+Meta+Q",
               "Ctrl+Meta+F", "Ctrl+Meta+Space", "Meta+Space", "Meta+Alt+Space", "Meta+Up",
               "Meta+Down", "Meta+Left", "Meta+Right", "Ctrl+Alt+Eject", "Ctrl+Comma"],
}


def _platform(platform: str | None) -> str:
    p = platform or sys.platform
    return "linux" if p.startswith("linux") or p.startswith("freebsd") else p


def problem(seq: str, platform: str | None = None) -> str:
    """Why this key can't be a shortcut ("" when it can): it belongs to the system (Windows,
    macOS or Linux), or it moves the focus, confirms or cancels."""
    seq = normalize(seq)
    if not seq:
        return ""
    combo = QKeySequence(seq)[0]
    key, mods = combo.key(), combo.keyboardModifiers()
    plat = _platform(platform)
    if key in _MOD_KEYS:
        return tr("A key like Ctrl, Shift or Alt needs another key with it.")
    if key in _NEVER_KEYS:
        return tr("{key} is kept for the system or for moving around in the window.").format(key=native(seq))
    # The Windows key and the Super key belong to the system (Start menu, the desktop's own keys).
    # On a Mac Qt calls the Control key Meta; only some of its combinations are taken (below).
    if mods & Qt.MetaModifier and plat != "darwin":
        return tr("Keys with the Windows or Super key belong to the system.")
    reserved = {normalize(s) for s in _RESERVED.get(plat, [])}
    if seq in reserved:
        return tr("{key} is used by the system.").format(key=native(seq))
    if key == Qt.Key_Space and not mods:
        return tr("{key} is kept for the system or for moving around in the window.").format(key=native(seq))
    return ""


def conflicts(keys: dict[str, str]) -> dict[str, list[str]]:
    """{key: [ids]} for every key given to more than one shortcut."""
    seen: dict[str, list[str]] = {}
    for i in IDS:
        k = normalize(keys.get(i, ""))
        if k:
            seen.setdefault(k, []).append(i)
    return {k: v for k, v in seen.items() if len(v) > 1}

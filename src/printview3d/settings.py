"""Small JSON settings store.

Windows:  %APPDATA%\\PrintView3D\\settings.json
Linux:    ~/.config/printview3d/settings.json  (or $XDG_CONFIG_HOME)
macOS:    ~/Library/Application Support/PrintView3D/settings.json
"""

from __future__ import annotations

import json
import os
import sys

DEFAULTS = {
    "language": "en",
    "backdrop": "",             # Windows 11 transparency: "off", "mica" or "acrylic" ("" = from "mica")
    "mica": False,              # 0.15: the old on/off switch for Mica (read by win_mica.choice())
    "theme": "auto",            # "auto" = follow the system; or a key of ui.theme.THEMES           # "auto" = system language; otherwise a code from i18n.LANGUAGES
    "slicer_id": "",            # default slicer; empty = first installed one
    "slicer_paths": {},         # {slicer_id: exe} picked manually in Settings
    "custom_slicer": {},
    "freecad_path": "",         # FreeCAD program picked in Settings; empty = find automatically        # {"name": ..., "path": ...} for any other program
    "slicer_path": "",          # v0.1/v0.2 setting, migrated into slicer_paths
    "update_check": None,       # None = not asked yet; True/False = automatic daily check on/off
    "update_last_check": 0,     # time of the last check (seconds since 1970)
    "update_last_ok": 0,        # time of the last check that reached GitHub
    "update_latest": {},        # newest release seen on GitHub (version, notes, download)
    "update_skip": "",          # version the user chose to skip
    "new_window": False,         # Settings -> Files: True = every file in its own window
    "export_mode": "dialog",    # Settings -> Files: what a click on Export STL does (EXPORT_MODES)
    "star_prompt_shown": False, # the one-time "star us on GitHub" message (new installs only)
    "start_count": 0,           # how often the main window started (first start: no questions)
    "last_run_version": "",     # version of the last start; "" = new install ("What's new" after updates)
    "recent_files": [],
    "show_travel": False,
    "show_bed": True,
    "max_recent": 10,
}

# Export STL: show the list of objects, save all in one STL, or one STL per object.
EXPORT_MODES = ("dialog", "combined", "per_object")


def settings_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "PrintView3D")
    if sys.platform == "darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "PrintView3D")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "printview3d")


class Settings:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(settings_dir(), "settings.json")
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                # People who used PrintView3D before themes existed keep the
                # dark look they know; new installs follow the system.
                stored.setdefault("theme", "dark")
                # The GitHub star message is for new installs; people updating
                # from an older version never see it.
                stored.setdefault("star_prompt_shown", True)
                # Settings from before 0.21.2 belong to people who have started PrintView3D
                # before: nothing about their start changes.
                stored.setdefault("start_count", 2)
                # Versions before 0.18 didn't record themselves. Treat them as 0.17, so people
                # updating see what's new in 0.18 rather than the whole history.
                stored.setdefault("last_run_version", "0.17.0")
                self.data.update(stored)
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def get(self, key, default=None):
        return self.data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def add_recent(self, path: str):
        path = os.path.abspath(path)
        recent = [p for p in self.get("recent_files", []) if os.path.normcase(p) != os.path.normcase(path)]
        recent.insert(0, path)
        self.set("recent_files", recent[: int(self.get("max_recent", 10))])

    def clear_recent(self):
        self.set("recent_files", [])

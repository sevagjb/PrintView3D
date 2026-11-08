"""Find and launch slicers.

PrintView3D can hand the current file to any slicer. Known slicers are listed
in SLICERS and found automatically; any other program can be chosen as a
"Custom" slicer in Settings.

Detection for a known slicer, in order:
  1. A path the user picked manually (Settings)
  Windows:
  2. "App Paths" registry entries
  3. Uninstall entries whose display name matches the slicer
  4. Common install folders (Program Files, LocalAppData)
  Linux:
  2. AppImages in the usual places (~/Applications, ~/Downloads, /opt, ...)
  3. Flatpak and Snap launchers
  4. Programs installed in /opt/<name>/
  Everywhere:
  5. The PATH (distribution packages, portable installs)
The newest version wins when several copies are installed.

All slicers listed here accept a file path on the command line, which is
how Windows "Open with" and Linux file managers start them too.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

CUSTOM = "custom"


@dataclass(frozen=True)
class Slicer:
    id: str
    name: str
    exe_names: tuple[str, ...]                 # exact file names, most likely first
    keywords: tuple[str, ...]                  # fallback: exe name contains one of these
    display_name: str                          # regex for the Windows uninstall entry
    folders: tuple[str, ...] = field(default_factory=tuple)  # globs under Program Files etc.
    # Linux: command names on the PATH, and the text that identifies the slicer in
    # AppImage / Flatpak / Snap file names (compared without spaces, - and _).
    linux_bins: tuple[str, ...] = field(default_factory=tuple)
    linux_match: tuple[str, ...] = field(default_factory=tuple)


SLICERS: list[Slicer] = [
    Slicer("creality_print", "Creality Print",
           ("CrealityPrint.exe", "Creality Print.exe", "CrealityPrint6.exe"),
           ("crealityprint", "creality print"),
           r"creality\s*print",
           (r"Creality\Creality Print*", "Creality Print*", "CrealityPrint*",
            r"Programs\Creality*", r"Programs\Creality\Creality Print*"),
           ("CrealityPrint", "crealityprint", "creality-print"), ("crealityprint",)),
    Slicer("orcaslicer", "OrcaSlicer",
           ("orca-slicer.exe", "OrcaSlicer.exe"),
           ("orca-slicer", "orcaslicer"),
           r"^orca\s*slicer",
           ("OrcaSlicer*", r"Programs\OrcaSlicer*"),
           ("orca-slicer", "OrcaSlicer", "orcaslicer"), ("orcaslicer",)),
    Slicer("bambu_studio", "Bambu Studio",
           ("bambu-studio.exe", "BambuStudio.exe"),
           ("bambu-studio", "bambustudio"),
           r"bambu\s*studio",
           (r"Bambu Studio*", r"BambuStudio*", r"Bambu Lab\Bambu Studio*"),
           ("bambu-studio", "BambuStudio", "bambustudio"), ("bambustudio",)),
    Slicer("prusaslicer", "PrusaSlicer",
           ("prusa-slicer.exe", "PrusaSlicer.exe"),
           ("prusa-slicer", "prusaslicer"),
           r"prusa\s*slicer",
           (r"Prusa3D\PrusaSlicer*", r"PrusaSlicer*"),
           ("prusa-slicer", "PrusaSlicer", "prusaslicer"), ("prusaslicer",)),
    Slicer("cura", "UltiMaker Cura",
           ("UltiMaker-Cura.exe", "Ultimaker-Cura.exe", "Cura.exe"),
           ("ultimaker-cura", "cura"),
           r"\bcura\b",
           ("UltiMaker Cura*", "Ultimaker Cura*"),
           ("cura", "ultimaker-cura", "UltiMaker-Cura"), ("ultimakercura", "comultimakercura")),
    Slicer("elegoo_slicer", "Elegoo Slicer",
           ("elegoo-slicer.exe", "ElegooSlicer.exe"),
           ("elegoo",),
           r"elegoo\s*slicer",
           ("ElegooSlicer*", r"ELEGOO\ElegooSlicer*", "Elegoo Slicer*"),
           ("elegoo-slicer", "ElegooSlicer", "elegooslicer"), ("elegooslicer",)),
    Slicer("anycubic_slicer_next", "Anycubic Slicer Next",
           ("AnycubicSlicerNext.exe", "anycubic-slicer-next.exe"),
           ("anycubic",),
           r"anycubic\s*slicer\s*next",
           ("AnycubicSlicerNext*", r"Anycubic\AnycubicSlicerNext*", "Anycubic Slicer Next*"),
           ("AnycubicSlicerNext", "anycubic-slicer-next", "anycubicslicernext"), ("anycubicslicer",)),
]
BY_ID = {s.id: s for s in SLICERS}

# Slicers that open STEP files themselves; the others get an STL that FreeCAD made.
STEP_SLICERS = frozenset({"orcaslicer", "prusaslicer", "bambu_studio"})


def reads_step(slicer_id: str) -> bool:
    return slicer_id in STEP_SLICERS

# Helper programs that live next to the real slicer and must never be launched.
_EXCLUDE = ("uninst", "update", "crash", "console", "gcodeviewer", "gcode-viewer", "engine",
            "helper", "setup", "redist", "qtwebengine", "dumper", "elevate", "repair")


def slicer_name(slicer_id: str, custom_name: str = "") -> str:
    if slicer_id == CUSTOM:
        return custom_name or "custom slicer"
    s = BY_ID.get(slicer_id)
    return s.name if s else "slicer"


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------
def _version_key(path: str):
    # Version numbers appear in folder names (Windows) or file names (AppImages).
    nums = re.findall(r"\d+", path)
    return ([int(n) for n in nums[-4:]], os.path.getmtime(path) if os.path.exists(path) else 0)


def _usable(path: str) -> bool:
    base = os.path.basename(path).lower()
    return os.path.isfile(path) and not any(x in base for x in _EXCLUDE)


def _exe_in_folder(s: Slicer, folder: str) -> list[str]:
    if not folder or not os.path.isdir(folder):
        return []
    found = [os.path.join(folder, n) for n in s.exe_names if os.path.isfile(os.path.join(folder, n))]
    if not found:
        for p in glob.glob(os.path.join(folder, "*.exe")):
            base = os.path.basename(p).lower()
            if any(k in base for k in s.keywords) and _usable(p):
                found.append(p)
    return [p for p in found if _usable(p)]


def _registry_candidates(s: Slicer) -> list[str]:
    if sys.platform != "win32":
        return []
    import winreg

    out: list[str] = []
    hives = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    for hive in hives:
        for exe in s.exe_names:
            try:
                with winreg.OpenKey(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}") as k:
                    out.append(str(winreg.QueryValueEx(k, "")[0]).strip('"'))
            except OSError:
                pass

    name_re = re.compile(s.display_name, re.I)
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hive, path in roots:
        try:
            root = winreg.OpenKey(hive, path)
        except OSError:
            continue
        with root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, sub) as k:
                        try:
                            name = str(winreg.QueryValueEx(k, "DisplayName")[0])
                        except OSError:
                            continue
                        if not name_re.search(name):
                            continue
                        for value in ("DisplayIcon", "InstallLocation"):
                            try:
                                v = str(winreg.QueryValueEx(k, value)[0])
                            except OSError:
                                continue
                            v = v.split(",")[0].strip().strip('"')
                            if v.lower().endswith(".exe") and _usable(v):
                                out.append(v)
                            else:
                                out.extend(_exe_in_folder(s, v if os.path.isdir(v) else os.path.dirname(v)))
                except OSError:
                    continue
    return out


def _folder_candidates(s: Slicer) -> list[str]:
    if sys.platform != "win32":
        return []
    out = []
    bases = [os.environ.get(v) for v in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "LOCALAPPDATA")]
    for b in filter(None, bases):
        for pat in s.folders:
            for folder in glob.glob(os.path.join(b, pat)):
                out.extend(_exe_in_folder(s, folder))
    return out


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _linux_search_dirs() -> list[str]:
    home = os.path.expanduser("~")
    dirs = [os.path.join(home, d) for d in
            ("Applications", "applications", "Apps", "AppImages", "AppImage", ".local/bin", "bin",
             "Downloads", "Desktop")]
    dirs += ["/opt", "/usr/local/bin", "/snap/bin",
             "/var/lib/flatpak/exports/bin",
             os.path.join(home, ".local/share/flatpak/exports/bin")]
    return dirs


def _linux_matches(s: Slicer, filename: str) -> bool:
    n = _norm(filename)
    if any(_norm(x) in n for x in _EXCLUDE):
        return False
    return any(m in n for m in s.linux_match)


def _linux_candidates(s: Slicer, search_dirs: Optional[list[str]] = None) -> list[str]:
    """AppImages, Flatpak/Snap launchers and /opt installs whose name matches the slicer."""
    if sys.platform != "linux" and search_dirs is None:
        return []
    out = []
    for d in (search_dirs if search_dirs is not None else _linux_search_dirs()):
        try:
            entries = os.listdir(d)
        except OSError:
            continue
        for name in entries:
            p = os.path.join(d, name)
            if not _linux_matches(s, name):
                continue
            if os.path.isdir(p):
                # e.g. /opt/OrcaSlicer/orca-slicer or /opt/CrealityPrint/AppRun
                for sub in list(s.linux_bins) + ["AppRun", "bin/" + (s.linux_bins[0] if s.linux_bins else "")]:
                    q = os.path.join(p, sub)
                    if os.path.isfile(q) and os.access(q, os.X_OK):
                        out.append(q)
                        break
            elif os.access(p, os.X_OK) and (name.lower().endswith(".appimage")
                                             or "flatpak" in d or d.startswith("/snap")
                                             or d.endswith("bin")):
                out.append(p)
    return out


def _desktop_dirs() -> list[str]:
    home = os.path.expanduser("~")
    data = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":")
    return [os.path.join(home, ".local/share/applications")] + [os.path.join(d, "applications") for d in data]


def _desktop_candidates(s: Slicer, dirs: Optional[list[str]] = None) -> list[str]:
    """Programs started by .desktop menu entries (distribution packages, AppImage integrations)."""
    if sys.platform != "linux" and dirs is None:
        return []
    out = []
    for d in (dirs if dirs is not None else _desktop_dirs()):
        try:
            names = [n for n in os.listdir(d) if n.endswith(".desktop")]
        except OSError:
            continue
        for n in names:
            try:
                with open(os.path.join(d, n), encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            title = re.search(r"^Name=(.+)$", text, re.M)
            if not (_linux_matches(s, n) or (title and _linux_matches(s, title.group(1)))):
                continue
            m = re.search(r"^Exec=(.+)$", text, re.M)
            if not m:
                continue
            first = m.group(1).strip()
            exe = first[1:first.index('"', 1)] if first.startswith('"') else first.split()[0]
            if os.path.basename(exe) in ("flatpak", "env", "snap"):
                continue                        # handled by the Flatpak/Snap scan
            exe = exe if os.path.isabs(exe) else (shutil.which(exe) or "")
            if exe and os.path.isfile(exe) and os.access(exe, os.X_OK):
                out.append(exe)
    return out


def _path_candidates(s: Slicer) -> list[str]:
    out = []
    names = [n for exe in s.exe_names for n in (exe, os.path.splitext(exe)[0])]
    names += list(s.linux_bins)
    for name in names:
        p = shutil.which(name)
        if p:
            out.append(p)
    return out


def _is_mac_app(p: str) -> bool:
    return sys.platform == "darwin" and p.endswith(".app") and os.path.isdir(p)


def _mac_candidates(s: "Slicer", dirs: Optional[list] = None) -> list[str]:
    """macOS: apps are folders like /Applications/OrcaSlicer.app; match on the name
    without spaces ("Bambu Studio" finds BambuStudio.app and "Bambu Studio.app")."""
    if sys.platform != "darwin" and dirs is None:
        return []
    dirs = dirs if dirs is not None else ["/Applications", os.path.expanduser("~/Applications")]
    key = s.name.lower().replace(" ", "")
    out = []
    for d in dirs:
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        out += [os.path.join(d, n) for n in names
                if n.lower().endswith(".app") and key in n.lower().replace(" ", "")]
    return out


def find_slicer(slicer_id: str, manual_path: str = "") -> Optional[str]:
    """Full path of a known slicer, or None if it is not installed."""
    if manual_path and (os.path.isfile(manual_path) or _is_mac_app(manual_path)):
        return manual_path
    s = BY_ID.get(slicer_id)
    if s is None:
        return None
    seen, cands = set(), []
    for p in (_registry_candidates(s) + _folder_candidates(s) + _linux_candidates(s) + _desktop_candidates(s)
              + _mac_candidates(s) + _path_candidates(s)):
        key = os.path.normcase(os.path.abspath(p))
        if key not in seen and (os.path.isfile(p) or _is_mac_app(p)):
            seen.add(key)
            cands.append(p)
    if not cands:
        return None
    cands.sort(key=_version_key, reverse=True)
    return cands[0]


def detect_installed(manual_paths: Optional[dict] = None) -> dict[str, str]:
    """{slicer_id: exe path} for every known slicer that is installed."""
    manual_paths = manual_paths or {}
    found = {}
    for s in SLICERS:
        p = find_slicer(s.id, manual_paths.get(s.id, ""))
        if p:
            found[s.id] = p
    return found


def program_file_filter() -> str:
    """File-dialog filter for choosing a slicer program on this OS."""
    if sys.platform == "win32":
        return "Programs (*.exe);;All files (*)"
    if sys.platform == "linux":
        return "Programs and AppImages (*);;AppImages (*.AppImage *.appimage)"
    return "Applications (*.app);;All files (*)"


# --------------------------------------------------------------------------
# Settings helpers
# --------------------------------------------------------------------------
def migrate_settings(settings) -> None:
    """Move the single 'slicer_path' of v0.1/v0.2 into the per-slicer paths."""
    old = settings.get("slicer_path", "")
    if old:
        paths = dict(settings.get("slicer_paths") or {})
        paths.setdefault("creality_print", old)
        settings.set("slicer_paths", paths)
        settings.set("slicer_path", "")
        if not settings.get("slicer_id"):
            settings.set("slicer_id", "creality_print")


def resolve(settings, slicer_id: Optional[str] = None,
            installed: Optional[dict] = None) -> tuple[str, str, Optional[str]]:
    """Which slicer to use: (id, display name, exe path or None).

    slicer_id None = the default from Settings. If no default was chosen yet,
    the first installed slicer (in SLICERS order) is used.
    """
    paths = settings.get("slicer_paths") or {}
    custom = settings.get("custom_slicer") or {}
    sid = slicer_id or settings.get("slicer_id", "")

    if sid == CUSTOM:
        p = custom.get("path", "")
        return CUSTOM, slicer_name(CUSTOM, custom.get("name", "")), (p if os.path.isfile(p) else None)
    if sid in BY_ID:
        return sid, BY_ID[sid].name, find_slicer(sid, paths.get(sid, ""))

    # Nothing chosen yet: first slicer that is installed.
    installed = installed if installed is not None else detect_installed(paths)
    for s in SLICERS:
        if s.id in installed:
            return s.id, s.name, installed[s.id]
    return "", "slicer", None


# --------------------------------------------------------------------------
# Launch
# --------------------------------------------------------------------------
def clean_environment(env: Optional[dict] = None) -> dict:
    """Environment for starting another program from the packaged PrintView3D.

    PyInstaller and AppImage point library and plugin search paths at our own
    bundled copies of Qt, Python and friends. A slicer started with those
    settings can load the wrong libraries and crash, so restore the user's
    original values and drop the variables that only make sense for us.
    """
    env = dict(os.environ if env is None else env)
    for var in ("LD_LIBRARY_PATH", "PATH"):
        orig = env.pop(var + "_ORIG", None)        # PyInstaller saves the original here
        if orig is not None:
            env[var] = orig
        elif var == "LD_LIBRARY_PATH" and getattr(sys, "frozen", False):
            env.pop(var, None)
    # Variables that point into our own bundle (PyInstaller temp dir / AppImage mount)
    ours = [p for p in (getattr(sys, "_MEIPASS", ""), env.get("APPDIR", "")) if p]
    for var in list(env):
        if var in ("LD_LIBRARY_PATH", "PATH"):
            continue
        if ours and any(p in env[var] for p in ours):
            env.pop(var)
    for var in ("APPIMAGE", "APPDIR", "ARGV0", "OWD", "QT_API"):
        env.pop(var, None)
    if env.pop("PRINTVIEW3D_SET_QPA", None):
        env.pop("QT_QPA_PLATFORM", None)
    return env


def launch_command(slicer_exe: str, file_path=None) -> list[str]:
    """file_path: one file, a list of files (all opened together, e.g. the models of a ZIP;
    slicers put them on one plate) or None."""
    args = [slicer_exe]
    if sys.platform == "darwin" and slicer_exe.endswith(".app"):
        args = ["open", "-a", slicer_exe]          # macOS app bundles
    files = [file_path] if isinstance(file_path, str) else list(file_path or [])
    args.extend(os.path.abspath(f) for f in files if f)
    return args


def open_in_slicer(slicer_exe: str, file_path=None) -> None:
    """Start the slicer (detached), optionally opening one file or several files in it."""
    args = launch_command(slicer_exe, file_path)
    kwargs = {"cwd": os.path.dirname(slicer_exe) or None, "close_fds": True, "env": clean_environment()}
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, **kwargs)

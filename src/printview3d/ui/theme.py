"""Colour themes: Automatic (follows the system), Dark, Gray, Graphite, Light, Ember Light and
Ember Dark.

A theme sets the colours of the window (Qt palette + style sheet) and of the
3D view (background, build plate, grid). Each theme also has its own accent colours: the teal
of the classic themes, or the warm orange + teal pair of the Ember themes (primary = the slicer
button, OK buttons and the selected Settings page; accent = toolbar tiles, sliders, focus). The colours of G-code features and
models never change, so they always mean the same thing as in the slicer;
the 3D backgrounds are chosen so every feature colour stays visible.

Switching is immediate: apply_theme() restyles every window, and the main
window recolours the 3D view (MainWindow.apply_theme).
"""

from __future__ import annotations

import math
import os
import subprocess
import sys

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QGuiApplication, QIcon, QLinearGradient, QPainter, QPainterPath, QPalette,
                           QPen, QPixmap, QPolygonF)

from ..i18n import tr_noop

# The classic teal. Every theme has its own "accent"/"primary" keys; these stay for older callers.
ACCENT = "#2fa4a0"
ACCENT_HOVER = "#38bbb6"

# Setting value -> name shown in Settings.
THEME_NAMES = {
    "auto": tr_noop("Automatic (system theme)"),
    "dark": tr_noop("Dark"),
    "gray": tr_noop("Gray"),
    "graphite": tr_noop("Graphite"),
    "light": tr_noop("Light"),
    "ember": tr_noop("Ember Light"),
    "ember_dark": tr_noop("Ember Dark"),
}
# Order used by Ctrl+T (next theme).
CYCLE = ["dark", "gray", "graphite", "light", "ember", "ember_dark"]
# Themes with a light window; every other theme is dark (title bar, Mica, icon contrast).
LIGHT_THEMES = {"light", "ember"}

# Accent keys of the classic themes (all the same teal, so nothing changes for them).
# accent_ink / primary_ink: the symbol colour on a soft accent / primary tile.
# selected_bg / selected_text: the chosen page in the Settings sidebar.
def _classic(ink: str, selected: str, text: str) -> dict[str, str]:
    return {"accent": ACCENT, "accent_hover": ACCENT_HOVER, "accent_ink": ink,
            "primary": ACCENT, "primary_hover": ACCENT_HOVER, "primary_ink": ink,
            "selected_bg": selected, "selected_text": text}


THEMES: dict[str, dict[str, str]] = {
    "dark": {
        # window
        "window": "#1f2328", "base": "#171a1e", "alt": "#23272d", "text": "#e6e8eb",
        "button": "#2a2f36", "button_hover": "#353c46", "button_border": "#3a414b",
        "tool_hover": "#2d333b", "tool_checked": "#343b45",
        "bar": "#1a1d21", "bar_border": "#2d323a", "border": "#2f343c",
        "muted": "#9aa1aa", "group_title": "#aab1ba", "disabled": "#6b727b",
        "placeholder": "#8a919a", "tooltip": "#2b3038",
        "groove": "#2d333b", "handle": "#e6e8eb", "handle_border": "#e6e8eb",
        "link": "#7cc7c4", "thumb": "#15181c",
        # 3D view
        "bg_bottom": "#16191d", "bg_top": "#2a2f37", "plate": "#22262c",
        "grid_minor": "#363b43", "grid_major": "#535a64", "plate_edge": "#7a828d",
        "axes_label": "#e6e8eb",
        **_classic("#2fa4a0", "#343b45", "#e6e8eb"),
    },
    "gray": {
        "window": "#3b3e43", "base": "#33363a", "alt": "#404349", "text": "#eef0f2",
        "button": "#4a4e54", "button_hover": "#555a61", "button_border": "#5d626a",
        "tool_hover": "#4b4f56", "tool_checked": "#575c64",
        "bar": "#35383c", "bar_border": "#4a4e55", "border": "#52575e",
        "muted": "#b4b9bf", "group_title": "#c3c8cd", "disabled": "#80868d",
        "placeholder": "#a2a7ad", "tooltip": "#4a4e54",
        "groove": "#4f545b", "handle": "#eef0f2", "handle_border": "#eef0f2",
        "link": "#8fd6d2", "thumb": "#2f3236",
        "bg_bottom": "#45494f", "bg_top": "#6c727a", "plate": "#4f545a",
        "grid_minor": "#5f646b", "grid_major": "#7b8189", "plate_edge": "#a6acb3",
        "axes_label": "#eef0f2",
        **_classic("#2fa4a0", "#575c64", "#eef0f2"),
    },
    # Warm, dark coffee-brown charcoal: soft on the eyes in the evening.
    "graphite": {
        "window": "#2b2622", "base": "#231f1c", "alt": "#312b27", "text": "#ece6df",
        "button": "#3a332e", "button_hover": "#463e37", "button_border": "#5a4e44",
        "tool_hover": "#3d3530", "tool_checked": "#4a4039",
        "bar": "#26211e", "bar_border": "#3a332d", "border": "#40372f",
        "muted": "#b3a89c", "group_title": "#c2b6a9", "disabled": "#7d7268",
        "placeholder": "#9e9387", "tooltip": "#3a332e",
        "groove": "#40372f", "handle": "#ece6df", "handle_border": "#ece6df",
        "link": "#8fd6d2", "thumb": "#201c19",
        "bg_bottom": "#28221e", "bg_top": "#4d433b", "plate": "#3a322c",
        "grid_minor": "#4a4038", "grid_major": "#685b50", "plate_edge": "#9a8b7d",
        "axes_label": "#ece6df",
        **_classic("#2fa4a0", "#4a4039", "#ece6df"),
    },
    "light": {
        "window": "#f3f4f6", "base": "#ffffff", "alt": "#f0f1f3", "text": "#1f2328",
        "button": "#e8eaed", "button_hover": "#dde0e4", "button_border": "#c9cdd3",
        "tool_hover": "#e1e4e8", "tool_checked": "#d3d8de",
        "bar": "#e9ebee", "bar_border": "#d0d4d9", "border": "#d0d4d9",
        "muted": "#5d646d", "group_title": "#4a5059", "disabled": "#a0a6ad",
        "placeholder": "#868d96", "tooltip": "#ffffff",
        "groove": "#d0d4d9", "handle": "#ffffff", "handle_border": "#9aa1aa",
        "link": "#1f7f7b", "thumb": "#c4cad1",
        # Light-gray rather than white, so white and yellow toolpaths stay visible.
        "bg_bottom": "#c9ced5", "bg_top": "#eceef1", "plate": "#b3bac3",
        "grid_minor": "#a3abb5", "grid_major": "#858e99", "plate_edge": "#5b6470",
        "axes_label": "#1f2328",
        **_classic("#1f7f7b", "#d3d8de", "#1f2328"),
    },
    # Warm cream paper with a bright orange and a lagoon teal: the slicer button, OK and the
    # chosen Settings page are orange; toolbar tiles, sliders and focus are teal. Text is a
    # soft slate instead of black. The 3D view is a deeper sand, so white and yellow toolpaths
    # stay visible.
    "ember": {
        "window": "#edebe4", "base": "#fbfaf7", "alt": "#f3f1eb", "text": "#484d52",
        "button": "#f7f5f0", "button_hover": "#ffffff", "button_border": "#d3cdbe",
        "tool_hover": "#e4decb", "tool_checked": "#dcd5bf",
        "bar": "#e4decb", "bar_border": "#d3cdbe", "border": "#d3cdbe",
        "muted": "#6e6a62", "group_title": "#5a5f64", "disabled": "#aba597",
        "placeholder": "#8e897f", "tooltip": "#fbfaf7",
        "groove": "#d3cdbe", "handle": "#ffffff", "handle_border": "#a69f90",
        "link": "#14736a", "thumb": "#ddd7c6",
        "bg_bottom": "#cdc6b3", "bg_top": "#edebe4", "plate": "#b9b19c",
        "grid_minor": "#a9a08a", "grid_major": "#8c8370", "plate_edge": "#5e574a",
        "axes_label": "#484d52",
        "accent": "#2cc1b2", "accent_hover": "#4fd0c3", "accent_ink": "#14736a",
        "primary": "#ef791b", "primary_hover": "#f48f3e", "primary_ink": "#c9600f",
        "selected_bg": "#ef791b", "selected_text": "#ffffff",
    },
    # The same orange + teal at night: deep lagoon greens instead of grey, teal-lit build plate.
    "ember_dark": {
        "window": "#1a2221", "base": "#141b1a", "alt": "#1f2928", "text": "#e9e6df",
        "button": "#22302e", "button_hover": "#2b3b39", "button_border": "#34514d",
        "tool_hover": "#233230", "tool_checked": "#2a3d3a",
        "bar": "#151c1b", "bar_border": "#263331", "border": "#2b3836",
        "muted": "#9daaa7", "group_title": "#b3bebb", "disabled": "#5f6d6a",
        "placeholder": "#7f8d8a", "tooltip": "#22302e",
        "groove": "#2b3836", "handle": "#e9e6df", "handle_border": "#e9e6df",
        "link": "#5fd6ca", "thumb": "#111716",
        "bg_bottom": "#121817", "bg_top": "#25312f", "plate": "#1e2826",
        "grid_minor": "#2e3b39", "grid_major": "#46605b", "plate_edge": "#6fa8a0",
        "axes_label": "#e9e6df",
        "accent": "#2cc1b2", "accent_hover": "#4fd0c3", "accent_ink": "#2cc1b2",
        "primary": "#ef791b", "primary_hover": "#f48f3e", "primary_ink": "#f48f3e",
        "selected_bg": "#ef791b", "selected_text": "#ffffff",
    },
}

_setting = "auto"
_current = "dark"


def system_theme() -> str:
    """'dark' or 'light' from the operating system (Windows, GNOME, KDE, macOS)."""
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light"
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
    except AttributeError:          # Qt older than 6.5
        pass
    if sys.platform.startswith("linux"):
        # Qt couldn't tell (desktops without a colour-scheme portal, bare X servers). Ask the
        # desktop's own settings; if nothing says dark, use light, as Linux desktops do.
        return "dark" if _linux_prefers_dark() else "light"
    return "dark"                   # unknown on Windows/macOS: keep the classic look


def _linux_prefers_dark(env=None, home=None, run=None) -> bool:
    """True if the Linux desktop is set to a dark style (GNOME, GTK, KDE settings)."""
    env = os.environ if env is None else env
    home = home or os.path.expanduser("~")
    gtk_theme = env.get("GTK_THEME", "").lower()
    if gtk_theme:
        return "dark" in gtk_theme
    if run is None:
        run = _run_gsettings
    scheme = run("color-scheme")                    # GNOME 42+: 'prefer-dark', 'prefer-light', 'default'
    if scheme:
        if "dark" in scheme:
            return True
        if "light" in scheme:
            return False
    name = run("gtk-theme")                         # e.g. 'Adwaita-dark'
    if name and "dark" in name.lower():
        return True
    config = env.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    for path, keys in ((os.path.join(config, "gtk-3.0", "settings.ini"),
                        ("gtk-application-prefer-dark-theme", "gtk-theme-name")),
                       (os.path.join(config, "kdeglobals"), ("colorscheme", "lookandfeelpackage"))):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    key, _, value = line.partition("=")
                    key, value = key.strip().lower(), value.strip().lower()
                    if key == "gtk-application-prefer-dark-theme" and value in ("1", "true"):
                        return True
                    if key in keys and key != "gtk-application-prefer-dark-theme" and "dark" in value:
                        return True
        except OSError:
            pass
    return False


def _run_gsettings(key: str) -> str:
    """One GNOME interface setting, or "" (no gsettings, no GNOME, or too slow)."""
    try:
        from ..slicer import clean_environment     # the system's own libraries, not our bundle's
        out = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", key],
                             capture_output=True, text=True, timeout=2, env=clean_environment())
        return out.stdout.strip().strip("'") if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError, ValueError):
        return ""


def resolve(setting: str) -> str:
    if setting in THEMES:
        return setting
    return system_theme()


def current() -> str:
    """The theme in use ('dark', 'gray', 'graphite', 'light', 'ember' or 'ember_dark')."""
    return _current


def setting() -> str:
    return _setting


def colors(name: str | None = None) -> dict[str, str]:
    return THEMES[name or _current]


# Windows 11 Mica (Settings -> Appearance): the main window's own backgrounds become transparent,
# so the backdrop Windows draws behind the window shows through (see win_mica.py). The 3D view is a
# separate OpenGL surface and stays solid anyway.
# Every rule names one of the main window's own parts by its object name. A rule such as
# "QMainWindow#mainWindow QScrollArea" would also reach dialogs - a dialog opened from the main
# window is its child - and made the Settings window black in 0.15.0.
MICA_CSS = """
    QMainWindow#mainWindow,
    QStackedWidget#centralStack,
    QStackedWidget#centralStack QStackedWidget,
    QStackedWidget#centralStack QSplitter,
    QStackedWidget#centralStack QScrollArea,
    QStackedWidget#centralStack QScrollArea > QWidget {{ background: transparent; }}
    /* A frosted layer of the theme colour over the glass, so text stays readable on any
       wallpaper (strongest in the light theme, where the glass is bright). */
    QToolBar#mainToolbar {{ background: {bar}; border-bottom: 1px solid {border}; }}
    QStatusBar#mainStatusBar {{ background: {bar}; }}
    QStackedWidget#centralStack QScrollArea > QWidget > QWidget {{ background: {panel}; }}
    QStackedWidget#centralStack QGroupBox {{ background: {box}; }}
    QStackedWidget#centralStack QGroupBox::title {{ color: {title}; }}
    QStackedWidget#centralStack QLabel#muted, QStackedWidget#centralStack QLabel#formKey {{ color: {muted}; }}
"""

# How strong the frosted layer is: (toolbar/status bar, side panel, boxes in the side panel)
_GLASS = {"light": (0.62, 0.72, 0.80), "dark": (0.35, 0.45, 0.40)}


def is_dark(name: str | None = None) -> bool:
    return (name or _current) not in LIGHT_THEMES


def apply_theme(app, choice: str = "auto", mica: bool = False) -> str:
    """Style the whole application. Returns the theme used."""
    global _setting, _current
    _setting = choice if choice in THEME_NAMES else "auto"
    hints = QGuiApplication.styleHints()
    if _setting == "auto" and hasattr(hints, "unsetColorScheme"):
        hints.unsetColorScheme()            # back to the system's own dark/light before asking it
    _current = resolve(_setting)
    _tell_qt_light_or_dark(hints)
    t = THEMES[_current]
    app.setStyle("Fusion")
    pal = QPalette()
    c = QColor
    pal.setColor(QPalette.Window, c(t["window"]))
    pal.setColor(QPalette.WindowText, c(t["text"]))
    pal.setColor(QPalette.Base, c(t["base"]))
    pal.setColor(QPalette.AlternateBase, c(t["alt"]))
    pal.setColor(QPalette.ToolTipBase, c(t["tooltip"]))
    pal.setColor(QPalette.ToolTipText, c(t["text"]))
    pal.setColor(QPalette.Text, c(t["text"]))
    pal.setColor(QPalette.Button, c(t["button"]))
    pal.setColor(QPalette.ButtonText, c(t["text"]))
    pal.setColor(QPalette.BrightText, c("#ffffff"))
    pal.setColor(QPalette.Highlight, c(t["primary"]))
    pal.setColor(QPalette.HighlightedText, c("#ffffff"))
    pal.setColor(QPalette.Link, c(t["link"]))
    pal.setColor(QPalette.PlaceholderText, c(t["placeholder"]))
    # Fusion draws frames/shadows from these.
    pal.setColor(QPalette.Light, c(t["button_hover"]))
    pal.setColor(QPalette.Midlight, c(t["button"]))
    pal.setColor(QPalette.Mid, c(t["border"]))
    pal.setColor(QPalette.Dark, c(t["bar_border"]))
    pal.setColor(QPalette.Shadow, c("#000000" if is_dark() else "#9aa1aa"))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, c(t["disabled"]))
    app.setPalette(pal)
    accent, accent_hover = t["accent"], t["accent_hover"]
    primary, primary_hover = t["primary"], t["primary_hover"]
    app.setStyleSheet(f"""
        QToolBar {{ background: {t['bar']}; border: none; border-bottom: 1px solid {t['bar_border']}; spacing: 4px; padding: 4px; }}
        QToolButton {{ padding: 5px 9px; border-radius: 5px; color: {t['text']}; }}
        QToolButton:hover {{ background: {t['tool_hover']}; }}
        QToolButton:checked {{ background: {t['tool_checked']}; }}
        QToolBar QToolButton {{ border: 1px solid {t['button_border']}; background: {t['button']};
            padding: 4px 10px; margin: 1px 2px; font-weight: 600; }}
        QToolBar QToolButton:hover {{ background: {t['button_hover']}; border-color: {t['muted']}; }}
        QToolBar QToolButton:checked {{ background: {t['tool_checked']}; border-color: {accent}; }}
        QToolBar QToolButton#iconButton {{ padding: 2px 3px; }}
        QToolBar QToolButton#iconButton::menu-indicator {{ image: none; width: 0; }}
        QToolBar QToolButton#exportButton {{ padding: 2px 10px 2px 3px; }}
        QToolBar QToolButton#exportButton[popupMode="1"] {{ padding-right: 26px; }}
        QToolBar QToolButton#exportButton::menu-button {{ width: 20px; border-left: 1px solid {t['button_border']};
            border-top-right-radius: 5px; border-bottom-right-radius: 5px; }}
        QToolButton#slicerButton {{ background: {primary}; color: white; font-weight: 600; padding: 2px 14px 2px 3px; }}
        QToolButton#slicerButton:hover {{ background: {primary_hover}; }}
        QToolButton#slicerButton[popupMode="1"] {{ padding-right: 28px; }}
        QToolButton#slicerButton::menu-button {{ width: 22px; border-left: 1px solid rgba(255,255,255,0.35);
            border-top-right-radius: 5px; border-bottom-right-radius: 5px; }}
        QGroupBox {{ border: 1px solid {t['border']}; border-radius: 6px; margin-top: 14px; padding: 8px 8px 6px 8px; font-weight: 600; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {t['group_title']}; }}
        QLabel#fileName {{ font-size: 15px; font-weight: 600; }}
        QLabel#muted, QLabel#formKey {{ color: {t['muted']}; }}
        QLabel#thumbnail {{ background: {t['thumb']}; border-radius: 6px; padding: 6px; }}
        QPushButton {{ padding: 5px 12px; border-radius: 5px; background: {t['button']}; border: 1px solid {t['button_border']}; }}
        QPushButton:hover {{ background: {t['button_hover']}; }}
        QPushButton#primary {{ background: {primary}; border: none; color: white; font-weight: 600; }}
        QPushButton#primary:hover {{ background: {primary_hover}; }}
        QPushButton#link {{ color: {t['link']}; border: none; background: transparent; }}
        QPushButton#link:hover {{ text-decoration: underline; }}
        QScrollArea {{ border: none; }}
        QSlider::groove:horizontal {{ height: 6px; background: {t['groove']}; border-radius: 3px; }}
        QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {t['handle']}; border: 1px solid {t['handle_border']};
            width: 14px; margin: -6px 0; border-radius: 8px; }}
        QStatusBar {{ background: {t['bar']}; color: {t['group_title']}; }}
        QListWidget {{ border: 1px solid {t['border']}; border-radius: 6px; }}
        QListWidget#zipList {{ background: {t['base']}; outline: none; }}
        QListWidget#zipList::item {{ border-radius: 4px; }}
        QListWidget#zipList::item:hover {{ background: {t['tool_hover']}; }}
        QListWidget#zipList::item:selected {{ background: {t['tool_checked']}; border-left: 3px solid {accent}; }}
        QListWidget#settingsNav {{ background: {t['bar']}; border-radius: 8px; padding: 6px; outline: none; }}
        QListWidget#settingsNav::item {{ padding: 0px 6px; border-radius: 6px; color: {t['text']}; }}
        QListWidget#settingsNav::item:hover {{ background: {t['tool_hover']}; }}
        QListWidget#settingsNav::item:selected {{ background: {t['selected_bg']}; color: {t['selected_text']}; }}
        QLabel#pageTitle {{ font-size: 18px; font-weight: 600; padding-bottom: 4px; }}
        QLabel#keyCap {{
            background: {t['button']}; border: 1px solid {t['button_border']};
            border-bottom-width: 2px; border-radius: 4px; padding: 1px 7px; font-weight: 400;
        }}
        QLabel#versionBadge {{
            color: {t['muted']}; background: {t['button']};
            border: 1px solid {t['button_border']}; border-radius: 4px;
            padding: 1px 8px; margin: 2px 4px;
        }}
        QLabel#versionBadge:hover {{ background: {t['button_hover']}; }}
        QToolButton#themeCard {{
            background: {t['base']}; border: 2px solid {t['border']}; border-radius: 10px;
            padding: 8px 6px 6px 6px; color: {t['text']}; font-weight: 600;
        }}
        QToolButton#themeCard:hover {{ border-color: {accent}; }}
        QToolButton#themeCard:checked {{ border: 3px solid {primary}; background: {t['tool_hover']}; }}
    """ + (_mica_css(t, _current) if mica else ""))
    return _current


def _tell_qt_light_or_dark(hints) -> None:
    """Tell Qt (6.8+) whether our theme is light or dark. On Windows Qt then draws the title bar
    and the Mica/Acrylic backdrop in the same variant. Without this, Qt follows Windows' own dark
    mode and overrides ours: with Windows in dark mode, our light theme kept a dark title bar
    and a dark backdrop behind dark text (seen on Sevag's PC in 0.15.2 and 0.16.0)."""
    if _setting == "auto" or not hasattr(hints, "setColorScheme"):
        return
    try:
        hints.setColorScheme(Qt.ColorScheme.Dark if is_dark() else Qt.ColorScheme.Light)
    except Exception:  # noqa: BLE001 - a platform without this keeps the system's choice
        pass


def _mica_css(t: dict, name: str) -> str:
    light = not is_dark(name)
    bar, panel, box = _GLASS["light" if light else "dark"]
    return MICA_CSS.format(
        bar=_rgba(t["bar"], bar), border=_rgba(t["bar_border"], 0.6),
        panel=_rgba(t["window"], panel), box=_rgba(t["base"] if light else t["window"], box),
        # On glass the light theme's grey labels need a little more contrast.
        title="#2f343b" if light else t["group_title"],
        muted="#454b53" if light else t["muted"])


def _rgba(hex_color: str, alpha: float) -> str:
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


def next_theme(name: str) -> str:
    """The theme after `name` for Ctrl+T."""
    i = CYCLE.index(name) if name in CYCLE else -1
    return CYCLE[(i + 1) % len(CYCLE)]


def theme_icon(name: str | None = None) -> QIcon:
    """Half-filled circle (the usual 'theme' symbol) in the theme's text colour."""
    size = 64                       # drawn large, Qt scales it down sharply
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    fg = QColor(colors(name)["text"])
    p.setPen(QPen(fg, 5))
    c, r = QPointF(size / 2, size / 2), 24
    p.drawEllipse(c, r, r)
    half = QPainterPath()
    half.moveTo(c)
    half.arcTo(QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r), 90, 180)
    p.fillPath(half, fg)
    p.end()
    return QIcon(pm)


def theme_preview(name: str, width: int = 168, height: int = 104, ratio: float = 2.0) -> QPixmap:
    """A small picture of PrintView3D in a theme: toolbar with its tiles and slicer button,
    the side panel with a chosen row, and the 3D view with plate and model. Used by the theme
    cards in Settings and the toolbar's theme menu. 'auto' shows Dark and Light split diagonally.
    Drawn at `ratio` x the size, so it stays sharp on high-DPI screens."""
    pm = QPixmap(round(width * ratio), round(height * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    frame = QPainterPath()
    frame.addRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), 7, 7)
    p.setClipPath(frame)
    if name in THEMES:
        _draw_preview(p, THEMES[name], name, width, height)
    else:                                             # Automatic: dark top-left, light bottom-right
        _draw_preview(p, THEMES["dark"], "dark", width, height)
        half = QPainterPath()
        half.moveTo(width * 0.62, 0)
        half.lineTo(width, 0)
        half.lineTo(width, height)
        half.lineTo(width * 0.38, height)
        half.closeSubpath()
        p.setClipPath(frame.intersected(half))
        _draw_preview(p, THEMES["light"], "light", width, height)
        p.setClipPath(frame)
    p.setClipping(False)
    p.setPen(QPen(QColor(0, 0, 0, 40), 1))
    p.setBrush(Qt.NoBrush)
    p.drawPath(frame)
    p.end()
    return pm


def _draw_preview(p: QPainter, t: dict, name: str, w: float, h: float) -> None:
    dark = is_dark(name)
    p.setPen(Qt.NoPen)
    p.fillRect(QRectF(0, 0, w, h), QColor(t["window"]))
    # toolbar: three accent tiles, the slicer button, one primary tile
    bar_h = h * 0.2
    p.fillRect(QRectF(0, 0, w, bar_h), QColor(t["bar"]))
    p.fillRect(QRectF(0, bar_h - 1, w, 1), QColor(t["bar_border"]))
    tile = bar_h * 0.56
    y = (bar_h - tile) / 2
    for i in range(3):
        c = QColor(t["accent"])
        c.setAlphaF(0.30 if dark else 0.34)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(6 + i * (tile + 3), y, tile, tile), 2.5, 2.5)
        p.setBrush(QColor(t["accent_ink"]))
        p.drawEllipse(QPointF(6 + i * (tile + 3) + tile / 2, y + tile / 2), tile * 0.17, tile * 0.17)
    p.setBrush(QColor(t["primary"]))
    p.drawRoundedRect(QRectF(w * 0.5, y, w * 0.3, tile), 3, 3)
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(w * 0.5 + 5, y + tile * 0.38, w * 0.3 - 10, tile * 0.24), 1, 1)
    c = QColor(t["primary"])
    c.setAlphaF(0.28)
    p.setBrush(c)
    p.drawRoundedRect(QRectF(w - 6 - tile, y, tile, tile), 2.5, 2.5)
    # side panel: a chosen row and some text
    side_w = w * 0.27
    p.fillRect(QRectF(0, bar_h, side_w, h - bar_h), QColor(t["window"]))
    p.setBrush(QColor(t["selected_bg"]))
    p.drawRoundedRect(QRectF(4, bar_h + 6, side_w - 8, 9), 2.5, 2.5)
    p.setBrush(QColor(t["selected_text"]))
    p.drawRoundedRect(QRectF(8, bar_h + 9.5, side_w * 0.5, 2), 1, 1)
    txt = QColor(t["text"])
    txt.setAlphaF(0.55)
    p.setBrush(txt)
    for i, f in enumerate((0.62, 0.45, 0.7, 0.5)):
        p.drawRoundedRect(QRectF(8, bar_h + 22 + i * 9, (side_w - 12) * f, 2.2), 1, 1)
    # 3D view: background gradient, plate, a small model
    view = QRectF(side_w, bar_h, w - side_w, h - bar_h)
    g = QLinearGradient(view.topLeft(), view.bottomLeft())
    g.setColorAt(0, QColor(t["bg_top"]))
    g.setColorAt(1, QColor(t["bg_bottom"]))
    p.fillRect(view, g)
    cx, cy = view.center().x(), view.top() + view.height() * 0.66
    pw, ph = view.width() * 0.4, view.height() * 0.22
    plate = QPolygonF([QPointF(cx - pw, cy), QPointF(cx, cy - ph), QPointF(cx + pw, cy), QPointF(cx, cy + ph)])
    p.setBrush(QColor(t["plate"]))
    p.setPen(QPen(QColor(t["plate_edge"]), 0.8))
    p.drawPolygon(plate)
    p.setPen(QPen(QColor(t["grid_major"]), 0.6))
    left, top, right, bottom = (plate[i] for i in range(4))
    for f in (0.25, 0.5, 0.75):
        p.drawLine(left + (bottom - left) * f, top + (right - top) * f)
        p.drawLine(left + (top - left) * f, bottom + (right - bottom) * f)
    base = QColor(PREVIEW_MODEL)
    s = view.height() * 0.2
    top_y = cy - s * 1.25
    p.setPen(Qt.NoPen)
    faces = (
        ([QPointF(cx - s, top_y), QPointF(cx, top_y - s * 0.5), QPointF(cx + s, top_y), QPointF(cx, top_y + s * 0.5)], 125),
        ([QPointF(cx - s, top_y), QPointF(cx, top_y + s * 0.5), QPointF(cx, top_y + s * 1.6), QPointF(cx - s, top_y + s * 1.1)], 100),
        ([QPointF(cx + s, top_y), QPointF(cx, top_y + s * 0.5), QPointF(cx, top_y + s * 1.6), QPointF(cx + s, top_y + s * 1.1)], 75),
    )
    for pts, shade in faces:
        p.setBrush(base.lighter(shade) if shade > 100 else base.darker(round(10000 / shade)) if shade < 100 else base)
        p.drawPolygon(QPolygonF(pts))


def theme_swatch(name: str) -> QIcon:
    """A round colour swatch for the theme menu: the window colour with the theme's primary
    colour in the lower right and an accent ring ('auto': Dark and Light halves)."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(6, 6, 52, 52)
    if name in THEMES:
        t = THEMES[name]
        first, second, ring = t["window"], t["primary"], t["accent"]
    else:
        first, second, ring = THEMES["dark"]["window"], THEMES["light"]["window"], "#8a919a"
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(first))
    p.drawEllipse(r)
    lower = QPainterPath()
    lower.moveTo(r.center())
    lower.arcTo(r, -135, 180)                        # lower-right half
    lower.closeSubpath()
    p.fillPath(lower, QColor(second))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(ring), 5))
    p.drawEllipse(r.adjusted(-2.5, -2.5, 2.5, 2.5))
    p.end()
    return QIcon(pm)


PREVIEW_MODEL = "#4aa3df"   # scene.MODEL_COLORS[0]: models keep their colour in every theme
UPDATE_DOT = "#e5484d"      # the red "update available" dot
UP_TO_DATE_DOT = "#30a46c"  # the green "up to date" dot


def nav_icon(kind: str, dot: bool = False) -> QIcon:
    """Line icons for the Settings sidebar, in the theme's text colour (sharp at any scale).
    With dot=True a red dot marks the icon (update available). The chosen page's icon is drawn
    in the colour of its text (white on the orange of the Ember themes)."""
    t = colors()
    icon = QIcon(_nav_pixmap(kind, dot, t["text"], t["bar"]))
    if t["selected_text"] != t["text"]:
        icon.addPixmap(_nav_pixmap(kind, dot, t["selected_text"], t["selected_bg"]), QIcon.Selected)
    return icon


def _nav_pixmap(kind: str, dot: bool, color: str, ring: str) -> QPixmap:
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    fg = QColor(color)
    pen = QPen(fg, 4.5)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    c = QPointF(32, 32)
    if kind == "language":                       # globe
        p.drawEllipse(c, 24, 24)
        p.drawEllipse(c, 10, 24)
        p.drawLine(QPointF(8, 32), QPointF(56, 32))
        p.drawLine(QPointF(13, 20), QPointF(51, 20))
        p.drawLine(QPointF(13, 44), QPointF(51, 44))
    elif kind == "appearance":                   # half circle, as on the toolbar
        p.drawEllipse(c, 24, 24)
        half = QPainterPath()
        half.moveTo(c)
        half.arcTo(QRectF(8, 8, 48, 48), 90, 180)
        p.fillPath(half, fg)
    elif kind == "slicer":                       # 3D printer: frame, gantry, nozzle, bed
        p.drawRoundedRect(QRectF(8, 8, 48, 48), 6, 6)
        p.drawLine(QPointF(8, 22), QPointF(56, 22))
        nozzle = QPainterPath()
        nozzle.moveTo(26, 22)
        nozzle.lineTo(38, 22)
        nozzle.lineTo(32, 32)
        nozzle.closeSubpath()
        p.fillPath(nozzle, fg)
        p.drawLine(QPointF(18, 46), QPointF(46, 46))
    elif kind == "freecad":                      # isometric cube
        top, mid, bot = QPointF(32, 8), QPointF(32, 32), QPointF(32, 58)
        l_up, r_up = QPointF(10, 20), QPointF(54, 20)
        l_dn, r_dn = QPointF(10, 46), QPointF(54, 46)
        for a, b in ((top, l_up), (top, r_up), (l_up, mid), (r_up, mid), (mid, bot),
                     (l_up, l_dn), (r_up, r_dn), (l_dn, bot), (r_dn, bot)):
            p.drawLine(a, b)
    elif kind == "files":                        # folder
        path = QPainterPath()
        path.moveTo(8, 18)
        path.lineTo(26, 18)
        path.lineTo(31, 24)
        path.lineTo(56, 24)
        path.lineTo(56, 52)
        path.lineTo(8, 52)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "viewer":                       # eye
        eye = QPainterPath()
        eye.moveTo(6, 32)
        eye.quadTo(32, 6, 58, 32)
        eye.quadTo(32, 58, 6, 32)
        p.drawPath(eye)
        p.setBrush(fg)
        p.drawEllipse(c, 7, 7)
    elif kind == "updates":                      # circular arrow
        p.drawArc(QRectF(10, 10, 44, 44), 60 * 16, 290 * 16)
        head = QPainterPath()
        head.moveTo(48, 6)
        head.lineTo(52, 22)
        head.lineTo(36, 20)
        head.closeSubpath()
        p.fillPath(head, fg)
    elif kind == "about":                        # (i)
        p.drawEllipse(c, 24, 24)
        p.drawLine(QPointF(32, 28), QPointF(32, 44))
        p.setBrush(fg)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(32, 19), 3.5, 3.5)
    if dot:
        p.setPen(QPen(QColor(ring), 3))
        p.setBrush(QColor(UPDATE_DOT))
        p.drawEllipse(QPointF(51, 13), 10, 10)
    p.end()
    return pm


def _tool_glyph(p: QPainter, kind: str, fg: QColor) -> None:
    """Draw one toolbar symbol on a 64 x 64 grid (same line style as the Settings icons)."""
    if kind == "menu":                           # hamburger
        for y in (18, 32, 46):
            p.drawLine(QPointF(12, y), QPointF(52, y))
    elif kind == "home":                         # house: roof, walls and a door
        house = QPainterPath()
        house.moveTo(8, 30)
        house.lineTo(32, 9)
        house.lineTo(56, 30)
        p.drawPath(house)
        walls = QPainterPath()
        walls.moveTo(15, 25)
        for x, y in ((15, 55), (49, 55), (49, 25)):
            walls.lineTo(x, y)
        p.drawPath(walls)
        door = QPainterPath()
        door.moveTo(26, 55)
        for x, y in ((26, 41), (38, 41), (38, 55)):
            door.lineTo(x, y)
        p.drawPath(door)
    elif kind == "open":                         # folder
        path = QPainterPath()
        path.moveTo(8, 18)
        for x, y in ((26, 18), (31, 24), (56, 24), (56, 52), (8, 52)):
            path.lineTo(x, y)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "recent":                       # clock with a turn-back arrow
        p.drawArc(QRectF(12, 12, 40, 40), 135 * 16, -315 * 16)
        p.drawLine(QPointF(10, 12), QPointF(17.9, 17.9))
        p.drawLine(QPointF(17.9, 17.9), QPointF(24, 10))
        p.drawLine(QPointF(32, 22), QPointF(32, 33))
        p.drawLine(QPointF(32, 33), QPointF(40, 39))
    elif kind == "screenshot":                   # camera
        p.drawRoundedRect(QRectF(8, 20, 48, 32), 6, 6)
        top = QPainterPath()
        top.moveTo(22, 20)
        top.lineTo(26, 13)
        top.lineTo(38, 13)
        top.lineTo(42, 20)
        p.drawPath(top)
        p.drawEllipse(QPointF(32, 36), 9, 9)
    elif kind == "theme":                        # palette
        pal = QPainterPath()
        pal.moveTo(32, 8)
        pal.arcTo(QRectF(8, 8, 48, 48), 90, 180)              # left half, down to (32, 56)
        pal.cubicTo(36, 56, 38, 53, 36, 49)
        pal.cubicTo(34, 45, 37, 42, 41, 42)
        pal.lineTo(48, 42)
        pal.arcTo(QRectF(40, 26, 16, 16), 270, 90)            # small curve up to (56, 34)
        pal.cubicTo(56, 19, 45, 8, 32, 8)
        p.drawPath(pal)
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(fg)
        for x, y in ((19, 31), (25, 19), (38, 17), (47, 26)):
            p.drawEllipse(QPointF(x, y), 3.5, 3.5)
        p.restore()
    elif kind == "slicer":                       # 3D printer with a part on the bed
        p.drawRoundedRect(QRectF(8, 8, 48, 48), 6, 6)
        p.drawLine(QPointF(8, 20), QPointF(56, 20))
        nozzle = QPainterPath()
        nozzle.moveTo(27, 20)
        nozzle.lineTo(37, 20)
        nozzle.lineTo(32, 28)
        nozzle.closeSubpath()
        p.fillPath(nozzle, fg)
        p.drawRect(QRectF(24, 34, 16, 12))
        p.drawLine(QPointF(16, 46), QPointF(48, 46))
    elif kind == "freecad":                      # cube, as on the Settings FreeCAD page
        top, mid, bot = QPointF(32, 6), QPointF(32, 30), QPointF(32, 58)
        l_up, r_up = QPointF(10, 18), QPointF(54, 18)
        l_dn, r_dn = QPointF(10, 46), QPointF(54, 46)
        for a, b in ((top, l_up), (top, r_up), (l_up, mid), (r_up, mid), (mid, bot),
                     (l_up, l_dn), (r_up, r_dn), (l_dn, bot), (r_dn, bot)):
            p.drawLine(a, b)
    elif kind == "settings":                     # gear
        p.drawEllipse(QPointF(32, 32), 9, 9)
        p.drawEllipse(QPointF(32, 32), 18, 18)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(32 + 18 * math.cos(a), 32 + 18 * math.sin(a)),
                       QPointF(32 + 25 * math.cos(a), 32 + 25 * math.sin(a)))
    elif kind == "updates":                      # circular arrow, as on the Settings Updates page
        p.drawArc(QRectF(10, 10, 44, 44), 60 * 16, 290 * 16)
        head = QPainterPath()
        head.moveTo(48, 6)
        head.lineTo(52, 22)
        head.lineTo(36, 20)
        head.closeSubpath()
        p.fillPath(head, fg)
    elif kind == "about":                        # (i)
        p.drawEllipse(QPointF(32, 32), 24, 24)
        p.drawLine(QPointF(32, 28), QPointF(32, 44))
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(fg)
        p.drawEllipse(QPointF(32, 19), 3.5, 3.5)
        p.restore()
    elif kind == "export":                       # page with an arrow going out
        page = QPainterPath()
        page.moveTo(40, 56)
        for x, y in ((14, 56), (14, 8), (36, 8), (46, 18), (46, 26)):
            page.lineTo(x, y)
        p.drawPath(page)
        fold = QPainterPath()
        fold.moveTo(36, 8)
        fold.lineTo(36, 18)
        fold.lineTo(46, 18)
        p.drawPath(fold)
        p.drawLine(QPointF(28, 40), QPointF(58, 40))
        p.drawLine(QPointF(50, 32), QPointF(58, 40))
        p.drawLine(QPointF(58, 40), QPointF(50, 48))


TOOL_ICONS = ("menu", "home", "open", "recent", "screenshot", "theme", "slicer", "freecad", "export",
              "settings", "updates", "about")


def tool_icon(kind: str, on_accent: bool = False, warm: bool = False) -> QIcon:
    """Toolbar icon: the symbol in the accent colour on a soft accent-tinted tile.
    on_accent=True is for the slicer button: a white symbol on a soft white tile.
    warm=True uses the theme's primary colour instead (the orange tiles of the Ember themes; the
    classic themes have the same teal for both, so there it looks the same)."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    t = colors()
    if on_accent:
        fg, tile = QColor("#ffffff"), QColor(255, 255, 255, 46)
    else:
        # The *_ink colour is darker on light themes, so the symbol stays crisp on the pale tile.
        fg = QColor(t["primary_ink" if warm else "accent_ink"])
        tile = QColor(t["primary" if warm else "accent"])
        tile.setAlphaF(0.22 if not is_dark() else 0.20)
    p.setPen(Qt.NoPen)
    p.setBrush(tile)
    p.drawRoundedRect(QRectF(0, 0, size, size), 14, 14)
    # The symbol sits inside the tile with a margin, drawn on its own 64 x 64 grid.
    p.translate(size * 0.12, size * 0.12)
    p.scale(0.76, 0.76)
    pen = QPen(fg, 6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    _tool_glyph(p, kind, fg)
    p.end()
    return QIcon(pm)


def apply_dark_theme(app):
    """Kept for older scripts."""
    return apply_theme(app, "dark")

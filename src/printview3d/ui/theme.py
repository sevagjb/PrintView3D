"""Colour themes: Automatic (follows the system), Dark, Gray, Graphite and Light.

A theme sets the colours of the window (Qt palette + style sheet) and of the
3D view (background, build plate, grid). The colours of G-code features and
models never change, so they always mean the same thing as in the slicer;
the 3D backgrounds are chosen so every feature colour stays visible.

Switching is immediate: apply_theme() restyles every window, and the main
window recolours the 3D view (MainWindow.apply_theme).
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap

from ..i18n import tr_noop

ACCENT = "#2fa4a0"
ACCENT_HOVER = "#38bbb6"

# Setting value -> name shown in Settings.
THEME_NAMES = {
    "auto": tr_noop("Automatic (system theme)"),
    "dark": tr_noop("Dark"),
    "gray": tr_noop("Gray"),
    "graphite": tr_noop("Graphite"),
    "light": tr_noop("Light"),
}
# Order used by Ctrl+T (next theme).
CYCLE = ["dark", "gray", "graphite", "light"]

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
    return "dark"                   # unknown: keep the classic look


def resolve(setting: str) -> str:
    if setting in THEMES:
        return setting
    return system_theme()


def current() -> str:
    """The theme in use ('dark', 'gray' or 'light')."""
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
    return (name or _current) != "light"


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
    pal.setColor(QPalette.Highlight, c(ACCENT))
    pal.setColor(QPalette.HighlightedText, c("#ffffff"))
    pal.setColor(QPalette.Link, c(t["link"]))
    pal.setColor(QPalette.PlaceholderText, c(t["placeholder"]))
    # Fusion draws frames/shadows from these.
    pal.setColor(QPalette.Light, c(t["button_hover"]))
    pal.setColor(QPalette.Midlight, c(t["button"]))
    pal.setColor(QPalette.Mid, c(t["border"]))
    pal.setColor(QPalette.Dark, c(t["bar_border"]))
    pal.setColor(QPalette.Shadow, c("#000000" if _current != "light" else "#9aa1aa"))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, c(t["disabled"]))
    app.setPalette(pal)
    app.setStyleSheet(f"""
        QToolBar {{ background: {t['bar']}; border: none; border-bottom: 1px solid {t['bar_border']}; spacing: 4px; padding: 4px; }}
        QToolButton {{ padding: 5px 9px; border-radius: 5px; color: {t['text']}; }}
        QToolButton:hover {{ background: {t['tool_hover']}; }}
        QToolButton:checked {{ background: {t['tool_checked']}; }}
        QToolBar QToolButton {{ border: 1px solid {t['button_border']}; background: {t['button']};
            padding: 4px 10px; margin: 1px 2px; font-weight: 600; }}
        QToolBar QToolButton:hover {{ background: {t['button_hover']}; border-color: {t['muted']}; }}
        QToolBar QToolButton:checked {{ background: {t['tool_checked']}; border-color: {ACCENT}; }}
        QToolBar QToolButton#themeButton {{ padding: 4px 6px; }}
        QToolBar QToolButton#themeButton::menu-indicator {{ image: none; width: 0; }}
        QToolButton#slicerButton {{ background: {ACCENT}; color: white; font-weight: 600; padding: 6px 14px; }}
        QToolButton#slicerButton:hover {{ background: {ACCENT_HOVER}; }}
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
        QPushButton#primary {{ background: {ACCENT}; border: none; color: white; font-weight: 600; }}
        QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
        QPushButton#link {{ color: {t['link']}; border: none; background: transparent; }}
        QPushButton#link:hover {{ text-decoration: underline; }}
        QScrollArea {{ border: none; }}
        QSlider::groove:horizontal {{ height: 6px; background: {t['groove']}; border-radius: 3px; }}
        QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {t['handle']}; border: 1px solid {t['handle_border']};
            width: 14px; margin: -6px 0; border-radius: 8px; }}
        QStatusBar {{ background: {t['bar']}; color: {t['group_title']}; }}
        QListWidget {{ border: 1px solid {t['border']}; border-radius: 6px; }}
        QListWidget#settingsNav {{ background: {t['bar']}; border-radius: 8px; padding: 6px; outline: none; }}
        QListWidget#settingsNav::item {{ padding: 0px 6px; border-radius: 6px; color: {t['text']}; }}
        QListWidget#settingsNav::item:hover {{ background: {t['tool_hover']}; }}
        QListWidget#settingsNav::item:selected {{ background: {t['tool_checked']}; color: {t['text']}; }}
        QLabel#pageTitle {{ font-size: 18px; font-weight: 600; padding-bottom: 4px; }}
        QLabel#versionBadge {{
            color: {t['muted']}; background: {t['button']};
            border: 1px solid {t['button_border']}; border-radius: 4px;
            padding: 1px 8px; margin: 2px 4px;
        }}
        QLabel#versionBadge:hover {{ background: {t['button_hover']}; }}
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
        hints.setColorScheme(Qt.ColorScheme.Light if _current == "light" else Qt.ColorScheme.Dark)
    except Exception:  # noqa: BLE001 - a platform without this keeps the system's choice
        pass


def _mica_css(t: dict, name: str) -> str:
    light = name == "light"
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


UPDATE_DOT = "#e5484d"      # the red "update available" dot
UP_TO_DATE_DOT = "#30a46c"  # the green "up to date" dot


def nav_icon(kind: str, dot: bool = False) -> QIcon:
    """Line icons for the Settings sidebar, in the theme's text colour (sharp at any scale).
    With dot=True a red dot marks the icon (update available)."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    fg = QColor(colors()["text"])
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
        p.setPen(QPen(QColor(colors()["bar"]), 3))
        p.setBrush(QColor(UPDATE_DOT))
        p.drawEllipse(QPointF(51, 13), 10, 10)
    p.end()
    return QIcon(pm)


def apply_dark_theme(app):
    """Kept for older scripts."""
    return apply_theme(app, "dark")

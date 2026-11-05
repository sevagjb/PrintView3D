"""Main application window."""

from __future__ import annotations

import gc
import math
import os
import sys
import threading
from typing import Optional

import numpy as np
from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QFont, QFontMetrics, QGuiApplication, QIcon,
                           QKeySequence, QPixmap, QShortcut)
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QColorDialog, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QSpinBox, QSplitter, QStackedWidget, QToolBar,
    QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__
from .. import units
from .. import archive as za
from .. import freecad as fc
from .. import slicer as sl
from .. import gpu
from ..gpu import renderer_info
from ..i18n import count, ltr, num, tr
from ..loaders import (
    FEATURES, GcodeData, ModelData, SEND_AS_STL, SUPPORTED_EXTENSIONS, file_kind, load_file,
    parse_gcode_text, read_3mf_for_export, read_embedded_gcode, stl_file_names, write_binary_stl,
)
from ..loaders.gcode import FEATURE_INDEX
from ..settings import EXPORT_MODES, Settings
from .labels import feature_label, meta_label, meta_value, plate_mode_label
from . import theme, update_ui
from .. import updates as up
from .export_stl import ExportStlDialog
from .scene import PLATE_MODES, Scene
from .settings_dialog import SettingsDialog
from . import send_dialog as sd

RESOURCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
GCODE_META_ORDER = ("Print time", "Filament (g)", "Filament (mm)", "Filament type", "Layer height",
                    "Nozzle", "Printer", "Printer profile", "Slicer")


def resource(name: str) -> str:
    return os.path.join(RESOURCES, name)


def file_filter() -> str:
    return ";;".join([
        tr("3D files") + " (*.stl *.3mf *.obj *.ply *.off *.glb *.gltf *.step *.stp *.STEP *.STP "
                         "*.gcode *.gco *.g *.FCStd *.fcstd *.zip)",
        tr("STL models") + " (*.stl)",
        tr("3MF projects") + " (*.3mf)",
        tr("Other 3D models") + " (*.obj *.ply *.off *.glb *.gltf)",
        tr("G-code") + " (*.gcode *.gco *.g)",
        tr("FreeCAD documents") + " (*.FCStd *.fcstd)",
        tr("STEP CAD files") + " (*.step *.stp *.STEP *.STP)",
        tr("ZIP files with 3D models") + " (*.zip)",
        tr("All files") + " (*)",
    ])


def _swatch(color: str, size: int = 12) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(QColor(color))
    return QIcon(pm)


# The coloured type labels in the ZIP list: (label, background, text on dark, text on light)
_TYPE_TAGS = {
    "stl": ("STL", "rgba(47,164,160,0.22)", "#6fd6d1", "#17706c"),
    "3mf": ("3MF", "rgba(127,119,221,0.24)", "#b9b3f2", "#4a41a8"),
    "gcode": ("G-code", "rgba(232,163,61,0.24)", "#f2c27e", "#8a5608"),
    "step": ("STEP", "rgba(55,138,221,0.22)", "#9cc6f2", "#185fa5"),
    "freecad": ("FreeCAD", "rgba(55,138,221,0.22)", "#9cc6f2", "#185fa5"),
}
_OTHER_TAG = ("rgba(136,135,128,0.25)", "#c9c8c0", "#4a4944")
_KIND_LABELS = {"obj": "OBJ", "ply": "PLY", "off": "OFF", "gltf": "glTF"}


def _type_info(kind: str) -> str:
    """One line that says what a file type is (ZIP list), for people new to 3D printing."""
    if kind == "stl":
        return tr("STL: one model shape")
    if kind == "3mf":
        return tr("3MF: project with objects, colours and settings")
    if kind == "gcode":
        return tr("G-code: already sliced, ready to print")
    if kind == "step":
        return tr("STEP: CAD model (shown with the help of FreeCAD)")
    if kind == "freecad":
        return tr("FreeCAD: CAD document")
    return tr("{kind}: 3D model").format(kind=_KIND_LABELS.get(kind, kind.upper()))


def _wrappable(name: str) -> str:
    """A file name that can wrap: an invisible break chance after + _ - . (Downloads such as
    "Elegoo+72mm+spool+adjustable+silica+holder.3mf" have no spaces, and one unbreakable name
    made the whole side panel wider than the window.)"""
    for ch in "+_-.":
        name = name.replace(ch, ch + "\u200b")
    return name


def _breakable(text: str, longer_than: int = 16) -> str:
    """Words longer than `longer_than` letters (BambuStudio-02.03.00.70, profile names joined
    with _ or @) get invisible break chances like file names, so a narrow side panel can wrap
    them instead of cutting them off at its edge."""
    return " ".join(_wrappable(w) if len(w) > longer_than else w for w in text.split(" "))


def _size_text(size: int) -> str:
    if size >= 1024 * 1024:
        return tr("{n} MB").format(n=num(size / (1024 * 1024), 1))
    return tr("{n} KB").format(n=num(max(1, round(size / 1024)), 0))


def _short_mm(v: float) -> str:
    """A length (mm) for the Objects list: whole millimetres without decimals, otherwise one; in
    inches two decimals."""
    if units.imperial():
        return units.number(v, 0)
    return num(v, 0 if abs(v - round(v)) < 0.05 else 1)


def _size_mm(size: tuple) -> str:
    """'20 × 12.5 × 3 mm': an object's size in the Objects list (issue #59)."""
    return tr("{x} × {y} × {z} {unit}").format(x=_short_mm(size[0]), y=_short_mm(size[1]), z=_short_mm(size[2]),
                                               unit=units.name())


def _plate_name(member: str) -> str:
    """'Metadata/plate_2.gcode' -> 'Plate 2' (translated)."""
    stem = os.path.splitext(os.path.basename(member))[0]
    digits = "".join(ch for ch in stem if ch.isdigit())
    return tr("Plate {n}").format(n=digits) if digits else stem


class _LoadSignals(QObject):
    progress = Signal(int, float)
    done = Signal(int, object)
    failed = Signal(int, str)


class _ExportSignals(QObject):
    done = Signal(str, object)      # path, list of MeshPart
    failed = Signal(str, str)       # path, error


# Icons with text beside them: 22 px, plus the empty gap on their right (theme.tool_icon(gap=True)).
TEXT_ICON = QSize(22 + theme.ICON_GAP, 22)


class _FitButton(QToolButton):
    """A button of the View or Measure section whose icon and name always show in full. When the
    panel is narrow its font gets a little smaller; the side panel is never narrower than the
    smallest font needs (MainWindow._update_side_min_width), so the icon never has to go and no
    character is cut off. The buttons of one group (a row or grid) take the same font, so they
    keep looking alike."""

    SCALES = (1.0, 0.92, 0.84)                       # font sizes it tries, of the normal size
    PAD = 20                                         # the button's padding and border, both sides
    ICON = 22 + theme.ICON_GAP + 2                   # the icon, its gap and Qt's own 2 px before the text

    def __init__(self, group: list, parent=None):
        super().__init__(parent)
        self.group = group
        group.append(self)
        self._base = None
        self._level = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def setDefaultAction(self, action):
        super().setDefaultAction(action)
        action.changed.connect(self.fit)

    def _text(self) -> str:
        a = self.defaultAction()
        return a.text().replace("&", "") if a is not None else ""

    def minimumSizeHint(self):
        """Wide enough for the icon and the name in the smallest font."""
        need = QFontMetrics(self._font(self.SCALES[-1])).horizontalAdvance(self._text()) + self.ICON + self.PAD
        return QSize(int(math.ceil(need)) + 1, super().sizeHint().height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()

    def _font(self, scale: float) -> QFont:
        if self._base is None:
            self._base = QFont(self.font())
        f = QFont(self._base)
        if self._base.pointSizeF() > 0:
            f.setPointSizeF(self._base.pointSizeF() * scale)
        else:
            f.setPixelSize(max(6, int(self._base.pixelSize() * scale)))
        f.setWeight(QFont.DemiBold)
        return f

    def level_needed(self) -> int:
        """The largest font (0 = normal) at which icon and name fit in the button's width."""
        room = self.width() - self.PAD
        for level, scale in enumerate(self.SCALES):
            if QFontMetrics(self._font(scale)).horizontalAdvance(self._text()) + self.ICON <= room:
                return level
        return len(self.SCALES) - 1

    def apply_level(self, level: int):
        if level == self._level:
            return
        self._level = level
        self.setFont(self._font(self.SCALES[level]))
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)        # the icon always stays

    def fit(self):
        """Every button of the group takes the font the narrowest one needs."""
        if self.defaultAction() is None or self.width() <= 1:
            return
        self.updateGeometry()                        # a new name may need another minimum width
        level = max(b.level_needed() for b in self.group if b.width() > 1 and b.defaultAction() is not None)
        for b in self.group:
            b.apply_level(level)


class _FitLabel(QLabel):
    """A label that always stays on one line: when the panel is too narrow its font gets smaller
    (down to MIN_SCALE of the normal size) until the whole text fits."""

    MIN_SCALE = 0.7

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(False)
        self._base = None
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def setText(self, text: str):
        super().setText(text)
        self._fit()

    def minimumSizeHint(self):
        return QSize(0, super().sizeHint().height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def _fit(self):
        if self._base is None:
            self._base = QFont(self.font())
        room = self.width() - self.contentsMargins().left() - self.contentsMargins().right() - 2
        if room <= 1 or not self.text():
            return
        scale = 1.0
        while scale > self.MIN_SCALE:
            f = QFont(self._base)
            if self._base.pointSizeF() > 0:
                f.setPointSizeF(self._base.pointSizeF() * scale)
            else:
                f.setPixelSize(max(6, int(self._base.pixelSize() * scale)))
            if QFontMetrics(f).horizontalAdvance(self.text()) <= room:
                break
            scale -= 0.05
        f = QFont(self._base)
        if self._base.pointSizeF() > 0:
            f.setPointSizeF(self._base.pointSizeF() * max(scale, self.MIN_SCALE))
        else:
            f.setPixelSize(max(6, int(self._base.pixelSize() * max(scale, self.MIN_SCALE))))
        if f != self.font():
            self.setFont(f)


class _FitRow(QWidget):
    """Widgets side by side while they fit; when the panel is too narrow, one under the other."""

    def __init__(self, widgets, spacing: int = 16, parent=None):
        super().__init__(parent)
        self._widgets = list(widgets)
        self._spacing = spacing
        self._stacked = None
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSizeConstraint(QGridLayout.SetNoConstraint)    # free to get narrower than the row
        self._grid.setHorizontalSpacing(spacing)
        self._grid.setVerticalSpacing(4)
        self._arrange(False)

    @property
    def stacked(self) -> bool:
        return bool(self._stacked)

    def _needed(self) -> int:
        return sum(w.sizeHint().width() for w in self._widgets) + self._spacing * (len(self._widgets) - 1)

    def _arrange(self, stacked: bool):
        if stacked == self._stacked:
            return
        self._stacked = stacked
        for w in self._widgets:
            self._grid.removeWidget(w)
        for i, w in enumerate(self._widgets):
            self._grid.addWidget(w, i if stacked else 0, 0 if stacked else i)
        self._grid.setColumnStretch(len(self._widgets), 0 if stacked else 1)
        self.updateGeometry()

    def minimumSizeHint(self):
        return QSize(0, self._grid.minimumSize().height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._arrange(self.width() < self._needed())


class _ColorButton(QToolButton):
    """The colour box of an object: it shows the object's colour, a click picks another one and a
    right-click goes back to the colour from the file."""

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("colorBox")
        self.setFixedSize(22, 22)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.set_color(color)

    def set_color(self, color: str):
        self.color = color
        self.setStyleSheet(
            "QToolButton#colorBox {{ background: {c}; border: 1px solid rgba(128, 128, 128, 0.7);"
            " border-radius: 5px; padding: 0; margin: 0; }}"
            "QToolButton#colorBox:hover {{ border: 2px solid palette(highlight); }}".format(c=color))


class _ElidedLabel(QLabel):
    """A one-line label that ends in "…" when it does not fit; the tooltip has the full text."""

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._full = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(20)
        self.setText(text)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.setText(self.fontMetrics().elidedText(self._full, Qt.ElideRight, max(10, self.width())))


class _LongValue(QWidget):
    """A long detail value (such as a project's description): the first lines, and a
    "Show more" / "Show less" link when there is more. A description of a few paragraphs
    made the Details box so tall that the Objects box ended up below the window (issue #62)."""

    LINES = 4

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.expanded = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignTop | Qt.AlignLeading)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.label)
        self.toggle = QLabel()
        self.toggle.setObjectName("moreLink")
        self.toggle.setWordWrap(True)
        self.toggle.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        self.toggle.linkActivated.connect(lambda _=None: self.set_expanded(not self.expanded))
        lay.addWidget(self.toggle)
        self._update()

    def collapsed_height(self) -> int:
        return self.label.fontMetrics().lineSpacing() * self.LINES

    def is_clamped(self) -> bool:
        """True when the text is longer than the first lines (so the link is shown)."""
        return self.label.heightForWidth(max(1, self.label.width())) > self.collapsed_height()

    def set_expanded(self, on: bool):
        self.expanded = on
        self._update()

    def _update(self):
        long_text = self.is_clamped()
        self.label.setMaximumHeight(16777215 if (self.expanded or not long_text) else self.collapsed_height())
        self.toggle.setVisible(long_text)
        self.toggle.setText('<a href="#">{}</a>'.format(tr("Show less") if self.expanded else tr("Show more")))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update()           # a narrower panel wraps into more lines


class _RowList(QListWidget):
    """A list of row widgets that follow the list's width. (A plain QListWidget keeps a row
    widget at its first width: when the panel's scroll bar appeared, the rows stayed 14 px
    too wide and the file sizes at their right end were cut off.)"""

    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(0, self.doItemsLayout)


class _KeySwallower(QObject):
    """Stops VTK's built-in single-letter shortcuts (wireframe, quit, ...)."""

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            return True
        return False


class PlateSizeDialog(QDialog):
    """Plate menu -> Custom size: width and depth of the plate in millimetres."""

    MIN, MAX = 10, 5000

    def __init__(self, size: tuple, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Plate size"))
        form = QFormLayout(self)
        from .length_spin import LengthSpin
        self.width_spin = LengthSpin(self.MIN, self.MAX)
        self.depth_spin = LengthSpin(self.MIN, self.MAX)
        for spin, value in ((self.width_spin, size[0]), (self.depth_spin, size[1])):
            spin.set_mm(value)
        form.addRow(tr("Width (X)"), self.width_spin)
        form.addRow(tr("Depth (Y)"), self.depth_spin)
        note = QLabel(tr("The plate starts at the printer's origin (0, 0) when the file has one, "
                         "otherwise it is centred under the model."))
        note.setObjectName("muted")
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def plate_size(self) -> tuple:
        return (self.width_spin.mm(), self.depth_spin.mm())


def _return_free_memory() -> None:
    """Linux: ask the C library to give memory that is free again back to the system. Without
    this it keeps it for later, and the program looks just as big after closing a file.
    Windows and macOS give large freed blocks back by themselves."""
    if not sys.platform.startswith("linux"):
        return
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):      # not glibc (e.g. musl): nothing to do
        pass


class MainWindow(QMainWindow):
    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        self.settings = settings or Settings()
        self.folder: Optional[dict] = None          # Open folder: {"path", "files"}
        self._folder_index = 0
        units.set_unit(self.settings.get("units", "mm"))       # before any length is shown
        self.current_path: Optional[str] = None
        self.current_kind = ""
        self.model: Optional[ModelData] = None
        self.gcode: Optional[GcodeData] = None
        self.showing_embedded = False
        self._embedded_member = ""
        self._file_size_mb = 0.0
        self._load_token = 0
        # ZIP files: what is inside, which entry is shown (-1 = Show all), and for Show all
        # which entry each part came from.
        self.zip: Optional[za.ZipContents] = None
        self._zip_index = 0
        self._zip_last_single = 0
        self._zip_wanted = 0                # the entry asked for (a quick second ↓ continues from it)
        self._zip_owner: list[int] = []
        self._pending_zip: tuple = (None, 0)

        self.setWindowTitle(APP_NAME)
        self.setObjectName("mainWindow")
        self.mica = False                   # Windows 11 Mica, switched on by enable_mica() at start
        # What this window started with; Settings offers a restart when these are changed.
        self.backdrop_at_start = "off"      # set by app.main() after enable_mica()
        self.gpu_at_start = gpu.high_performance_enabled()
        self.file_server = None             # files from later starts (see start_file_server)
        # Windows: the .ico holds every size the taskbar and Alt+Tab need.
        self.setWindowIcon(QIcon(resource("icon.ico" if sys.platform == "win32" else "icon.png")))
        self.resize(1320, 840)
        self.setAcceptDrops(True)

        self._signals = _LoadSignals()
        self._signals.progress.connect(self._on_progress)
        self._signals.done.connect(self._on_loaded)
        self._signals.failed.connect(self._on_failed)
        self._export_signals = _ExportSignals()
        self._export_signals.done.connect(self._on_export_read)
        self._export_signals.failed.connect(self._on_export_failed)

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._build_shortcuts()
        sl.migrate_settings(self.settings)

        self._gcode_timer = QTimer(self)
        self._gcode_timer.setSingleShot(True)
        self._gcode_timer.setInterval(15)
        self._gcode_timer.timeout.connect(self._redraw_gcode)

        # Installing translators sends several LanguageChange events; handle them once.
        self._retranslate_timer = QTimer(self)
        self._retranslate_timer.setSingleShot(True)
        self._retranslate_timer.setInterval(0)
        self._retranslate_timer.timeout.connect(self._on_language_changed)

        self.retranslate_ui()
        self._update_view_menu()            # nothing open yet: View is greyed out

        # "Automatic" theme: follow the system when it switches dark/light.
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_theme_changed)
        except AttributeError:      # Qt older than 6.5
            pass

    # ================================================================ theme
    def apply_theme(self, choice: str):
        """Switch theme now: windows, then the 3D view."""
        theme.apply_theme(QApplication.instance(), choice, mica=self.mica)
        if self.mica:
            from .. import win_mica
            win_mica.set_dark(int(self.winId()), theme.is_dark())
            # Once more after Qt has finished its own update of the window, so ours is the last word.
            QTimer.singleShot(200, lambda: self.mica and win_mica.set_dark(int(self.winId()), theme.is_dark()))
        self.scene.set_colors(theme.colors())
        self.view_cube.set_colors(theme.colors())
        if hasattr(self, "measure"):
            self.measure.set_colors(theme.colors())
            self.hints.set_colors(theme.colors())
            self.grid_labels.set_colors(theme.colors())
        self._update_theme_button()
        self.refresh_update_badge()
        # The ZIP list's type labels take their text colour from the theme when they are made.
        if self.zip is not None and self.stack.currentIndex() == 1:
            self._fill_zip_box()
        self.plotter.render()

    def prepare_mica(self):
        """Before the window is shown: transparent window background (Windows 11 Mica)."""
        self.mica = True
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        theme.apply_theme(QApplication.instance(), theme.setting(), mica=True)

    def enable_mica(self, kind: str = "mica") -> bool:
        """After show(): ask Windows for the Mica backdrop. Falls back to the normal look."""
        from .. import win_mica
        ok = win_mica.apply(int(self.winId()), theme.is_dark(), kind)
        if not ok:                                   # Windows said no: solid backgrounds again
            self.mica = False
            self.setAttribute(Qt.WA_TranslucentBackground, False)
            theme.apply_theme(QApplication.instance(), theme.setting(), mica=False)
        return ok

    def choose_theme(self, choice: str):
        """From the toolbar menu or Ctrl+T: switch and remember."""
        self.settings.set("theme", choice)
        self.apply_theme(choice)

    def next_theme(self):
        """Ctrl+T: the next style, in the same mode."""
        self.choose_theme(theme.next_theme(theme.setting()))

    def toggle_light_dark(self):
        """Ctrl+Shift+T: the same style, light <-> dark."""
        self.choose_theme(theme.toggle_light_dark(theme.setting()))

    def _choose_style(self, style: str):
        self.choose_theme(theme.make_choice(style, theme.split_choice(theme.setting())[1]))

    def _choose_mode(self, mode: str):
        self.choose_theme(theme.make_choice(theme.split_choice(theme.setting())[0], mode))

    def _update_theme_button(self):
        if not hasattr(self, "theme_btn"):
            return
        self._update_toolbar_icons()
        style, mode = theme.split_choice(theme.setting())
        for key, a in self.style_actions.items():
            a.setText(tr(theme.STYLE_NAMES[key]))
            a.setIcon(theme.theme_swatch(theme.theme_for(key, mode)))
            a.setChecked(key == style)
        for key, a in self.mode_actions.items():
            a.setText(tr(theme.MODE_NAMES[key]))
            a.setIcon(theme.segment_icon(key, menu=True))
            a.setChecked(key == mode)
        self.act_next_theme.setText(tr("Next theme style") + "\t" + self._native("Ctrl+T"))
        self.act_toggle_dark.setText(tr("Switch between light and dark") + "\t" + self._native("Ctrl+Shift+T"))
        self.theme_btn.setToolTip(tr("Theme: {name} (Ctrl+T: next theme)").format(
            name=theme.display_name(theme.make_choice(style, mode))))

    @staticmethod
    def _native(seq: str) -> str:
        return QKeySequence(seq).toString(QKeySequence.NativeText)

    def _system_theme_changed(self, *_):
        if theme.follows_system():
            self.apply_theme(theme.setting())

    # =================================================================== UI
    def _build_toolbar(self):
        tb = QToolBar()
        tb.setObjectName("mainToolbar")          # the Mica style rules name it (theme.MICA_CSS)
        tb.setMovable(False)
        tb.setIconSize(TEXT_ICON)                # square icons stay 22 x 22; icons with text get their gap
        # Buttons with an icon show it beside their text; the view buttons have no icon (text only).
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(tb)

        def icon_button(menu: QMenu | None = None, action: QAction | None = None) -> QToolButton:
            """A square icon tile (no text; the tooltip names it)."""
            b = QToolButton()
            b.setObjectName("iconButton")
            b.setIconSize(QSize(22, 22))
            b.setToolButtonStyle(Qt.ToolButtonIconOnly)
            if action is not None:
                b.setDefaultAction(action)
            if menu is not None:
                b.setMenu(menu)
                b.setPopupMode(QToolButton.InstantPopup)
            return b

        # Actions live on the window too, so their shortcuts work wherever the button is.
        self.act_open = QAction(self, shortcut=QKeySequence.Open, triggered=self.open_dialog)
        # Home: close the file and go back to the start page (frees what the file took).
        self.act_home = QAction(self, shortcut=QKeySequence("Ctrl+W"), triggered=self.go_home)
        self.act_home.setEnabled(False)                 # nothing open yet
        self.addAction(self.act_home)
        self.act_screenshot = QAction(self, triggered=self.save_screenshot)
        self.act_settings = QAction(self, triggered=self.open_settings)
        self.act_updates = QAction(self, triggered=lambda: self.open_settings("updates"))
        self.act_about = QAction(self, triggered=lambda: self.open_settings("about"))
        # This version's notes, any time (the same window as once after an update).
        self.act_whats_new = QAction(self, triggered=lambda: update_ui.show_current(self))
        self.addAction(self.act_open)

        self.recent_menu = QMenu(self)

        # Menu (hamburger): everything in one place, with the shortcuts shown.
        self.main_menu = QMenu(self)
        self.main_menu.addAction(self.act_home)
        self.main_menu.addAction(self.act_open)
        # Open folder: its 3D files in a list, stepped through with the arrow keys like a ZIP.
        self.act_open_folder = QAction(self, triggered=self.open_folder_dialog)
        self.main_menu.addAction(self.act_open_folder)
        self.main_menu.addMenu(self.recent_menu)
        self.main_menu.addSeparator()
        self.main_menu.addAction(self.act_screenshot)
        self.main_menu.addSeparator()
        self.main_menu.addAction(self.act_settings)
        self.main_menu.addAction(self.act_updates)
        self.main_menu.addAction(self.act_whats_new)
        self.main_menu.addAction(self.act_about)
        self.menu_btn = icon_button(menu=self.main_menu)
        tb.addWidget(self.menu_btn)

        # Home and Open next to the menu. Recent is in the menu only, and the start page lists the
        # recent files too (#66).
        self.home_btn = icon_button(action=self.act_home)
        tb.addWidget(self.home_btn)
        self.open_btn = icon_button(action=self.act_open)
        tb.addWidget(self.open_btn)

        tb.addSeparator()
        self.slicer_btn = QToolButton()
        self.slicer_btn.setObjectName("slicerButton")
        self.slicer_btn.setIconSize(TEXT_ICON)
        self.slicer_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.slicer_btn.clicked.connect(lambda: self.open_in_slicer())
        # The small arrow: send the file to another slicer just once.
        self.slicer_menu = QMenu(self)
        self.slicer_menu.aboutToShow.connect(self._fill_slicer_menu)
        self.slicer_btn.setMenu(self.slicer_menu)
        self.slicer_btn.setPopupMode(QToolButton.MenuButtonPopup)
        tb.addWidget(self.slicer_btn)
        # 3MF projects, FreeCAD and STEP files: save the objects as plain STL files.
        # A click (or Ctrl+E) does what Settings -> Files says; the arrow offers every way.
        self.act_export_stl = QAction(self, triggered=lambda: self.export_stl())
        self.act_export_stl.setShortcut(QKeySequence("Ctrl+E"))
        self.addAction(self.act_export_stl)
        self.act_export_one = QAction(self, triggered=lambda: self.export_stl("combined"))
        self.act_export_each = QAction(self, triggered=lambda: self.export_stl("per_object"))
        self.act_export_choose = QAction(self, triggered=lambda: self.export_stl("dialog"))
        self.act_export_setting = QAction(self, triggered=lambda: self.open_settings("files"))
        self.export_menu = QMenu(self)
        self.export_menu.addAction(self.act_export_one)
        self.export_menu.addAction(self.act_export_each)
        self.export_menu.addAction(self.act_export_choose)
        self.export_menu.addSeparator()
        self.export_menu.addAction(self.act_export_setting)
        self.export_menu.aboutToShow.connect(self._mark_export_default)
        self.export_btn = QToolButton()
        self.export_btn.setObjectName("exportButton")
        self.export_btn.setIconSize(TEXT_ICON)
        self.export_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.export_btn.setDefaultAction(self.act_export_stl)
        self.export_btn.setMenu(self.export_menu)
        self.export_btn.setPopupMode(QToolButton.MenuButtonPopup)
        self.export_btn_act = tb.addWidget(self.export_btn)
        self._set_export_visible(False)
        tb.addSeparator()

        self.view_actions = []
        for view, key in ((None, "F"), ("iso", "1"), ("top", "2"), ("front", "3"), ("right", "4")):
            act = QAction(self)
            act.triggered.connect(lambda _=False, v=view: self.set_view(v, animate=True))
            if view is None:
                self.act_fit = act                   # Fit goes after Measure (below), with an icon
            else:
                tb.addAction(act)
            self.view_actions.append((act, key, view))

        self.act_bed = QAction(self, checkable=True)
        self.act_bed.setChecked(bool(self.settings.get("show_bed", True)))
        self.act_bed.toggled.connect(self._toggle_bed)
        tb.addAction(self.act_bed)
        # Named, so a theme can style them on their own (Ember Light fills them with teal).
        for act in [a for a, _, v in self.view_actions if v is not None] + [self.act_bed]:
            tb.widgetForAction(act).setObjectName("viewButton")
        # The Plate button's arrow: which plate to draw (issue #61). A click still shows / hides it.
        self.plate_menu = QMenu(self)
        self.plate_group = QActionGroup(self)
        self.plate_actions = {}
        for mode in PLATE_MODES:
            a = QAction(self, checkable=True)
            a.triggered.connect(lambda _=False, m=mode: self.choose_plate_mode(m))
            self.plate_group.addAction(a)
            self.plate_menu.addAction(a)
            self.plate_actions[mode] = a
        self.plate_menu.aboutToShow.connect(self._mark_plate_mode)
        self.plate_btn = tb.widgetForAction(self.act_bed)
        self.plate_btn.setMenu(self.plate_menu)
        self.plate_btn.setPopupMode(QToolButton.MenuButtonPopup)
        # View: how the model is drawn (issue #60). Models only; G-code toolpaths are lines
        # already and have the layer slider as their cut.
        self.act_wireframe = QAction(self, checkable=True, shortcut=QKeySequence("W"))
        self.act_wireframe.toggled.connect(self.set_wireframe)
        self.act_xray = QAction(self, checkable=True, shortcut=QKeySequence("X"))
        self.act_xray.toggled.connect(self.set_xray)
        self.act_clip = QAction(self, checkable=True, shortcut=QKeySequence("C"))
        self.act_clip.toggled.connect(self.set_clip_on)
        # Clip facing you: an upright cut that turns with the view. Both cuts can be on together
        # (#70); C and V each turn their own cut on and off.
        self.act_clip_face = QAction(self, checkable=True, shortcut=QKeySequence("V"))
        self.act_clip_face.toggled.connect(self.set_clip_face_on)
        # Reset view (#66): all of the above off and the model fitted, in one go.
        self.act_reset_view = QAction(self, shortcut=QKeySequence("R"), triggered=self.reset_view)
        # Measure: distances, angles and circles on the model; a click places a point.
        self.act_measure = QAction(self, checkable=True, shortcut=QKeySequence("M"))
        self.act_measure.toggled.connect(self.set_measure_on)
        for a in (self.act_wireframe, self.act_xray, self.act_clip, self.act_clip_face, self.act_reset_view,
                  self.act_measure):
            self.addAction(a)                   # the shortcuts work wherever the focus is
        # The View and Measure buttons are switches: each opens its own section in the side panel
        # (View: how the model is drawn and cut; Measure: distances, angles and circles).
        # Check (between Plate and View): overhangs, thin walls and mesh problems, in its section.
        self.act_check = QAction(self, checkable=True)
        self.act_check.toggled.connect(self.set_check_section)
        self.check_btn = QToolButton()
        self.check_btn.setObjectName("viewButton")
        self.check_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.check_btn.setDefaultAction(self.act_check)
        tb.addWidget(self.check_btn)
        self.act_view = QAction(self, checkable=True)
        self.act_view.toggled.connect(self.set_view_section)
        self.view_btn = QToolButton()
        self.view_btn.setObjectName("viewButton")
        self.view_btn.setIconSize(QSize(22, 22))
        self.view_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.view_btn.setDefaultAction(self.act_view)
        tb.addWidget(self.view_btn)
        self.measure_group = QActionGroup(self)
        self.measure_actions = {}
        for kind in ("distance", "angle", "circle"):
            a = QAction(self, checkable=True)
            a.triggered.connect(lambda _=False, k=kind: self.choose_measure_mode(k))
            self.measure_group.addAction(a)
            self.measure_actions[kind] = a
        self.measure_actions[self._measure_mode_setting()].setChecked(True)
        self.measure_btn = QToolButton()
        self.measure_btn.setObjectName("viewButton")
        self.measure_btn.setIconSize(QSize(22, 22))
        self.measure_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.measure_btn.setDefaultAction(self.act_measure)
        tb.addWidget(self.measure_btn)
        tb.addAction(self.act_fit)
        tb.widgetForAction(self.act_fit).setObjectName("viewButton")
        # The view buttons with an icon: styled to be as tall as the others (theme: hasIcon).
        for b in (self.plate_btn, self.check_btn, self.view_btn, self.measure_btn, tb.widgetForAction(self.act_fit)):
            b.setProperty("hasIcon", True)
            b.setIconSize(TEXT_ICON)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.screenshot_btn = icon_button(action=self.act_screenshot)
        tb.addWidget(self.screenshot_btn)

        # Theme: palette at the end of the toolbar; its menu has the styles, then Light/Dark/System.
        self.theme_menu = QMenu(self)
        self.theme_group = QActionGroup(self)
        self.style_actions = {}
        for key in theme.STYLES:
            a = QAction("", self, checkable=True)
            a.triggered.connect(lambda _=False, k=key: self._choose_style(k))
            self.theme_group.addAction(a)
            self.theme_menu.addAction(a)
            self.style_actions[key] = a
        self.theme_menu.addSeparator()
        self.mode_group = QActionGroup(self)
        self.mode_actions = {}
        for key in theme.MODES:
            a = QAction("", self, checkable=True)
            a.triggered.connect(lambda _=False, k=key: self._choose_mode(k))
            self.mode_group.addAction(a)
            self.theme_menu.addAction(a)
            self.mode_actions[key] = a
        self.theme_menu.addSeparator()
        self.act_next_theme = QAction(self, triggered=self.next_theme)
        self.theme_menu.addAction(self.act_next_theme)
        self.act_toggle_dark = QAction(self, triggered=self.toggle_light_dark)
        self.theme_menu.addAction(self.act_toggle_dark)
        self.theme_btn = icon_button(menu=self.theme_menu)
        tb.addWidget(self.theme_btn)

    def _update_toolbar_icons(self):
        """Draw the toolbar icons in the current theme's colours (again after a theme switch)."""
        if not hasattr(self, "theme_btn"):
            return
        self.menu_btn.setIcon(theme.tool_icon("menu"))
        self.act_home.setIcon(theme.tool_icon("home"))
        self.act_open.setIcon(theme.tool_icon("open"))
        # Screenshot and theme are drawn in the primary colour (orange tiles in the Ember themes).
        self.act_screenshot.setIcon(theme.tool_icon("screenshot", warm=True))
        self.act_export_stl.setIcon(theme.tool_icon("export", on_accent=theme.filled_view_buttons(), gap=True))
        self.theme_btn.setIcon(theme.tool_icon("theme", warm=True))
        self.recent_menu.setIcon(theme.tool_icon("recent"))
        self.act_settings.setIcon(theme.tool_icon("settings"))
        self.act_updates.setIcon(theme.tool_icon("updates"))
        self.act_about.setIcon(theme.tool_icon("about"))
        self.act_whats_new.setIcon(theme.tool_icon("whats_new"))
        # Plate, View and Measure; the buttons of the View and Measure sections.
        filled = theme.filled_view_buttons()
        self.act_bed.setIcon(theme.tool_icon("plate", on_accent=filled, gap=True))
        self.act_view.setIcon(theme.tool_icon("view", on_accent=filled, gap=True))
        self.act_check.setIcon(theme.tool_icon("check", on_accent=filled, gap=True))
        self.act_fit.setIcon(theme.tool_icon("fit", on_accent=filled, gap=True))
        self.act_measure.setIcon(theme.tool_icon("measure", on_accent=filled, gap=True))
        for kind, a in self.measure_actions.items():
            a.setIcon(theme.tool_icon(kind, gap=True))
        for a, kind in ((self.act_wireframe, "wireframe"), (self.act_xray, "xray"), (self.act_clip, "clip_top"),
                        (self.act_clip_face, "clip_face"), (self.act_reset_view, "reset")):
            a.setIcon(theme.tool_icon(kind, gap=True))

    def _build_preview_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.addStretch(1)
        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignCenter)
        v.addWidget(self.preview_image)
        self.preview_title = QLabel()
        self.preview_title.setAlignment(Qt.AlignCenter)
        self.preview_title.setStyleSheet("font-size: 17px; font-weight: 600; margin-top: 10px;")
        v.addWidget(self.preview_title)
        self.preview_text = QLabel()
        self.preview_text.setObjectName("muted")
        self.preview_text.setAlignment(Qt.AlignCenter)
        self.preview_text.setWordWrap(True)
        self.preview_text.setFixedWidth(520)          # fixed width: word wrap gets its full height
        v.addWidget(self.preview_text, 0, Qt.AlignHCenter)
        v.addSpacing(8)
        row = QHBoxLayout()
        row.addStretch(1)
        self.preview_download = QPushButton()
        self.preview_download.setObjectName("primary")
        self.preview_download.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.freecad.org/downloads.php")))
        row.addWidget(self.preview_download)
        self.preview_choose = QPushButton()
        self.preview_choose.clicked.connect(self.open_settings)
        row.addWidget(self.preview_choose)
        row.addStretch(1)
        v.addLayout(row)
        v.addStretch(2)
        return page

    def _show_freecad_preview(self, m: ModelData):
        pm = QPixmap()
        if m.thumbnail and pm.loadFromData(m.thumbnail) and not pm.isNull():
            self.preview_image.setPixmap(pm.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.preview_image.show()
        else:
            self.preview_image.hide()
        status = (m.freecad or {}).get("status")
        self.preview_title.setText(tr("Preview picture") if m.thumbnail else tr("No 3D view"))
        self.preview_text.setText(self._freecad_status_text(m))
        self.preview_text.setMinimumHeight(self.preview_text.heightForWidth(520))
        no_freecad = status == "no_freecad"
        self.preview_download.setText(tr("Download FreeCAD"))
        self.preview_download.setVisible(no_freecad)
        self.preview_choose.setText(tr("Choose FreeCAD…"))
        self.preview_choose.setVisible(no_freecad or status == "failed")
        self.view_stack.setCurrentIndex(1)

    def _build_central(self):
        from pyvistaqt import QtInteractor

        self.stack = QStackedWidget()
        self.stack.setObjectName("centralStack")  # the Mica style rules name it (theme.MICA_CSS)

        # ---- welcome page ----
        welcome = QWidget()
        wl = QVBoxLayout(welcome)
        wl.addStretch(2)
        icon = QLabel()
        icon.setPixmap(QPixmap(resource("icon.png")).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon.setAlignment(Qt.AlignCenter)
        wl.addWidget(icon)
        title = QLabel(APP_NAME)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 600; margin-top: 8px;")
        wl.addWidget(title)
        self.welcome_sub = QLabel()
        self.welcome_sub.setAlignment(Qt.AlignCenter)
        self.welcome_sub.setObjectName("muted")
        wl.addWidget(self.welcome_sub)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.welcome_open = QPushButton()
        self.welcome_open.setObjectName("primary")
        self.welcome_open.setMinimumWidth(160)
        self.welcome_open.clicked.connect(self.open_dialog)
        btn_row.addWidget(self.welcome_open)
        btn_row.addStretch(1)
        wl.addSpacing(10)
        wl.addLayout(btn_row)
        self.welcome_recent = QVBoxLayout()
        self.welcome_recent.setAlignment(Qt.AlignHCenter)
        wl.addSpacing(18)
        wl.addLayout(self.welcome_recent)
        wl.addStretch(3)
        self.stack.addWidget(welcome)

        # ---- viewer page ----
        splitter = QSplitter(Qt.Horizontal)
        self.splitter = splitter
        self.plotter = QtInteractor(splitter, auto_update=False)
        try:
            for key in ("q", "b", "C", "v", "Up", "Down", "plus", "minus"):
                self.plotter.clear_events_for_key(key)
        except Exception:
            pass
        self._key_filter = _KeySwallower(self)
        self.plotter.interactor.installEventFilter(self._key_filter)
        self.scene = Scene(self.plotter)
        from .camera_controls import TurntableControls
        self.controls = TurntableControls(self.plotter, self.scene, self.scene.interaction_started,
                                          self.scene.interaction_ended)
        self.scene.bed_visible = self.act_bed.isChecked()
        self.scene.on_face_plane = lambda: self._update_clip_label()
        self.scene.show_ghost = bool(self.settings.get("clip_ghost", True))
        self.scene.show_cut_plane = bool(self.settings.get("clip_plane", True))
        self.scene.set_ghost_strength(self.settings.get("ghost_strength", 50))
        self.scene.set_plane_strength(self.settings.get("plane_strength", 50))
        self.scene.set_plate_mode(self.settings.get("plate_mode", "printer"), self._plate_size())
        # The view cube in the top-right corner (Settings -> Viewer can hide it).
        from .view_cube import ViewCube
        self.view_cube = ViewCube(self.plotter, theme.colors(), self._cube_labels())
        self.view_cube.set_visible(bool(self.settings.get("show_view_cube", True)))
        self.controls.cube = self.view_cube
        self.controls.on_cube_view = self._cube_view
        from .measure import MeasureTool
        self.measure = MeasureTool(self.plotter, self.scene, self._update_measure_panel,
                                   self.controls.request_render)
        self.measure.set_snap(True)
        self.measure.set_dotted(bool(self.settings.get("measure_dotted", False)))
        self.measure.set_deltas(bool(self.settings.get("measure_deltas", False)))
        self.measure.set_line_width(self.settings.get("measure_line_width", 4))
        self.measure.set_colors(theme.colors())
        self.measure.set_mode(self._measure_mode_setting())
        self.controls.measure = self.measure
        # Check: the analyses and their highlights (print_check.py).
        from .print_check import PrintCheck
        self.check = PrintCheck(self.plotter, self.scene, self._update_check_panel, self.controls.request_render)
        self.check.angle = float(self.settings.get("check_angle", 45) or 45)
        self.check.nozzle = float(self.settings.get("check_nozzle", 0.4) or 0.4)
        self.check.show.update({k: bool(v) for k, v in (self.settings.get("check_show", {}) or {}).items()})
        self.check.colors.update(self.settings.get("check_colors", {}) or {})
        # Instructions at the bottom of the 3D view, and the millimetre numbers on the plate's grid.
        from .grid_labels import GridLabels
        from .overlay_text import HintOverlay
        self.hints = HintOverlay(self.plotter, self.controls.request_render)
        self.hints.set_colors(theme.colors())
        self.grid_labels = GridLabels(self.plotter, self.scene, self.controls.request_render)
        self.grid_labels.set_colors(theme.colors())
        self._apply_grid_settings(render=False)
        self.grid_labels.set_enabled(bool(self.settings.get("show_grid_labels", False)))
        self.view_cube.set_tooltips(self._cube_tooltips())
        self._update_view_buttons()
        # The 3D view, or (FreeCAD file without FreeCAD) a large preview picture.
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.plotter.interactor)
        self.view_stack.addWidget(self._build_preview_page())
        splitter.addWidget(self.view_stack)

        self.side = QWidget()
        self.side_layout = QVBoxLayout(self.side)
        self.side_layout.setContentsMargins(10, 8, 10, 10)
        self.side_layout.setSpacing(10)             # room between the boxes and their titles
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.side)
        scroll.setMinimumWidth(290)
        scroll.setMaximumWidth(420)
        self.side_scroll = scroll
        self._side_width = 310                      # its width before it was dragged shut
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1000, 310])
        splitter.splitterMoved.connect(self._remember_side_width)
        self.stack.addWidget(splitter)

        self._build_side_panel()
        self.setCentralWidget(self.stack)

    def _section_button(self, action: QAction, group: list) -> QToolButton:
        """A button of the View or Measure section: the action's icon and name, lit while it is on.
        In a narrow panel the name gets a smaller font (see _FitButton)."""
        b = _FitButton(group)
        b.setObjectName("sectionButton")
        b.setIconSize(TEXT_ICON)
        b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        b.setDefaultAction(action)
        return b

    def _build_side_panel(self):
        L = self.side_layout

        # What the file is. Its name is in the window title already.
        self.kind_label = QLabel()
        self.kind_label.setObjectName("kindLabel")

        # The picture the slicer saved in the file. Next to the 3D view it mostly shows the same
        # thing, so a click on the link above it folds it away (remembered); it still helps while
        # a big file loads or when the 3D view can't show the file (issue #62).
        self.thumb_toggle = QLabel()
        self.thumb_toggle.setObjectName("moreLink")
        self.thumb_toggle.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        self.thumb_toggle.linkActivated.connect(lambda _=None: self.set_thumbnail_open(not self._thumbnail_open()))
        # The link sits on the line of the file type and size, to their right; the picture stays
        # below. In a narrow panel (a long translation) the link goes under them instead.
        self.kind_row = _FitRow([self.kind_label, self.thumb_toggle], spacing=14)
        L.addWidget(self.kind_row)
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setObjectName("thumbnail")
        L.addWidget(self.thumb_label)
        self._has_thumbnail = False

        # ZIP files: the 3D files inside, to pick one or show them all.
        # Open folder: the 3D files of the folder (see open_folder).
        self.folder_box = QGroupBox()
        self.folder_layout = QVBoxLayout(self.folder_box)
        L.addWidget(self.folder_box)
        self.folder_box.hide()

        self.zip_box = QGroupBox()
        self.zip_layout = QVBoxLayout(self.zip_box)
        L.addWidget(self.zip_box)

        # The objects come first (what you use most), the details last (something you read). A long
        # description no longer pushes the objects off the screen (#62). Each object has a colour
        # box: a click picks another colour for that object (kept until the program closes).
        self.objects_box = QGroupBox()
        box_layout = QVBoxLayout(self.objects_box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        self.objects_scroll = QScrollArea()
        self.objects_scroll.setObjectName("objectsScroll")
        self.objects_scroll.setWidgetResizable(True)
        self.objects_scroll.setFrameShape(QScrollArea.NoFrame)
        self.objects_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        objects_list = QWidget()
        objects_list.setObjectName("objectsList")
        self.objects_layout = QVBoxLayout(objects_list)
        self.objects_scroll.setWidget(objects_list)
        box_layout.addWidget(self.objects_scroll)
        self.objects_hint = _FitLabel()              # how to change an object's colour: one line
        self.objects_hint.setObjectName("muted")
        self.objects_hint.setContentsMargins(10, 0, 10, 6)
        box_layout.addWidget(self.objects_hint)
        L.addWidget(self.objects_box)

        self.embedded_box = QGroupBox()
        self.embedded_layout = QVBoxLayout(self.embedded_box)
        L.addWidget(self.embedded_box)

        # The Check button's section: what to look for and in which colour; the counts beside them.
        self.check_box = QGroupBox()
        ckl = QVBoxLayout(self.check_box)
        self.check_rows: dict = {}
        shown = dict(self.settings.get("check_show", {}) or {})
        colours = dict(self.settings.get("check_colors", {}) or {})
        from .print_check import DEFAULT_COLORS

        def check_row(kind: str, extra: Optional[QWidget] = None) -> QHBoxLayout:
            row = QHBoxLayout()
            row.setSpacing(8)
            box = _ColorButton(colours.get(kind, DEFAULT_COLORS[kind]))
            box.setToolTip(tr("Click to pick another colour (right-click: the original colour)"))
            box.clicked.connect(lambda _=False, k=kind, b=box: self._pick_check_color(k, b))
            box.customContextMenuRequested.connect(lambda _pos, k=kind, b=box: self._reset_check_color(k, b))
            cb = QCheckBox()
            cb.setChecked(bool(shown.get(kind, kind != "thin")))
            cb.toggled.connect(lambda on, k=kind: self._check_shown(k, on))
            count_lbl = QLabel()
            count_lbl.setObjectName("objectSize")
            row.addWidget(box)
            row.addWidget(cb, 1)
            if extra is not None:
                row.addWidget(extra)
            row.addWidget(count_lbl)
            self.check_rows[kind] = (cb, count_lbl, box)
            return row

        # Overhangs, with their angle
        angle_w = QWidget()
        al = QHBoxLayout(angle_w)
        al.setContentsMargins(0, 0, 0, 0)
        self.check_angle = QSpinBox()
        self.check_angle.setRange(1, 89)
        self.check_angle.setSuffix("°")
        self.check_angle.setValue(int(self.settings.get("check_angle", 45) or 45))
        self.check_angle.valueChanged.connect(self._check_angle_changed)
        self.check_angle_label = QLabel()
        self.check_angle_label.setObjectName("muted")
        al.addWidget(self.check_angle)
        al.addWidget(self.check_angle_label)
        ckl.addLayout(check_row("overhang", angle_w))
        # Thin walls, with the nozzle width (in the unit in use)
        from .length_spin import LengthSpin
        nozzle_w = QWidget()
        nl = QHBoxLayout(nozzle_w)
        nl.setContentsMargins(0, 0, 0, 0)
        self.check_nozzle_label = QLabel()
        self.check_nozzle_label.setObjectName("muted")
        self.check_nozzle = LengthSpin(0.1, 2.0, 0.05, mm_decimals=2, in_step=0.002, in_decimals=3)
        self.check_nozzle.set_mm(float(self.settings.get("check_nozzle", 0.4) or 0.4))
        self.check_nozzle.editingFinished.connect(self._check_nozzle_changed)
        nl.addWidget(self.check_nozzle_label)
        nl.addWidget(self.check_nozzle)
        ckl.addLayout(check_row("thin", nozzle_w))
        self.check_thin_status = QLabel()            # "Checking ... 40 %"
        self.check_thin_status.setObjectName("muted")
        ckl.addWidget(self.check_thin_status)
        # The mesh check
        self.check_mesh_title = QLabel()
        self.check_mesh_title.setObjectName("formKey")
        ckl.addWidget(self.check_mesh_title)
        for kind in ("open", "nonmanifold", "flipped", "loose"):
            ckl.addLayout(check_row(kind))
        crow = QHBoxLayout()
        self.check_close_btn = QPushButton()
        self.check_close_btn.clicked.connect(lambda: self.act_check.setChecked(False))
        crow.addStretch(1)
        crow.addWidget(self.check_close_btn)
        ckl.addLayout(crow)
        self.check_box.hide()
        L.addWidget(self.check_box)

        # The View button's section: how the model is drawn and cut, all as buttons. The controls of
        # a cut (its slider, the ghost and the plane) appear in it while that cut is on.
        self.view_box = QGroupBox()
        vl = QVBoxLayout(self.view_box)
        vg = QGridLayout()
        vg.setSpacing(6)
        view_group: list = []                     # these buttons shrink together in a narrow panel
        for i, act in enumerate((self.act_wireframe, self.act_xray, self.act_clip, self.act_clip_face)):
            vg.addWidget(self._section_button(act, view_group), i // 2, i % 2)
        vl.addLayout(vg)

        # View -> Clip (issues #60, #70): a row per cut, shown while that cut is on: the height of
        # Clip from the top and the depth of Clip facing you. Both can be on together. Like the
        # layer slider the sliders always run left-to-right.
        self.clip_box = QWidget()
        cl = QVBoxLayout(self.clip_box)
        cl.setContentsMargins(0, 0, 0, 0)
        self.clip_top_row = QWidget()
        tl = QVBoxLayout(self.clip_top_row)
        tl.setContentsMargins(0, 0, 0, 0)
        self.clip_info = QLabel()                 # Height … of … mm
        tl.addWidget(self.clip_info)
        self.clip_slider = QSlider(Qt.Horizontal)
        self.clip_slider.setLayoutDirection(Qt.LeftToRight)
        self.clip_slider.setRange(0, self.CLIP_STEPS)
        self.clip_slider.setValue(self.CLIP_STEPS // 2)
        self.clip_slider.valueChanged.connect(self._on_clip_changed)
        tl.addWidget(self.clip_slider)
        cl.addWidget(self.clip_top_row)
        self.clip_face_row = QWidget()
        fl = QVBoxLayout(self.clip_face_row)
        fl.setContentsMargins(0, 0, 0, 0)
        self.face_info = QLabel()                 # Depth … of … mm
        fl.addWidget(self.face_info)
        self.face_slider = QSlider(Qt.Horizontal)
        self.face_slider.setLayoutDirection(Qt.LeftToRight)
        self.face_slider.setRange(0, self.CLIP_STEPS)
        self.face_slider.setValue(self.CLIP_STEPS // 2)
        self.face_slider.valueChanged.connect(self._on_face_changed)
        fl.addWidget(self.face_slider)
        cl.addWidget(self.clip_face_row)
        # What the cut hides, as a see-through ghost, and the cutting plane, each on its own (#66).
        # Here, under the slider, where you look while cutting (3D Builder's Split puts it there
        # too). How strong both are drawn is in Settings -> Viewer.
        self.clip_ghost_cb = QCheckBox()
        self.clip_ghost_cb.setChecked(bool(self.settings.get("clip_ghost", True)))
        self.clip_ghost_cb.toggled.connect(self.set_clip_ghost)
        cl.addWidget(self.clip_ghost_cb)
        self.clip_plane_cb = QCheckBox()
        self.clip_plane_cb.setChecked(bool(self.settings.get("clip_plane", True)))
        self.clip_plane_cb.toggled.connect(self.set_clip_plane)
        cl.addWidget(self.clip_plane_cb)
        # Freezes the "Clip facing you" cut where it is, so you can turn and move the model
        # without the cut turning along (Clip from the top never moves).
        self.view_freeze_cb = QCheckBox()
        self.view_freeze_cb.toggled.connect(self.set_cut_frozen)
        cl.addWidget(self.view_freeze_cb)
        self.clip_box.hide()
        vl.addWidget(self.clip_box)

        vrow = QHBoxLayout()
        self.view_reset_btn = QPushButton()
        self.view_reset_btn.clicked.connect(self.reset_view)
        self.view_close_btn = QPushButton()
        self.view_close_btn.clicked.connect(lambda: self.act_view.setChecked(False))
        vrow.addStretch(1)
        vrow.addWidget(self.view_reset_btn)
        vrow.addWidget(self.view_close_btn)
        vl.addLayout(vrow)
        self.view_box.hide()
        L.addWidget(self.view_box)

        # The Measure button's section: what to measure, and how. The values themselves are
        # written next to the measurements in the 3D view.
        self.measure_box = QGroupBox()
        ml = QVBoxLayout(self.measure_box)
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_group: list = []
        for kind in ("distance", "angle", "circle"):
            mode_row.addWidget(self._section_button(self.measure_actions[kind], mode_group))
        ml.addLayout(mode_row)
        # Snapping is on at every start (a choice made last time is not kept: with it off, clicks
        # land beside the corners you mean).
        self.measure_snap_cb = QCheckBox()
        self.measure_snap_cb.setChecked(True)
        self.measure_snap_cb.toggled.connect(self.set_measure_snap)
        self.measure_dotted_cb = QCheckBox()
        self.measure_dotted_cb.setChecked(bool(self.settings.get("measure_dotted", False)))
        self.measure_dotted_cb.toggled.connect(self.set_measure_dotted)
        self.measure_deltas_cb = QCheckBox()
        self.measure_deltas_cb.setChecked(bool(self.settings.get("measure_deltas", False)))
        self.measure_deltas_cb.toggled.connect(self.set_measure_deltas)
        # Side by side while they fit, one under the other in a narrow panel.
        self.measure_opts = _FitRow([self.measure_snap_cb, self.measure_dotted_cb, self.measure_deltas_cb])
        ml.addWidget(self.measure_opts)
        mrow = QHBoxLayout()
        self.measure_clear_btn = QPushButton()
        self.measure_clear_btn.clicked.connect(self._measure_clear)
        self.measure_close_btn = QPushButton()
        self.measure_close_btn.clicked.connect(lambda: self.act_measure.setChecked(False))
        mrow.addStretch(1)
        mrow.addWidget(self.measure_clear_btn)
        mrow.addWidget(self.measure_close_btn)
        ml.addLayout(mrow)
        self.measure_box.hide()
        L.addWidget(self.measure_box)

        self.layers_box = QGroupBox()
        ll = QVBoxLayout(self.layers_box)
        self.layer_info = QLabel()
        ll.addWidget(self.layer_info)
        # The layer slider always runs left-to-right (layer 1 on the left), also in
        # right-to-left languages, matching the Western layer numbers.
        srow_widget = QWidget()
        srow_widget.setLayoutDirection(Qt.LeftToRight)
        srow = QHBoxLayout(srow_widget)
        srow.setContentsMargins(0, 0, 0, 0)
        self.layer_down = QPushButton()
        self.layer_down.setFixedWidth(34)
        self.layer_down.clicked.connect(lambda: self.step_layer(-1))
        self.layer_slider = QSlider(Qt.Horizontal)
        self.layer_slider.valueChanged.connect(self._on_layer_changed)
        self.layer_up = QPushButton()
        self.layer_up.setFixedWidth(34)
        self.layer_up.clicked.connect(lambda: self.step_layer(1))
        srow.addWidget(self.layer_down)
        srow.addWidget(self.layer_slider, 1)
        srow.addWidget(self.layer_up)
        ll.addWidget(srow_widget)
        row2 = QHBoxLayout()
        self.layer_spin = QSpinBox()
        self.layer_spin.valueChanged.connect(lambda v: self.layer_slider.setValue(v - 1))
        self.goto_label = QLabel()
        row2.addWidget(self.goto_label)
        row2.addWidget(self.layer_spin)
        row2.addStretch(1)
        ll.addLayout(row2)
        self.only_layer_cb = QCheckBox()
        self.only_layer_cb.toggled.connect(self._schedule_gcode)
        ll.addWidget(self.only_layer_cb)
        self.layer_hint = QLabel()
        self.layer_hint.setObjectName("muted")
        self.layer_hint.setWordWrap(True)
        ll.addWidget(self.layer_hint)
        L.addWidget(self.layers_box)

        self.features_box = QGroupBox()
        self.features_layout = QVBoxLayout(self.features_box)
        L.addWidget(self.features_box)
        self.feature_checks: dict[str, QCheckBox] = {}

        # The details, last, and foldable (the choice is remembered): a click on the heading.
        self.details_box = QGroupBox()
        dl = QVBoxLayout(self.details_box)
        self.details_toggle = QLabel()
        self.details_toggle.setObjectName("moreLink")
        self.details_toggle.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        self.details_toggle.linkActivated.connect(lambda _=None: self.set_details_open(not self._details_open()))
        dl.addWidget(self.details_toggle)
        self.details_body = QWidget()
        self.details_form = QFormLayout(self.details_body)
        self.details_form.setContentsMargins(0, 0, 0, 0)
        # Side by side, a row needs its name AND its value next to each other: with a compound
        # word ("Filamentprofiel") and an unbreakable value, or a bigger font (Windows display
        # scaling), that made the panel wider than its view. A row that doesn't fit puts the
        # value under its name instead; rows that fit stay side by side.
        self.details_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        dl.addWidget(self.details_body)
        L.addWidget(self.details_box)

        L.addStretch(1)
        self._reset_side_panel()

    def _build_statusbar(self):
        sb = self.statusBar()
        sb.setObjectName("mainStatusBar")        # the Mica style rules name it (theme.MICA_CSS)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.hide()
        sb.addPermanentWidget(self.progress)
        # Version in the corner; a red dot and the new version when an update exists.
        self.version_badge = QLabel()
        self.version_badge.setObjectName("versionBadge")
        self.version_badge.setTextFormat(Qt.RichText)
        self.version_badge.linkActivated.connect(lambda _l: self.open_settings("updates"))
        sb.addPermanentWidget(self.version_badge)

    def _build_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self.open_in_slicer)
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self.next_theme)
        QShortcut(QKeySequence("Ctrl+Shift+T"), self, activated=self.toggle_light_dark)
        for act, key, _ in self.view_actions:
            QShortcut(QKeySequence(key), self, activated=act.trigger)
        # Up/Down: layers of a G-code; in a ZIP list showing a model, the previous/next file.
        QShortcut(QKeySequence(Qt.Key_Up), self, activated=lambda: self._arrow_key(1))
        QShortcut(QKeySequence(Qt.Key_Down), self, activated=lambda: self._arrow_key(-1))
        QShortcut(QKeySequence(Qt.Key_PageUp), self, activated=lambda: self.step_layer(10))
        QShortcut(QKeySequence(Qt.Key_PageDown), self, activated=lambda: self.step_layer(-10))
        QShortcut(QKeySequence(Qt.Key_Home), self, activated=lambda: self.set_layer(0))
        QShortcut(QKeySequence(Qt.Key_End), self, activated=lambda: self.set_layer(10 ** 9))

    # ========================================================= language
    def retranslate_ui(self):
        """(Re)set every fixed text. Called at start and when the language changes."""
        self.act_open.setText(tr("Open…"))
        self.act_open_folder.setText(tr("Open folder…"))
        self.act_open_folder.setIcon(theme.tool_icon("open"))
        # The shortcut as the system writes it (Ctrl+O, or ⌘O on a Mac).
        self.act_open.setToolTip(tr("Open…") + " (" + QKeySequence(QKeySequence.Open).toString(
            QKeySequence.NativeText) + ")")
        self.menu_btn.setToolTip(tr("Menu"))
        self.act_home.setText(tr("Home"))
        self.act_home.setToolTip(tr("Close the file and go back to the start page ({key})").format(
            key=self.act_home.shortcut().toString(QKeySequence.NativeText)))
        self.recent_menu.setTitle(tr("Recent"))
        view_names = {None: tr("Fit"), "iso": tr("Iso"), "top": tr("Top"),
                      "front": tr("Front"), "right": tr("Right")}
        for act, key, view in self.view_actions:
            act.setText(view_names[view])
            act.setToolTip(tr("{view} view ({key})").format(view=view_names[view], key=key))
        if hasattr(self, "view_cube"):
            self.view_cube.set_labels(self._cube_labels())
            self.view_cube.set_tooltips(self._cube_tooltips())
        self.act_export_stl.setText(tr("Export STL"))
        self.act_export_stl.setToolTip(tr("Save the objects of this CAD file as STL files (Ctrl+E)")
                                       if getattr(self, "current_kind", "") in ("freecad", "step") else
                                       tr("Save the objects of this 3MF project as STL files (Ctrl+E)"))
        self.act_export_one.setText(tr("All objects as one STL"))
        self.act_export_each.setText(tr("One STL per object"))
        self.act_export_choose.setText(tr("Choose objects…"))
        self.act_export_setting.setText(tr("Change what a click does…"))
        self.act_bed.setText(tr("Plate"))
        self.act_bed.setToolTip(tr("Show / hide the build plate grid (arrow: plate size)"))
        self.act_check.setText(tr("Check"))
        self.act_check.setToolTip(tr("Check the model before printing: overhangs, thin walls and problems in the mesh"))
        self.check_box.setTitle(tr("Check"))
        self.check_angle_label.setText(tr("from vertical"))
        self.check_nozzle_label.setText(tr("nozzle"))
        self.check_mesh_title.setText(tr("Mesh"))
        self.check_close_btn.setText(tr("Close"))
        for kind, text, tip in (
                ("overhang", tr("Overhangs"), tr("Faces that face down and lean further from vertical than the angle: "
                                                  "they usually need supports. Faces on the plate are not counted.")),
                ("thin", tr("Thin walls"), tr("Walls and pins thinner than the nozzle: one line of plastic or less.")),
                ("open", tr("Open edges"), tr("Edges with a face on one side only: holes in the surface.")),
                ("nonmanifold", tr("Non-manifold edges"), tr("Edges shared by more than two faces.")),
                ("flipped", tr("Flipped normals"), tr("Faces turned the other way than their neighbours, or a closed "
                                                     "part that is inside out.")),
                ("loose", tr("Loose parts"), tr("Pieces not connected to the biggest one."))):
            cb = self.check_rows[kind][0]
            cb.setText(text)
            cb.setToolTip(tip)
        self._update_check_panel()
        self.act_view.setText(tr("View"))
        self.act_view.setToolTip(tr("How the model is drawn: wireframe, X-ray, clip"))
        self.view_box.setTitle(tr("View"))
        # The buttons of the View section are short; the tooltip says it in full.
        self.act_reset_view.setText(tr("Reset view"))
        for act, text, tip, key in ((self.act_wireframe, tr("Wireframe"), tr("Wireframe"), "W"),
                                    (self.act_xray, tr("X-ray"), tr("X-ray (see-through)"), "X"),
                                    (self.act_clip, tr("Clip from the top"), tr("Clip from the top"), "C"),
                                    (self.act_clip_face, tr("Clip facing you"), tr("Clip facing you"), "V"),
                                    (self.act_reset_view, tr("Reset view"), tr("Reset view"), "R")):
            act.setText(text)
            act.setToolTip(tip + " (" + key + ")")
        self.view_reset_btn.setText(tr("Reset view"))
        self.view_reset_btn.setToolTip(tr("Reset view") + " (R)")
        self.view_close_btn.setText(tr("Close"))
        self.view_freeze_cb.setText(tr("Freeze the cutting plane"))
        self.view_freeze_cb.setToolTip(tr("Keeps the cut of Clip facing you where it is, so you can turn and "
                                          "move the model without the cut turning along."))
        self._retitle_clip_box()
        self.clip_ghost_cb.setText(tr("Show the cut-away part"))
        self.clip_ghost_cb.setToolTip(tr("Shows what the cut hides as a see-through ghost."))
        self.clip_plane_cb.setText(tr("Show the cutting plane"))
        self.clip_plane_cb.setToolTip(tr("Shows where the cut is, as a faint sheet the size of the model."))
        self.act_measure.setText(tr("Measure"))
        self.act_measure.setToolTip(tr("Measure on the model: distance, angle, circle") + " (M)")
        self.measure_box.setTitle(tr("Measure"))
        for kind, a in self.measure_actions.items():
            a.setText(self._measure_mode_label(kind))
            a.setToolTip(self._measure_mode_tip(kind))
        self.objects_hint.setText(tr("Click a colour box to change its colour."))
        self.measure_snap_cb.setText(tr("Snapping"))
        self.measure_snap_cb.setToolTip(tr("Jumps to the nearest corner, the middle of an edge or a point on an "
                                           "edge of the model when the mouse is close to one."))
        self.measure_dotted_cb.setText(tr("Dotted line"))
        self.measure_dotted_cb.setToolTip(tr("Draws the measuring lines dotted."))
        self.measure_deltas_cb.setText(tr("Show ΔX ΔY ΔZ"))
        self.measure_deltas_cb.setToolTip(tr("Writes the distance along X, Y and Z under the value of every "
                                             "distance."))
        self.measure_clear_btn.setText(tr("Clear"))
        self.measure_close_btn.setText(tr("Close"))
        self._update_measure_panel()
        self._update_clip_label()
        self._mark_plate_mode()
        self.act_screenshot.setText(tr("Screenshot"))
        self.act_settings.setText(tr("Settings"))
        self.act_updates.setText(tr("Updates"))
        self.act_about.setText(tr("About"))
        self.act_whats_new.setText(tr("What's new"))
        self._update_theme_button()
        self.refresh_update_badge()

        self.welcome_sub.setText(tr("Drop a 3D model or G-code file here, or open one."))
        self.welcome_open.setText(tr("Open file…"))

        self._update_details_toggle()
        self.embedded_box.setTitle(tr("Project") if self.showing_embedded else tr("Sliced plates"))
        self.layers_box.setTitle(tr("Layers"))
        self.features_box.setTitle(tr("Features"))
        self.goto_label.setText(tr("Go to layer"))
        self.only_layer_cb.setText(tr("Show only this layer"))
        self.layer_hint.setText(tr("Tip: ↑ / ↓ arrow keys move through layers"))
        self.layer_down.setText("◀")
        self.layer_up.setText("▶")
        self.layer_down.setToolTip(tr("Previous layer"))
        self.layer_up.setToolTip(tr("Next layer"))

        self._refresh_recent_menu()
        self._update_slicer_button()
        self._update_layer_label()
        self._update_side_min_width()

    def changeEvent(self, e):
        if e.type() in (QEvent.LanguageChange, QEvent.LayoutDirectionChange):
            self._retranslate_timer.start()
        super().changeEvent(e)

    def _on_language_changed(self):
        self.retranslate_ui()
        self._refresh_panel()
        # A splitter does not re-place its panes on its own when the direction changes
        # (Arabic puts the information panel on the left).
        sizes = self.splitter.sizes()
        self.splitter.refresh()
        self.splitter.setSizes(sizes)

    # ========================================================= side panel
    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()            # hide now; Qt deletes it later
                w.deleteLater()
            elif item.layout() is not None:
                MainWindow._clear_layout(item.layout())

    def _reset_side_panel(self):
        self.kind_label.setText("")
        self._show_thumbnail(False)
        while self.details_form.rowCount():
            self.details_form.removeRow(0)
        self._clear_layout(self.zip_layout)
        self._clear_layout(self.objects_layout)
        self._clear_layout(self.embedded_layout)
        self._clear_layout(self.features_layout)
        self.feature_checks = {}
        for box in (self.zip_box, self.objects_box, self.embedded_box, self.layers_box, self.features_box):
            box.hide()

    def _refresh_panel(self):
        """Rebuild the information panel in the current language, keeping all settings."""
        if self.stack.currentIndex() != 1:
            return
        if self.gcode is not None:
            checks = {k: cb.isChecked() for k, cb in self.feature_checks.items()}
            layer = self.layer_slider.value()
            only = self.only_layer_cb.isChecked()
            self._reset_side_panel()
            self._fill_gcode_panel(self.gcode)
            for k, on in checks.items():
                if k in self.feature_checks:
                    self.feature_checks[k].blockSignals(True)
                    self.feature_checks[k].setChecked(on)
                    self.feature_checks[k].blockSignals(False)
            self.layer_slider.setValue(layer)
            self.only_layer_cb.setChecked(only)
            self._update_layer_label()
            self._schedule_gcode()
        elif self.model is not None:
            self._reset_side_panel()
            self._fill_model_panel(self.model)
            if self.view_stack.currentIndex() == 1:
                self._show_freecad_preview(self.model)
        self._fill_zip_box()
        self._fill_folder_box()

    def _details_open(self) -> bool:
        return bool(self.settings.get("details_open", True))

    def set_details_open(self, on: bool):
        """Fold the Details away or show them again; remembered for the next start."""
        self.settings.set("details_open", bool(on))
        self._update_details_toggle()

    def _update_details_toggle(self):
        is_open = self._details_open()
        closed = "◂" if self.layoutDirection() == Qt.RightToLeft else "▸"
        self.details_toggle.setText('<a href="#">{} {}</a>'.format("▾" if is_open else closed, tr("Details")))
        self.details_toggle.setToolTip(tr("Show less") if is_open else tr("Show more"))
        self.details_body.setVisible(is_open)

    def _add_detail(self, key: str, value: str):
        k = QLabel(key)
        k.setObjectName("formKey")
        # Field names may wrap: a long one (Arabic "ملف تعريف الخيط (الفلمنت)") next to a value
        # that can't wrap (BambuStudio-02.03.00.70) made the panel wider than its view, and in
        # right-to-left the overflow was cut off on the left.
        k.setWordWrap(True)
        text = str(value)
        if len(text) > self.LONG_DETAIL_CHARS or "\n" in text:
            self.details_form.addRow(k, _LongValue(text))
            return
        v = QLabel(_breakable(text))
        v.setWordWrap(True)
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.details_form.addRow(k, v)

    # Values longer than this (or with line breaks) start folded to their first lines.
    LONG_DETAIL_CHARS = 160
    # More objects than this: the Objects list scrolls on its own, so Details stays in reach.
    OBJECTS_VISIBLE_ROWS = 10

    def _fit_objects_list(self):
        """Show the Objects list in full up to OBJECTS_VISIBLE_ROWS objects, longer lists
        scroll inside the box."""
        n = self.objects_layout.count()
        inner = self.objects_scroll.widget()
        if n <= self.OBJECTS_VISIBLE_ROWS:
            self.objects_scroll.setFixedHeight(inner.sizeHint().height())
            self.objects_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            return
        row = self.objects_layout.itemAt(0).widget().sizeHint().height() + self.objects_layout.spacing()
        m = self.objects_layout.contentsMargins()
        self.objects_scroll.setFixedHeight(row * self.OBJECTS_VISIBLE_ROWS + m.top())
        self.objects_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _set_thumbnail(self, data: Optional[bytes]):
        pm = QPixmap()
        if data and pm.loadFromData(data) and not pm.isNull() and pm.width() > 8:
            self.thumb_label.setPixmap(pm.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self._show_thumbnail(True)
        else:
            self._show_thumbnail(False)

    def _thumbnail_open(self) -> bool:
        return bool(self.settings.get("thumbnail_open", True))

    def set_thumbnail_open(self, on: bool):
        """Fold the preview picture away or show it again; remembered for the next files."""
        self.settings.set("thumbnail_open", bool(on))
        self._show_thumbnail(self._has_thumbnail)

    def _show_thumbnail(self, has: bool):
        """`has`: this file has a preview picture. The link is shown with it, the picture only
        when it isn't folded away."""
        self._has_thumbnail = has
        is_open = self._thumbnail_open()
        # ▸ points to where the text goes: to the left in right-to-left languages such as Arabic.
        closed = "◂" if self.layoutDirection() == Qt.RightToLeft else "▸"
        self.thumb_toggle.setText('<a href="#">{} {}</a>'.format("▾" if is_open else closed,
                                                                 tr("Preview picture")))
        self.thumb_toggle.setToolTip(tr("Show less") if is_open else tr("Show more"))
        self.thumb_toggle.setVisible(has)
        self.thumb_label.setVisible(has and is_open)

    def _kind_text(self) -> str:
        if self.showing_embedded:
            return tr("Sliced toolpaths · {plate}").format(plate=_plate_name(self._embedded_member))
        names = {"stl": "STL", "3mf": "3MF", "obj": "OBJ", "ply": "PLY", "off": "OFF", "gltf": "glTF",
                 "gcode": tr("G-code"), "freecad": "FreeCAD", "step": "STEP", "zip": "ZIP"}
        return tr("Filetype: {kind}  ·  Size: {size}").format(
            kind=names.get(self.current_kind, self.current_kind.upper()),
            size=self._size_text(self._file_size_mb * 1024 * 1024))

    @staticmethod
    def _size_text(nbytes: float) -> str:
        """A file size in KB, or MB from a megabyte up: 0.35 KB, 12.4 KB, 350 KB, 1.2 MB."""
        if nbytes < 1024 * 1024:
            kb = nbytes / 1024
            return tr("{n} KB").format(n=num(kb, 2 if kb < 10 else 1 if kb < 100 else 0))
        mb = nbytes / (1024 * 1024)
        return tr("{n} MB").format(n=num(mb, 2 if mb < 10 else 1))

    # ================================================================ ZIP
    def _display_name(self) -> str:
        """Name of what is shown: the ZIP (Show all), the file inside the ZIP, or the file."""
        if self.zip and self.current_kind == "zip":
            return os.path.basename(self.zip.path)
        if self.zip and 0 <= self._zip_index < len(self.zip.entries):
            return self.zip.entries[self._zip_index].name
        return os.path.basename(self.current_path or "")

    def _user_folder(self) -> str:
        """Where the user's file is (for dialogs): the ZIP's folder, never the unpack cache."""
        if self.zip:
            return os.path.dirname(self.zip.path)
        return os.path.dirname(self.current_path or "") or os.path.expanduser("~")

    def _zip_of(self, path: str) -> tuple:
        """(ZIP, index) when `path` is a file unpacked from the open ZIP (e.g. opened again
        after viewing its sliced plates), otherwise (None, 0)."""
        if self.zip:
            for i, e in enumerate(self.zip.entries):
                if os.path.normcase(e.path) == os.path.normcase(path):
                    return self.zip, i
        return None, 0

    def _add_zip_detail(self):
        if self.zip and self.current_kind != "zip":
            self._add_detail(tr("From ZIP"), os.path.basename(self.zip.path))

    def _load_archive(self, path: str):
        self._load_token += 1
        token = self._load_token
        self.statusBar().showMessage(tr("Opening {name}…").format(name=os.path.basename(path)))
        self.progress.setValue(0)
        self.progress.show()
        self.slicer_btn.setEnabled(False)

        def work():
            try:
                c = za.open_archive(path, lambda f: self._signals.progress.emit(token, f))
                self._signals.done.emit(token, ("__zip__", c))
            except za.ArchiveError as e:
                self._signals.failed.emit(token, str(e))
            except Exception as e:  # noqa: BLE001 - show any error to the user
                self._signals.failed.emit(token, f"{type(e).__name__}: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _on_archive_ready(self, contents: za.ZipContents, sync: bool = False):
        self.progress.hide()
        self.slicer_btn.setEnabled(True)
        self.statusBar().clearMessage()
        if not contents.entries:
            QMessageBox.information(
                self, tr("No 3D files in this ZIP"),
                tr("This ZIP contains no files PrintView3D can open "
                   "(STL, 3MF, OBJ, PLY, OFF, glTF, STEP, FreeCAD or G-code)."))
            return
        # One 3D file: it simply opens, like the file itself. More: the first one, with the list.
        self._open_zip_entry(0, contents, sync)

    def _open_zip_entry(self, i: int, contents: Optional[za.ZipContents] = None, sync: bool = False):
        c = contents or self.zip
        if c is None or not 0 <= i < len(c.entries):
            return
        self._zip_wanted = i
        (self.load_sync if sync else self.load)(c.entries[i].path, c, i)

    def zip_show_all(self, sync: bool = False):
        """Show all models of the ZIP side by side (STL, 3MF, OBJ, PLY, OFF, glTF)."""
        c = self.zip
        if c is None or len(c.arrangeable) < 2:
            return
        todo = [(i, e) for i, e in enumerate(c.entries) if e.kind in za.ARRANGEABLE]
        self._load_token += 1
        token = self._load_token

        def build():
            models, index = [], []
            for k, (i, e) in enumerate(todo):
                m = load_file(e.path, lambda f, k=k: self._signals.progress.emit(token, (k + f) / len(todo)))
                if m.parts:
                    models.append((e.name, m))
                    index.append(i)
            merged, owner = za.arrange(models)
            return ("__zipall__", c, (merged, [index[o] for o in owner]))

        if sync:
            self._on_loaded(token, build())
            return
        self.statusBar().showMessage(tr("Placing {n} models side by side…").format(n=len(todo)))
        self.progress.setValue(0)
        self.progress.show()
        self.slicer_btn.setEnabled(False)

        def work():
            try:
                self._signals.done.emit(token, build())
            except Exception as e:  # noqa: BLE001
                self._signals.failed.emit(token, f"{type(e).__name__}: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _toggle_show_all(self):
        if self.current_kind == "zip":
            self._open_zip_entry(self._zip_last_single)
        else:
            self.zip_show_all()

    def _arrow_key(self, delta: int):
        """Up/Down: the previous/next file of a ZIP while a model is shown, else of the open
        folder; with G-code the layers."""
        c = self.zip
        if c and len(c.entries) > 1 and self._zip_index >= 0 and self.gcode is None:
            i = self._zip_wanted - delta                # Up = the file above in the list
            if 0 <= i < len(c.entries):
                self._open_zip_entry(i)
            return
        if self.folder and len(self.folder["files"]) > 1 and self.gcode is None:
            i = self._folder_index - delta
            if 0 <= i < len(self.folder["files"]):
                self._open_folder_entry(i)
            return
        self.step_layer(delta)

    # ------------------------------------------------------------ folder
    def open_folder_dialog(self):
        start = self._user_folder() if self.current_path else os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, tr("Open folder"), start)
        if path:
            self.open_folder(path)

    @staticmethod
    def folder_files(path: str) -> list:
        """The files PrintView3D can open in a folder (not its subfolders), by name."""
        try:
            names = os.listdir(path)
        except OSError:
            return []
        ok = SUPPORTED_EXTENSIONS + za.ARCHIVE_EXTENSIONS
        files = [os.path.join(path, n) for n in names
                 if n.lower().endswith(ok) and os.path.isfile(os.path.join(path, n))]
        return sorted(files, key=lambda f: os.path.basename(f).lower())

    def open_folder(self, path: str, sync: bool = False):
        """Menu -> Open folder: list the folder's 3D files in the side panel and open the first.
        Up / Down (or a click in the list) open the others."""
        files = self.folder_files(path)
        if not files:
            QMessageBox.information(self, tr("No 3D files in this folder"),
                                    tr("This folder contains no files PrintView3D can open."))
            return
        self.folder = {"path": os.path.abspath(path), "files": files}
        self._open_folder_entry(0, sync)

    def _open_folder_entry(self, i: int, sync: bool = False):
        if not self.folder or not 0 <= i < len(self.folder["files"]):
            return
        self._folder_index = i
        self._folder_loading = True
        try:
            (self.load_sync if sync else self.load)(self.folder["files"][i])
        finally:
            self._folder_loading = False

    def _folder_of(self, path: str) -> bool:
        """Is `path` one of the open folder's files? (Then the folder stays; otherwise it goes.)"""
        if not self.folder:
            return False
        norm = os.path.normcase(os.path.abspath(path))
        for i, f in enumerate(self.folder["files"]):
            if os.path.normcase(f) == norm:
                self._folder_index = i
                return True
        return False

    def _fill_folder_box(self):
        self._clear_layout(self.folder_layout)
        f = self.folder
        if not f:
            self.folder_box.hide()
            return
        self.folder_box.setTitle(tr("In this folder ({n})").format(n=len(f["files"])))
        lst = _RowList()
        lst.setObjectName("zipList")
        lst.setSelectionMode(QAbstractItemView.SingleSelection)
        lst.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        row_h = self.fontMetrics().height() + 16
        for path in f["files"]:
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(6, 0, 8, 0)
            h.setSpacing(8)
            kind = "zip" if za.is_archive(path) else (file_kind(path) or "")
            h.addWidget(self._type_tag(kind))
            name = _ElidedLabel(os.path.basename(path))
            name.setToolTip(path)
            h.addWidget(name, 1)
            try:
                size = QLabel(_size_text(os.path.getsize(path)))
            except OSError:
                size = QLabel("")
            size.setObjectName("muted")
            size.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            h.addWidget(size)
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, row_h))
            lst.addItem(item)
            lst.setItemWidget(item, w)
        lst.setCurrentRow(self._folder_index)
        lst.setFixedHeight(row_h * min(len(f["files"]), 8) + 2 * lst.frameWidth() + 2)
        lst.itemClicked.connect(lambda item, l=lst: self._open_folder_entry(l.row(item))
                                if l.row(item) != self._folder_index else None)
        self.folder_layout.addWidget(lst)
        note = QLabel(tr("Tip: ↑ / ↓ keys move through the list"))
        note.setObjectName("muted")
        note.setStyleSheet("font-size: 11px;")
        self.folder_layout.addWidget(note)
        self.folder_list = lst
        self.folder_box.show()

    def _show_all_entries(self) -> list[int]:
        """Show all: the ZIP entries of the ticked models (all of them when none is ticked)."""
        actors = getattr(self, "_model_actors", [])
        owners = [o for o, a in zip(self._zip_owner, actors) if a.GetVisibility()] or list(self._zip_owner)
        return list(dict.fromkeys(owners))              # in list order, each once

    def _files_to_send(self, indices: list[int]) -> Optional[list]:
        """The files a slicer gets for these ZIP entries, or None when the user cancels.
        A 3MF together with other files needs a choice (see send_dialog). Formats not every
        slicer reads (PLY, OFF, glTF) are sent as STL."""
        c = self.zip
        if c is None or not indices:
            return None
        entries = [c.entries[i] for i in indices]
        kinds = [e.kind for e in entries]
        as_stl_3mf = False
        if sd.needs_choice(kinds):
            dlg = sd.SendChoiceDialog([e.name for e in entries], kinds, self)
            if dlg.exec() != QDialog.Accepted:
                return None
            if dlg.choice == sd.PROJECT:
                return [entries[dlg.project_index].path]
            if dlg.choice == sd.MODELS:
                entries = [e for e in entries if e.kind != "3mf"]
            else:
                as_stl_3mf = True
        out = os.path.join(os.path.dirname(fc.cache_dir()), "to-slicer")
        files = []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for e in entries:
                if e.kind in ("stl", "obj") or (e.kind == "3mf" and not as_stl_3mf):
                    files.append(e.path)
                elif e.kind == "3mf":                   # printable objects only, as one STL
                    files.append(fc.export_stl(read_3mf_for_export(e.path), os.path.join(out, sd.stl_name(e.path))))
                else:                                   # PLY, OFF, glTF
                    files.append(fc.export_stl(load_file(e.path).parts, os.path.join(out, sd.stl_name(e.path))))
        finally:
            QApplication.restoreOverrideCursor()
        return files

    # kept for the tests and older callers: the files Show all sends, without asking
    def _show_all_files(self) -> list:
        c = self.zip
        return [c.entries[i].path for i in self._show_all_entries()] if c else []

    def _type_tag(self, kind: str) -> QLabel:
        """The coloured type label (STL, 3MF, G-code, ...) of the ZIP list and its legend."""
        label, bg, fg_dark, fg_light = _TYPE_TAGS.get(kind, (_KIND_LABELS.get(kind, kind.upper()),) + _OTHER_TAG)
        tag = QLabel(label)
        tag.setAlignment(Qt.AlignCenter)
        tag.setFixedWidth(self.fontMetrics().horizontalAdvance("FreeCAD") + 12)
        tag.setStyleSheet(f"background: {bg}; color: {fg_dark if theme.is_dark() else fg_light};"
                          f" border-radius: 3px; padding: 1px 4px; font-size: 11px; font-weight: 600;")
        tag.setToolTip(_type_info(kind))
        return tag

    def _zip_owner_visible(self, i: int) -> bool:
        actors = getattr(self, "_model_actors", [])
        return any(a.GetVisibility() for a, o in zip(actors, self._zip_owner) if o == i)

    def _set_zip_owner_visible(self, i: int, on: bool):
        for a, o in zip(getattr(self, "_model_actors", []), self._zip_owner):
            if o == i:
                a.SetVisibility(on)
        self.plotter.render()

    def _fill_zip_box(self):
        """The 3D files in the ZIP: one list to pick a file, or (Show all) to tick which models
        are shown. Below it a small legend of the types and what was left out."""
        c = self.zip
        self._clear_layout(self.zip_layout)
        self._zip_checks: dict[int, QCheckBox] = {}
        if c is None or len(c.entries) < 2:
            self.zip_box.hide()
            return
        showing_all = self.current_kind == "zip"
        if showing_all:
            self.objects_box.hide()                     # the list below has the checkboxes
        self.zip_box.setTitle(tr("In this ZIP ({n})").format(n=len(c.entries)))
        self.zip_layout.setSpacing(8)
        if len(c.arrangeable) >= 2:
            b = QPushButton(tr("Show one at a time") if showing_all else tr("Show all side by side"))
            b.setToolTip(tr("Place all models next to each other (G-code, STEP and FreeCAD files "
                            "are opened one at a time)"))
            b.clicked.connect(self._toggle_show_all)
            self.zip_layout.addWidget(b)

        lst = _RowList()
        lst.setObjectName("zipList")
        lst.setSelectionMode(QAbstractItemView.NoSelection if showing_all else QAbstractItemView.SingleSelection)
        lst.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        row_h = self.fontMetrics().height() + 16
        for i, e in enumerate(c.entries):
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(6, 0, 8, 0)
            h.setSpacing(8)
            arranged = showing_all and i in self._zip_owner
            if showing_all:
                cb = QCheckBox()
                if arranged:
                    cb.setChecked(self._zip_owner_visible(i))
                    cb.toggled.connect(lambda on, k=i: self._set_zip_owner_visible(k, on))
                    self._zip_checks[i] = cb
                else:                                   # G-code, STEP, FreeCAD: not on this plate
                    cb.setEnabled(False)
                    cb.setToolTip(tr("Opens on its own: click the name"))
                h.addWidget(cb)
            h.addWidget(self._type_tag(e.kind))
            name = _ElidedLabel(e.name)
            name.setToolTip(e.member)
            if showing_all and not arranged:
                name.setObjectName("muted")
            h.addWidget(name, 1)
            size = QLabel(_size_text(e.size))
            size.setObjectName("muted")
            size.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            h.addWidget(size)
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, row_h))
            lst.addItem(item)
            lst.setItemWidget(item, w)
        if not showing_all and 0 <= self._zip_index < len(c.entries):
            lst.setCurrentRow(self._zip_index)
        lst.setFixedHeight(row_h * min(len(c.entries), 10) + 2 * lst.frameWidth() + 2)
        lst.itemClicked.connect(lambda item, l=lst: self._zip_row_clicked(l.row(item)))
        self.zip_layout.addWidget(lst)

        # Legend: each type in this ZIP with its label and one line of explanation.
        legend = QWidget()
        g = QGridLayout(legend)
        g.setContentsMargins(0, 4, 0, 0)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(4)
        for r, k in enumerate(dict.fromkeys(e.kind for e in c.entries)):
            g.addWidget(self._type_tag(k), r, 0, Qt.AlignTop)
            text = _type_info(k).split(":", 1)[-1].strip()
            t = QLabel(text)
            t.setObjectName("muted")
            t.setWordWrap(True)
            g.addWidget(t, r, 1)
        g.setColumnStretch(1, 1)
        self.zip_layout.addWidget(legend)

        notes = []
        if c.skipped:
            notes.append(tr("{n} other files skipped (pictures, documents, links).").format(n=c.skipped))
        if showing_all:
            notes.append(tr("Untick a model to hide it; click a G-code to open it."))
        else:
            notes.append(tr("Tip: ↑ / ↓ keys move through the list"))
        note = QLabel("<br>".join(notes))
        note.setObjectName("muted")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px;")
        self.zip_layout.addWidget(note)
        self.zip_box.show()

    def _zip_row_clicked(self, row: int):
        if self.current_kind == "zip" and row in self._zip_checks:     # Show all: tick / untick
            cb = self._zip_checks[row]
            cb.setChecked(not cb.isChecked())
        elif row != self._zip_index or self.current_kind == "zip":
            self._open_zip_entry(row)

    # ============================================================ loading
    def open_dialog(self):
        start = self._user_folder() if self.current_path else ""
        if not start:
            recent = self.settings.get("recent_files", [])
            start = os.path.dirname(recent[0]) if recent else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, tr("Open 3D file"), start, file_filter())
        if path:
            self.load(path)

    def load(self, path: str, _zip: Optional[za.ZipContents] = None, _zip_index: int = 0):
        path = os.path.abspath(path)
        self._keep_folder(path, _zip)
        if not os.path.isfile(path):
            QMessageBox.warning(self, tr("File not found"),
                                tr("The file no longer exists:") + f"\n{path}")
            return
        if za.is_archive(path):
            self._load_archive(path)
            return
        kind = file_kind(path)
        if not kind:
            QMessageBox.warning(self, tr("Unsupported file"),
                                tr("PrintView3D can open STL, 3MF, OBJ, PLY, OFF, glTF/GLB, STEP, G-code and "
                                   "FreeCAD files, and ZIP files that contain them."))
            return
        self._pending_zip = (_zip, _zip_index) if _zip is not None else self._zip_of(path)
        self._load_token += 1
        token = self._load_token
        self.statusBar().showMessage(tr("Loading {name}…").format(name=os.path.basename(path)))
        self.progress.setValue(0)
        self.progress.show()
        self.slicer_btn.setEnabled(False)

        def work():
            try:
                result = load_file(path, lambda f: self._signals.progress.emit(token, f),
                                   self.settings.get("freecad_path", ""))
                self._signals.done.emit(token, (path, kind, result))
            except Exception as e:  # noqa: BLE001 - show any error to the user
                self._signals.failed.emit(token, f"{type(e).__name__}: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _keep_folder(self, path: str, _zip):
        """A file of the open folder (or of a ZIP in it) keeps the folder list; another file
        closes it."""
        if _zip is not None or getattr(self, "_folder_loading", False):
            return
        if not self._folder_of(path):
            self.folder = None

    def load_sync(self, path: str, _zip: Optional[za.ZipContents] = None, _zip_index: int = 0):
        """Load without a worker thread (used for --screenshot)."""
        path = os.path.abspath(path)
        self._keep_folder(path, _zip)
        if za.is_archive(path):
            self._load_token += 1
            self._on_archive_ready(za.open_archive(path), sync=True)
            return
        self._pending_zip = (_zip, _zip_index) if _zip is not None else self._zip_of(path)
        self._load_token += 1
        self._on_loaded(self._load_token, (path, file_kind(path),
                                           load_file(path, None, self.settings.get("freecad_path", ""))))

    def _on_progress(self, token: int, frac: float):
        if token == self._load_token:
            self.progress.setValue(int(frac * 100))

    def _on_failed(self, token: int, msg: str):
        if token != self._load_token:
            return
        self.progress.hide()
        self.slicer_btn.setEnabled(True)
        self.statusBar().clearMessage()
        QMessageBox.critical(self, tr("Could not open file"), msg)

    def _on_loaded(self, token: int, payload):
        if token != self._load_token:
            return
        if payload[0] == "__embedded__":
            self._on_embedded_loaded(token, payload)
            return
        if payload[0] == "__zip__":
            self._on_archive_ready(payload[1])
            return
        if payload[0] == "__zipall__":                  # Show all: the arranged models of a ZIP
            contents, data, owner = payload[1], payload[2][0], payload[2][1]
            self._pending_zip = (contents, -1)
            self._zip_owner = owner
            path, kind = contents.path, "zip"
        else:
            path, kind, data = payload
        self.zip, self._zip_index = self._pending_zip
        if self.zip is None:
            self._zip_owner = []
        elif self._zip_index >= 0:
            self._zip_last_single = self._zip_index
        self._zip_wanted = max(0, self._zip_index)
        self.progress.hide()
        self.slicer_btn.setEnabled(True)
        self.current_path = path
        self.current_kind = kind
        self._file_size_mb = os.path.getsize(path) / (1024 * 1024)
        self.showing_embedded = False
        self.settings.add_recent(self.zip.path if self.zip else path)
        self._refresh_recent_menu()
        title = self._display_name()
        if self.zip and kind != "zip":
            title += f" — {os.path.basename(self.zip.path)}"
        self.setWindowTitle(f"{title} — {APP_NAME}")
        self.stack.setCurrentIndex(1)
        self.act_home.setEnabled(True)

        self.scene.clear()
        self.view_stack.setCurrentIndex(0)
        self._reset_side_panel()
        # Another file (or Show all): its own start. The cuts and the frozen plane are for the
        # model they were made on, so they go; the measurements go too (see _update_view_menu).
        # Wireframe and X-ray stay: they are how you like to look at models.
        for a in (self.act_clip, self.act_clip_face):
            if a.isChecked():
                a.setChecked(False)
        self.view_freeze_cb.setChecked(False)

        if isinstance(data, GcodeData):
            self.model = None
            self._show_gcode(data)
        else:
            self.model = data
            self.gcode = None
            self._show_model(data)
        self.scene.set_bed_visible(self.act_bed.isChecked())
        self.controls.stop_animation()
        self.scene.set_view("iso")
        self._update_slicer_button()
        # 3MF projects; FreeCAD and STEP files once FreeCAD has turned them into 3D (it has parts).
        cad_parts = kind in ("freecad", "step") and bool(getattr(data, "parts", None))
        self._set_export_visible(kind == "3mf" or cad_parts)
        self.act_export_stl.setEnabled(True)
        self.act_export_stl.setToolTip(tr("Save the objects of this 3MF project as STL files (Ctrl+E)")
                                       if kind == "3mf" else
                                       tr("Save the objects of this CAD file as STL files (Ctrl+E)"))
        self._fill_zip_box()
        self._fill_folder_box()
        msg = tr("Opened {path}").format(path=self.zip.path if self.zip else path)
        if kind in ("freecad", "step") and not getattr(data, "parts", None):
            msg = self._freecad_status_text(data)
        self.statusBar().showMessage(msg, 10000)
        self._update_view_menu()

    # -------------------------------------------------------------- home
    def go_home(self):
        """Home (Ctrl+W): close the open file and show the start page with the recent files.
        Lets go of everything the file took: the model or toolpaths, the 3D view's copy of them
        and the side panel. The program itself (window, Qt, the 3D engine) stays, so this frees
        the most after big files. A ZIP's unpacked files stay on disk for the daily clean-up,
        because another window may be showing them."""
        self._load_token += 1               # a file still loading or switching is not shown after all
        self.progress.hide()
        self.slicer_btn.setEnabled(True)
        self._gcode_timer.stop()
        self.scene.clear()
        self._model_actors = []
        self.view_stack.setCurrentIndex(0)
        self._reset_side_panel()
        self.model = None
        self.gcode = None
        self.zip = None
        self.folder = None
        self.folder_box.hide()
        self._zip_index = self._zip_last_single = self._zip_wanted = 0
        self._zip_owner = []
        self._pending_zip = (None, 0)
        self.current_path = None
        self.current_kind = ""
        self.showing_embedded = False
        self._embedded_member = ""
        self._file_size_mb = 0.0
        self._set_export_visible(False)
        self._update_slicer_button()
        self.act_home.setEnabled(False)
        self.setWindowTitle(APP_NAME)
        self._refresh_recent_menu()         # the file just closed is at the top of the list
        self.stack.setCurrentIndex(0)
        self._update_view_menu()
        self.statusBar().clearMessage()
        self.plotter.render()               # the 3D view lets go of its drawn copy too
        gc.collect()                        # big arrays go back now, not at some later moment
        _return_free_memory()

    # ------------------------------------------------------------- model
    def _show_model(self, m: ModelData):
        self._model_actors = self.scene.show_model(m)
        self.check.set_model(m.parts)
        if m.freecad is not None and not m.parts:   # FreeCAD file without FreeCAD
            self._show_freecad_preview(m)
        self._fill_model_panel(m)

    def _fill_model_panel(self, m: ModelData):
        self.kind_label.setText(self._kind_text())
        self._add_zip_detail()
        if m.freecad is not None and not m.parts:
            self._show_thumbnail(False)             # shown large on the preview page
        else:
            self._set_thumbnail(m.thumbnail)
        actors = getattr(self, "_model_actors", [])
        b = m.bounds()
        if b:
            self._add_detail(tr("Size (X×Y×Z)"), ltr(tr("{x} × {y} × {z} {unit}").format(
                x=units.number(b[1] - b[0]), y=units.number(b[3] - b[2]), z=units.number(b[5] - b[4]),
                unit=units.name())))
        if b and max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) < 1.0:
            self._add_detail(tr("Note"), tr("Very small: the file may use metres instead of millimetres. "
                                            "Your slicer can scale it."))
        if m.parts:
            self._add_detail(tr("Triangles"), count(m.n_triangles))
        if len(m.parts) == 1:
            vol = self._mesh_volume(m.parts[0])
            if vol:
                self._add_detail(tr("Volume"), units.volume(vol))
        for k, v in m.meta.items():
            self._add_detail(meta_label(k), meta_value(v))

        if m.parts:
            many = len(m.parts) > 1
            for i, (part, actor) in enumerate(zip(m.parts, actors)):
                # One row per object: its colour box (a click picks another colour for this object
                # alone), its name - with a checkbox that shows or hides it when there are several -
                # and its size on the right (#59). The triangle count is in the tooltip.
                row = QWidget()
                row.setObjectName("objectRow")
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                rl.setSpacing(8)
                box = _ColorButton(self._object_color(i, part, len(m.parts)))
                box.setToolTip(tr("Click to pick another colour (right-click: the original colour)"))
                box.clicked.connect(lambda _=False, i=i, part=part, b=box: self._pick_object_color(i, part, b))
                box.customContextMenuRequested.connect(
                    lambda _pos, i=i, part=part, b=box: self._object_color_menu(i, part, b))
                rl.addWidget(box)
                if many:
                    cb = QCheckBox(part.name)
                    cb.setChecked(bool(actor.GetVisibility()))
                    cb.toggled.connect(lambda on, a=actor: (a.SetVisibility(on), self.plotter.render()))
                    name = cb
                else:
                    name = _ElidedLabel(part.name)
                # A long name is cut at the panel's edge (full name in the tooltip) instead of
                # making the whole panel wider than the window.
                name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
                rl.addWidget(name, 1)
                size = part.size()
                size_text = ltr(_size_mm(size)) if size else ""
                if size_text:
                    # Full width when there is room; in a very narrow panel (big font) it ends
                    # in "…" instead of pushing the panel wider than its view. Tooltip: all of it.
                    lbl = _ElidedLabel(size_text)
                    lbl.setObjectName("objectSize")
                    lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
                    rl.addWidget(lbl)
                tip = [part.name]
                if size_text:
                    tip.append(size_text)
                tip.append(tr("{n} triangles").format(n=count(part.n_triangles)))
                row.setToolTip("\n".join(tip))
                name.setToolTip(row.toolTip())
                self.objects_layout.addWidget(row)
            self.objects_box.setTitle(tr("Objects ({n})").format(n=len(m.parts)) if many else tr("Object"))
            self._fit_objects_list()
            self.objects_box.show()

        if m.freecad:
            self._fill_freecad_box(m)

        if m.embedded_gcode:
            self.embedded_box.setTitle(tr("Sliced plates"))
            info = QLabel(tr("This project contains sliced G-code."))
            info.setObjectName("muted")
            info.setWordWrap(True)
            self.embedded_layout.addWidget(info)
            for member in m.embedded_gcode:
                b = QPushButton(tr("Show toolpaths — {plate}").format(plate=_plate_name(member)))
                b.clicked.connect(lambda _=False, mem=member: self._show_embedded(mem))
                self.embedded_layout.addWidget(b)
            self.embedded_box.show()

    def _object_color(self, i: int, part, n: int) -> str:
        """The colour an object is drawn in now: the one picked for it, else the file's own."""
        return self.scene.part_color_override(i) or Scene.part_color(part, i, n)

    def _pick_object_color(self, i: int, part, button: "_ColorButton"):
        """A click on an object's colour box: the colour picker, for this object alone."""
        n = len(self.model.parts) if self.model is not None else 1
        c = QColorDialog.getColor(QColor(self._object_color(i, part, n)), self, tr("Colour of the object"))
        if c.isValid():
            self.scene.set_part_color(i, c.name())
            button.set_color(c.name())
            self.plotter.render()

    def _object_color_menu(self, i: int, part, button: "_ColorButton"):
        from PySide6.QtGui import QCursor
        menu = QMenu(self)
        back = menu.addAction(tr("Original colour"))
        back.setEnabled(self.scene.part_color_override(i) is not None)
        if menu.exec(QCursor.pos()) is back:
            self.scene.set_part_color(i, None)
            n = len(self.model.parts) if self.model is not None else 1
            button.set_color(Scene.part_color(part, i, n))
            self.plotter.render()

    # ----------------------------------------------------------- FreeCAD
    def _freecad_status_text(self, m: ModelData) -> str:
        info = m.freecad or {}
        status = info.get("status")
        step = info.get("source") == "step"
        if step and status == "ok":
            return tr("Converted to 3D with FreeCAD.")
        if step and status == "no_freecad":
            return tr("STEP files are shown in 3D with the help of FreeCAD (free), "
                      "which was not found on this computer.")
        if status == "ok":
            return tr("Shown as in FreeCAD: visible objects only (no sketches, hidden objects or helpers).")
        if status == "nothing_visible":
            return tr("Nothing is visible in this document: all objects are hidden in FreeCAD.")
        if status == "failed":
            return tr("FreeCAD could not convert this file: {error}").format(error=info.get("error", ""))
        return tr("FreeCAD was not found, so only the preview picture is shown. "
                  "Install FreeCAD (free, freecad.org) to see the model in 3D.")

    def _fill_freecad_box(self, m: ModelData):
        info = m.freecad
        self.embedded_box.setTitle(tr("STEP file") if info.get("source") == "step" else tr("FreeCAD document"))
        if m.parts:                                 # (otherwise the preview page explains it)
            text = QLabel(self._freecad_status_text(m))
            text.setObjectName("muted")
            text.setWordWrap(True)
            self.embedded_layout.addWidget(text)
        shown = info.get("shown") or []
        if shown and not m.parts:
            names = QLabel(tr("Visible objects: {names}").format(
                names=", ".join(o.label for o in shown)))
            names.setWordWrap(True)
            self.embedded_layout.addWidget(names)
        if info.get("install"):
            b = QPushButton(tr("Open in FreeCAD"))
            b.clicked.connect(self.open_in_freecad)
            self.embedded_layout.addWidget(b)
        else:
            b = QPushButton(tr("Choose FreeCAD…"))
            b.clicked.connect(self.open_settings)
            self.embedded_layout.addWidget(b)
        self.embedded_box.show()

    def _freecad_install(self):
        info = (self.model.freecad or {}) if self.model is not None else {}
        return info.get("install") or fc.find_freecad(self.settings.get("freecad_path", ""))

    def open_in_freecad(self):
        install = self._freecad_install()
        if install is None:
            r = QMessageBox.question(self, tr("FreeCAD not found"),
                                     tr("FreeCAD was not found on this computer.") + "\n\n"
                                     + tr("Open Settings to choose the FreeCAD program?"))
            if r == QMessageBox.Yes:
                self.open_settings()
            return
        try:
            fc.open_in_freecad(install, self.current_path)
        except OSError as e:
            QMessageBox.critical(self, tr("Could not start FreeCAD"), str(e))
            return
        self.statusBar().showMessage(tr("Opening {file} in {slicer}…").format(
            file=os.path.basename(self.current_path or ""), slicer="FreeCAD"), 6000)

    def _stl_for_slicer(self) -> Optional[str]:
        """The visible objects as a temporary STL a slicer can open (FreeCAD, PLY, OFF, glTF)."""
        m = self.model
        actors = getattr(self, "_model_actors", [])
        parts = [p for p, a in zip(m.parts, actors) if a.GetVisibility()] if m else []
        if m and m.parts and not parts:            # every object hidden: send them all
            parts = list(m.parts)
        if not parts:
            if self.current_kind == "step":
                text = tr("This slicer does not open STEP files, and PrintView3D needs FreeCAD to convert "
                          "it to STL. Install FreeCAD or choose it in Settings, or send the file to "
                          "OrcaSlicer, PrusaSlicer or Bambu Studio, which open STEP files themselves.")
            else:
                text = tr("To send a FreeCAD model to a slicer, PrintView3D needs FreeCAD to "
                          "convert it first. Install FreeCAD or choose it in Settings.")
            QMessageBox.information(self, tr("Nothing to send"), text)
            return None
        base = os.path.splitext(os.path.basename(self.current_path or "model"))[0]
        return fc.export_stl(parts, os.path.join(os.path.dirname(fc.cache_dir()), "to-slicer", base + ".stl"))

    @staticmethod
    def _mesh_volume(part) -> float:
        v, f = part.vertices.astype(np.float64), part.faces
        if len(f) == 0:
            return 0.0
        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        vol = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
        return abs(vol)

    def _show_embedded(self, member: str):
        path = self.current_path
        if not path:
            return
        self.statusBar().showMessage(tr("Reading sliced G-code from project…"))
        self.progress.setValue(0)
        self.progress.show()
        self._load_token += 1
        token = self._load_token

        def work():
            try:
                text = read_embedded_gcode(path, member)
                g = parse_gcode_text(text, lambda f: self._signals.progress.emit(token, f))
                self._signals.done.emit(token, ("__embedded__", member, g))
            except Exception as e:  # noqa: BLE001
                self._signals.failed.emit(token, f"{type(e).__name__}: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _on_embedded_loaded(self, token: int, payload):
        _, member, g = payload
        self.progress.hide()
        self.showing_embedded = True
        self._embedded_member = member
        self.model = None
        self.scene.clear()
        self._reset_side_panel()
        self._show_gcode(g)
        self._fill_zip_box()
        self.scene.set_bed_visible(self.act_bed.isChecked())
        self.controls.stop_animation()
        self.scene.set_view("iso")
        self.statusBar().clearMessage()
        self._update_view_menu()

    # ------------------------------------------------------------- gcode
    def _show_gcode(self, g: GcodeData):
        self.gcode = g
        self.check.set_model([])
        self.scene.show_gcode(g)
        self._fill_gcode_panel(g)
        if g.n_layers == 0:
            self.statusBar().showMessage(tr("No printable moves found in this G-code."), 8000)
            return
        # Start with the whole print visible
        self.layer_slider.blockSignals(True)
        self.layer_spin.blockSignals(True)
        self.layer_slider.setValue(g.n_layers - 1)
        self.layer_spin.setValue(g.n_layers)
        self.layer_slider.blockSignals(False)
        self.layer_spin.blockSignals(False)
        self.only_layer_cb.blockSignals(True)
        self.only_layer_cb.setChecked(False)
        self.only_layer_cb.blockSignals(False)
        self._update_layer_label()
        self._redraw_gcode()

    def _fill_gcode_panel(self, g: GcodeData):
        self.kind_label.setText(self._kind_text())
        self._add_zip_detail()
        self._set_thumbnail(g.thumbnail)

        b = g.extrusion_bounds
        if b:
            self._add_detail(tr("Print size"), ltr(tr("{x} × {y} × {z} {unit}").format(
                x=units.number(b[1] - b[0], 1), y=units.number(b[3] - b[2], 1), z=units.number(b[5]),
                unit=units.name())))
        self._add_detail(tr("Layers"), count(g.n_layers))
        for key in GCODE_META_ORDER:
            if key in g.meta:
                self._add_detail(meta_label(key), meta_value(g.meta[key]))

        if self.showing_embedded:
            self.embedded_box.setTitle(tr("Project"))
            back = QPushButton(tr("Back to 3D model"))
            back.clicked.connect(lambda: self.load(self.current_path))
            self.embedded_layout.addWidget(back)
            self.embedded_box.show()

        if g.n_layers == 0:
            return

        show_travel = bool(self.settings.get("show_travel"))
        for key, _label, color in FEATURES:
            if key not in g.feature_counts:
                continue
            cb = QCheckBox(feature_label(key))
            cb.setIcon(_swatch(color))
            cb.setChecked(show_travel if key == "travel" else True)
            cb.toggled.connect(self._schedule_gcode)
            self.features_layout.addWidget(cb)
            self.feature_checks[key] = cb
        row = QHBoxLayout()
        all_b = QPushButton(tr("All"))
        all_b.clicked.connect(lambda: self._set_all_features(True))
        none_b = QPushButton(tr("None"))
        none_b.clicked.connect(lambda: self._set_all_features(False))
        row.addWidget(all_b)
        row.addWidget(none_b)
        row.addStretch(1)
        self.features_layout.addLayout(row)
        self.features_box.show()

        self.layer_slider.blockSignals(True)
        self.layer_spin.blockSignals(True)
        self.layer_slider.setRange(0, g.n_layers - 1)
        self.layer_spin.setRange(1, g.n_layers)
        self.layer_slider.blockSignals(False)
        self.layer_spin.blockSignals(False)
        self.layers_box.show()
        self._update_layer_label()

    def _set_all_features(self, on: bool):
        for key, cb in self.feature_checks.items():
            if key == "travel" and on:
                continue
            cb.blockSignals(True)
            cb.setChecked(on)
            cb.blockSignals(False)
        self._schedule_gcode()

    def _visible_features(self) -> np.ndarray:
        vis = np.zeros(len(FEATURES), dtype=bool)
        for key, cb in self.feature_checks.items():
            vis[FEATURE_INDEX[key]] = cb.isChecked()
        return vis

    def _on_layer_changed(self, v: int):
        self.layer_spin.blockSignals(True)
        self.layer_spin.setValue(v + 1)
        self.layer_spin.blockSignals(False)
        self._update_layer_label()
        self._schedule_gcode()

    def _update_layer_label(self):
        g = self.gcode
        if g is None or g.n_layers == 0:
            self.layer_info.setText("")
            return
        i = self.layer_slider.value()
        self.layer_info.setText(tr("<b>Layer {n}</b> of {total}  ·  Z = {z} {unit}").format(
            n=count(i + 1), total=count(g.n_layers), z=units.number(g.layer_z[i]), unit=units.name()))

    def _schedule_gcode(self, *_):
        self._gcode_timer.start()

    def _redraw_gcode(self):
        if self.gcode is None or self.gcode.n_layers == 0:
            return
        self.scene.update_gcode(self.layer_slider.value(), self.only_layer_cb.isChecked(),
                                self._visible_features())

    def step_layer(self, delta: int):
        if self.gcode is not None and self.layers_box.isVisible():
            self.set_layer(self.layer_slider.value() + delta)

    def set_layer(self, value: int):
        if self.gcode is not None and self.layers_box.isVisible():
            self.layer_slider.setValue(max(0, min(value, self.layer_slider.maximum())))

    @staticmethod
    def _cube_labels() -> dict[str, str]:
        return {"top": tr("Top"), "front": tr("Front"), "right": tr("Right"),
                "back": tr("Back"), "left": tr("Left"), "bottom": tr("Bottom")}

    @staticmethod
    def _cube_tooltips() -> dict[str, str]:
        return {"arrow_left": tr("Turn left 45°"), "arrow_right": tr("Turn right 45°"),
                "arrow_up": tr("Tilt up 45° (towards Top)"),
                "arrow_down": tr("Tilt down 45° (towards Bottom)"),
                "home": tr("Home: Iso view, fitted")}

    def _cube_view(self, part: str):
        """A click on the view cube: a face picks that view, Home goes back to Iso."""
        self.set_view("iso" if part == "home" else part, animate=True)

    def set_view_cube_visible(self, on: bool):
        self.view_cube.set_visible(on)
        self._update_view_buttons()
        self.plotter.render()

    # Views the cube offers: their toolbar buttons only show while the cube is switched off.
    # Iso is the cube's Home icon.
    CUBE_VIEWS = ("iso", "top", "front", "right")

    def _update_view_buttons(self):
        """With the view cube on, the toolbar keeps Fit and Plate: Top, Front and Right are on the
        cube, and its Home icon is the Iso view. Switch the cube off (Settings -> Viewer) and their
        buttons come back. The keys 1, 2, 3 and 4 work either way."""
        cube_on = self.view_cube.visible
        for act, _, view in self.view_actions:
            if view in self.CUBE_VIEWS:
                act.setVisible(not cube_on)

    # ============================================================ actions
    def set_view(self, view: Optional[str], animate: bool = False):
        """Show the model from `view` (None = fit the current view). animate=True turns there
        smoothly (view buttons, keys and the view cube); the command line and screenshots jump."""
        if self.stack.currentIndex() != 1:
            return
        if not animate:
            self.controls.stop_animation()
            self.scene.set_view(view or self.scene._view)
            return
        start = self.controls.camera_state()
        self.scene.set_view(view or self.scene._view, render=False)
        end = self.controls.camera_state()
        self.controls._set_state(start)
        self.controls.animate_to(end)

    def _toggle_bed(self, on: bool):
        self.scene.set_bed_visible(on)
        self.settings.set("show_bed", on)
        self.plotter.render()

    # ------------------------------------------------------------ view (#60)
    CLIP_STEPS = 1000            # the clip slider's steps from the model's bottom to its top

    def _view_options_apply(self) -> bool:
        """The View menu works on a model shown in 3D (not on G-code or a preview picture)."""
        return (self.stack.currentIndex() == 1 and self.model is not None and self.gcode is None
                and bool(getattr(self.model, "parts", None)) and self.view_stack.currentIndex() == 0)

    SIDE_MIN_WIDTH = 290                             # the side panel never gets narrower than this ...

    def _update_side_min_width(self):
        """... nor narrower than the View and Measure sections need for every button's icon and
        whole name in the smallest font (it depends on the language). Called at start and when
        the language changes."""
        if not hasattr(self, "side_scroll"):
            return
        m = self.side_layout.contentsMargins()
        bar = self.side_scroll.style().pixelMetric(self.side_scroll.style().PixelMetric.PM_ScrollBarExtent)
        need = max(box.minimumSizeHint().width() for box in (self.view_box, self.measure_box))
        need += m.left() + m.right() + bar + 2 * self.side_scroll.frameWidth() + 2
        width = max(self.SIDE_MIN_WIDTH, need)
        self.side_scroll.setMinimumWidth(width)
        if self.side_scroll.maximumWidth() < width:
            self.side_scroll.setMaximumWidth(width)
        self._side_width = max(self._side_width, width)

    def _remember_side_width(self, *_):
        """Keep how wide the side panel was, for when it has been dragged shut."""
        w = self.splitter.sizes()[self.splitter.indexOf(self.side_scroll)]
        if w >= 50:
            self._side_width = w

    def _open_side_panel(self):
        """If the side panel was dragged shut, open it again to the width it had."""
        i = self.splitter.indexOf(self.side_scroll)
        sizes = self.splitter.sizes()
        if sizes[i] >= 50:
            return
        total = sum(sizes)
        sizes[i] = self._side_width
        sizes[1 - i] = max(0, total - self._side_width)
        self.splitter.setSizes(sizes)

    # ------------------------------------------------------------ check
    def set_check_section(self, on: bool):
        """The Check button: shows or hides the Check section and the highlights it controls."""
        show = bool(on) and self._view_options_apply()
        self.check_box.setVisible(show)
        if show:
            self._open_side_panel()
        if hasattr(self, "check") and self.check.active != show:
            self.check.set_active(show)
        self._update_check_panel()

    def _check_shown(self, kind: str, on: bool):
        shown = dict(self.settings.get("check_show", {}) or {})
        shown[kind] = bool(on)
        self.settings.set("check_show", shown)
        self.check.set_shown(kind, on)

    def _check_angle_changed(self, value: int):
        self.settings.set("check_angle", int(value))
        self.check.set_angle(value)

    def _check_nozzle_changed(self):
        mm = round(self.check_nozzle.mm(), 4)
        if abs(mm - self.check.nozzle) < 1e-6:
            return
        self.settings.set("check_nozzle", mm)
        self.check.set_nozzle(mm)

    def _pick_check_color(self, kind: str, button: "_ColorButton"):
        c = QColorDialog.getColor(QColor(self.check.colors[kind]), self, tr("Colour"))
        if c.isValid():
            self._set_check_color(kind, c.name(), button)

    def _reset_check_color(self, kind: str, button: "_ColorButton"):
        from .print_check import DEFAULT_COLORS
        self._set_check_color(kind, DEFAULT_COLORS[kind], button)

    def _set_check_color(self, kind: str, color: str, button: "_ColorButton"):
        colours = dict(self.settings.get("check_colors", {}) or {})
        colours[kind] = color
        self.settings.set("check_colors", colours)
        button.set_color(color)
        self.check.set_color(kind, color)

    def _update_check_panel(self):
        """The counts beside each check, and how far the thin-wall check is."""
        if not hasattr(self, "check") or not hasattr(self, "check_rows"):
            return
        counts = self.check.counts() if self.check.active else {}
        units_text = {"overhang": tr("{n} faces"), "thin": tr("{n} faces"), "open": tr("{n} edges"),
                      "nonmanifold": tr("{n} edges"), "flipped": tr("{n} faces"), "loose": tr("{n} parts")}
        for kind, (cb, lbl, _box) in self.check_rows.items():
            n = counts.get(kind)
            lbl.setText("" if n is None else (tr("none") if n == 0 else units_text[kind].format(n=count(n))))
        status = ""
        if self.check.active and self.check.mesh_busy:
            status = tr("Checking the mesh…")
        if self.check.active and self.check.show.get("thin"):
            if self.check.thin_progress is not None:
                status = tr("Checking thin walls… {p} %").format(p=int(self.check.thin_progress * 100))
        self.check_thin_status.setText(status)
        self.check_thin_status.setVisible(bool(status))

    def set_view_section(self, on: bool):
        """The View button: shows or hides the View section of the side panel (and opens the side
        panel if it was dragged shut)."""
        show = bool(on) and self._view_options_apply()
        self.view_box.setVisible(show)
        if show:
            self._open_side_panel()

    def set_cut_frozen(self, on: bool):
        """View section: freeze the Clip facing you cut where it is (the other cut never moves)."""
        self.scene.set_face_frozen(on)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def _update_view_menu(self):
        """After a file opens or closes: the View options on or off for it, the sections with it."""
        ok = self._view_options_apply()
        for a in (self.act_view, self.act_check, self.act_wireframe, self.act_xray, self.act_clip, self.act_clip_face,
                  self.act_reset_view, self.act_measure, *self.measure_actions.values()):
            a.setEnabled(ok)
        self.view_btn.setEnabled(ok)
        self.view_box.setVisible(ok and self.act_view.isChecked())
        if hasattr(self, "check"):
            self.set_check_section(self.act_check.isChecked())
        self._update_hints()
        if not hasattr(self, "measure"):
            pass                                         # still being built
        elif not ok and self.act_measure.isChecked():
            self.act_measure.setChecked(False)           # nothing to measure: off
        elif ok and self.measure.active and self.measure.refresh_model():
            self._update_measure_panel()                 # another model: the old points are gone
        self.clip_box.setVisible(ok and bool(self._clip_cuts()))
        if ok and self.act_clip.isChecked():
            self._on_clip_changed(self.clip_slider.value(), render=False)
        if ok and self.act_clip_face.isChecked():
            self._on_face_changed(self.face_slider.value(), render=False)
        self._update_clip_label()

    def set_wireframe(self, on: bool):
        self.scene.set_wireframe(on)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def set_xray(self, on: bool):
        self.scene.set_xray(on)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def set_clip_ghost(self, on: bool):
        """Clip box: the cut-away part as a see-through ghost (#66). Remembered."""
        self.settings.set("clip_ghost", bool(on))
        self.scene.set_ghost(on)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def set_clip_plane(self, on: bool):
        """Clip box: the cutting plane as a faint sheet (#66). Remembered."""
        self.settings.set("clip_plane", bool(on))
        self.scene.set_cut_plane(on)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def set_ghost_strength(self, strength: int):
        """Settings -> Viewer -> Cut-away part: drawn fainter or stronger. Shown at once, so the
        slider in Settings can be tried live (Cancel puts the old value back)."""
        self.scene.set_ghost_strength(strength)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def set_plane_strength(self, strength: int):
        """Settings -> Viewer -> Cutting plane: the same, for the plane."""
        self.scene.set_plane_strength(strength)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def reset_view(self):
        """View -> Reset view (R, #66): wireframe, X-ray and both cuts off, and the model fitted, like Fit.
        Nothing else changes (the plate, the objects shown, the theme, the measurements)."""
        if not self._view_options_apply():
            return
        for a in (self.act_wireframe, self.act_xray, self.act_clip, self.act_clip_face):
            if a.isChecked():
                a.setChecked(False)
        self.view_freeze_cb.setChecked(False)
        self.set_view(None, animate=True)

    # ------------------------------------------------------------ measure
    def _measure_mode_setting(self) -> str:
        mode = self.settings.get("measure_mode", "distance")
        return mode if mode in ("distance", "angle", "circle") else "distance"

    @staticmethod
    def _measure_mode_label(kind: str) -> str:
        return {"distance": tr("Distance"), "angle": tr("Angle"), "circle": tr("Circle")}[kind]

    @staticmethod
    def _measure_mode_tip(kind: str) -> str:
        return tr("Circle (diameter, radius)") if kind == "circle" else MainWindow._measure_mode_label(kind)

    def set_measure_on(self, on: bool):
        """The Measure button (M): a click on the model places a point (instead of setting the
        rotation centre); the side panel shows the value."""
        on = bool(on) and self._view_options_apply()
        if on == self.measure.active:
            return
        if on:
            self.measure.start()
        else:
            self.measure.stop()
        self.measure_box.setVisible(on)
        if on:
            self._open_side_panel()
        try:
            if on:
                self.plotter.interactor.setCursor(Qt.CrossCursor)
            else:
                self.plotter.interactor.unsetCursor()
        except Exception:   # noqa: BLE001
            pass
        self._update_measure_panel()
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def choose_measure_mode(self, kind: str):
        """The Measure button's menu: a distance, an angle or a circle. Turns Measure on."""
        self.settings.set("measure_mode", kind)
        self.measure_actions[kind].setChecked(True)
        self.measure.set_mode(kind)
        if not self.act_measure.isChecked() and self.act_measure.isEnabled():
            self.act_measure.setChecked(True)
        self._update_measure_panel()

    def set_measure_snap(self, on: bool):
        self.measure.set_snap(on)

    def set_measure_dotted(self, on: bool):
        self.settings.set("measure_dotted", bool(on))
        self.measure.set_dotted(on)

    def _measure_clear(self):
        self.measure.clear()

    def set_measure_line_width(self, px: int):
        """Settings -> Viewer -> Measurement lines: how thick the lines are. Shown at once, so the
        slider in Settings can be tried live (Cancel puts the old value back)."""
        self.measure.set_line_width(px)
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def set_measure_deltas(self, on: bool):
        self.settings.set("measure_deltas", bool(on))
        self.measure.set_deltas(on)

    def _update_measure_panel(self):
        """Clear on or off, and the hint for the chosen kind of measurement. The values are
        written next to the measurements in the 3D view, not here: there can be several at once."""
        if not hasattr(self, "measure") or not hasattr(self, "measure_clear_btn"):
            return
        self.measure_clear_btn.setEnabled(self.measure.has_items)
        self._update_hints()

    def _update_hints(self):
        """The instructions in the bottom centre of the 3D view: how to use Clip facing you while
        it is on, and how to use the kind of measurement that is chosen while Measure is on. They
        are in the 3D view, where you look, instead of in the side panel where they got overlooked."""
        if not hasattr(self, "hints") or not hasattr(self, "measure"):
            return
        texts = []
        if self._view_options_apply():
            if self.measure.active:
                texts.append({
                    "distance": tr("Click two points on the model."),
                    "angle": tr("Click three points: one side, the corner, the other side."),
                    "circle": tr("Click three points on the edge of a circle or hole."),
                }[self.measure.mode] + " " + tr("Drag a point to move it, drag elsewhere to turn the view."))
            if "face" in self._clip_cuts():
                texts.append(tr("Turn or move the view to pass the model through the cut."))
        self.hints.set_texts(texts)

    def _clip_cuts(self) -> list:
        """The cuts that are on: "top" (Clip from the top), "face" (Clip facing you), both or none."""
        if not hasattr(self, "act_clip_face"):
            return []
        return [k for k, a in (("top", self.act_clip), ("face", self.act_clip_face)) if a.isChecked()]

    def set_clip_face_on(self, on: bool):
        """View -> Clip facing you (V): on or off, whatever Clip from the top does (#70). It starts
        through the centre of the view; its slider moves the cut nearer or further."""
        self._start_clip("face", on)

    def set_clip_on(self, on: bool):
        """View -> Clip from the top (C): on or off, whatever Clip facing you does (#70). It starts
        halfway up the model; its slider moves the cut."""
        self._start_clip("top", on)

    def _start_clip(self, cut: str, on: bool):
        slider = self.clip_slider if cut == "top" else self.face_slider
        row = self.clip_top_row if cut == "top" else self.clip_face_row
        self._retitle_clip_box()
        if on and self._view_options_apply():
            if not self.act_view.isChecked():
                self.act_view.setChecked(True)       # its controls are in the View section
            # A cut that is turned on starts in the middle of its slider.
            slider.blockSignals(True)
            slider.setValue(self.CLIP_STEPS // 2)
            slider.blockSignals(False)
            row.show()
            self.clip_box.show()
            if cut == "top":
                self._on_clip_changed(slider.value())
            else:
                self._on_face_changed(slider.value())
            return
        row.setVisible(on)
        if cut == "top":
            self.scene.set_clip(None)
        else:
            self.scene.set_face_clip(None)
        if not self._clip_cuts():
            self.clip_box.hide()
        self._update_clip_label()
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def _clip_height(self, value: int) -> Optional[float]:
        r = self.scene.model_z_range()
        if r is None:
            return None
        return r[0] + (r[1] - r[0]) * value / self.CLIP_STEPS

    def _retitle_clip_box(self):
        """Show the rows of the cuts that are on (the freeze choice belongs to Clip facing you)."""
        cuts = self._clip_cuts()
        self.clip_top_row.setVisible("top" in cuts)
        self.clip_face_row.setVisible("face" in cuts)
        self.view_freeze_cb.setVisible("face" in cuts)
        self._update_hints()

    def _clip_offset(self, value: int) -> Optional[float]:
        """Clip facing you: the slider's middle is the centre of the view."""
        reach = self.scene.model_face_reach()
        if reach is None:
            return None
        return reach * (2.0 * value / self.CLIP_STEPS - 1.0)

    def _on_face_changed(self, value: int, render: bool = True):
        if not self.act_clip_face.isChecked():
            return
        d = self._clip_offset(value)
        if d is None:
            return
        self.scene.set_face_clip(d)
        self._update_clip_label()
        if render and self.stack.currentIndex() == 1:
            self.plotter.render()

    def _on_clip_changed(self, value: int, render: bool = True):
        if not self.act_clip.isChecked():
            return
        z = self._clip_height(value)
        if z is None:
            return
        # Exactly at the top the cut would hide the top faces: keep them (nothing is cut).
        self.scene.set_clip(None if value >= self.CLIP_STEPS else z)
        self._update_clip_label()
        if render and self.stack.currentIndex() == 1:
            self.plotter.render()

    def _update_clip_label(self):
        r = self.scene.model_z_range() if hasattr(self, "scene") else None
        if r is None:
            self.clip_info.setText("")
            self.face_info.setText("")
            return
        # How far the cut has gone into the model, seen from where it faces: 0 at the front, the
        # whole depth of the model at the back. (The slider itself moves the cut away from the
        # centre of the view; this number does not depend on where that is.)
        depth = self.scene.face_cut_depth()
        if depth is None:
            self.face_info.setText("")
        else:
            self.face_info.setText(ltr(tr("Depth {d} of {total} {unit}").format(
                d=units.number(depth[0], 1), total=units.number(depth[1], 1), unit=units.name())))
        z = self._clip_height(self.clip_slider.value())
        self.clip_info.setText(ltr(tr("Height {z} of {top} {unit}").format(
            z=units.number(z - r[0], 1), top=units.number(r[1] - r[0], 1), unit=units.name())))

    def _plate_size(self) -> tuple:
        size = self.settings.get("plate_size", [300, 300])
        try:
            w, d = (min(PlateSizeDialog.MAX, max(PlateSizeDialog.MIN, float(v))) for v in size)
        except (TypeError, ValueError):
            w, d = 300.0, 300.0
        return (w, d)

    def _mark_plate_mode(self):
        """Tick the plate in use in the Plate menu (with the custom size in its name)."""
        mode = self.settings.get("plate_mode", "printer")
        for key, a in self.plate_actions.items():
            text = plate_mode_label(key)
            if key == "custom":
                w, d = self._plate_size()
                text += "  ({w} × {d} {unit})".format(w=units.number(w, 0), d=units.number(d, 0),
                                                       unit=units.name())
            a.setText(text)
            a.setChecked(key == mode)

    def choose_plate_mode(self, mode: str, ask: bool = True):
        """Plate menu: draw the printer's plate, a plate that grows to fit the model, a plate of
        your own size (asks for it) or an endless grid. Shows the plate if it was hidden."""
        if mode not in PLATE_MODES:
            mode = "printer"
        if mode == "custom" and ask:
            dlg = PlateSizeDialog(self._plate_size(), self)
            if not dlg.exec():
                self._mark_plate_mode()             # keep the tick where it was
                return
            self.settings.set("plate_size", list(dlg.plate_size()))
        self.settings.set("plate_mode", mode)
        self.scene.set_plate_mode(mode, self._plate_size())
        self._mark_plate_mode()
        if not self.act_bed.isChecked():
            self.act_bed.setChecked(True)           # choosing a plate means you want to see it
        elif self.stack.currentIndex() == 1:
            self.plotter.render()

    # ------------------------------------------------------------ slicer
    def _slicer_name(self, sid: str, name: str) -> str:
        return tr("custom slicer") if (sid == sl.CUSTOM and name == "custom slicer") else name

    def _update_slicer_button(self):
        freecad = self.current_kind == "freecad" and not self.showing_embedded
        # A 3D printer for slicers; the FreeCAD cube when the button opens FreeCAD.
        self.slicer_btn.setIcon(theme.tool_icon("freecad" if freecad else "slicer", on_accent=True, gap=True))
        if freecad:
            self.slicer_btn.setText(tr("Open in FreeCAD"))
            self.slicer_btn.setToolTip(tr("Open this file in FreeCAD (Ctrl+P). "
                                          "Use the arrow to send the model to a slicer as STL."))
            return
        sid, name, _ = sl.resolve(self.settings)
        if sid:
            name = self._slicer_name(sid, name)
            self.slicer_btn.setText(tr("Open in {slicer}").format(slicer=name))
            self.slicer_btn.setToolTip(tr("Open this file in {slicer} (Ctrl+P). "
                                          "Use the arrow to pick another slicer.").format(slicer=name))
        else:
            self.slicer_btn.setText(tr("Open in slicer"))
            self.slicer_btn.setToolTip(tr("No slicer found yet — choose one in Settings (Ctrl+P)"))

    def _fill_slicer_menu(self):
        self.slicer_menu.clear()
        default_id = sl.resolve(self.settings)[0]
        installed = sl.detect_installed(self.settings.get("slicer_paths") or {})
        custom = self.settings.get("custom_slicer") or {}
        entries = [(s.id, s.name) for s in sl.SLICERS if s.id in installed]
        if os.path.isfile(custom.get("path", "")):
            entries.append((sl.CUSTOM, self._slicer_name(sl.CUSTOM, sl.slicer_name(sl.CUSTOM, custom.get("name", "")))))
        freecad_file = self.current_kind == "freecad"
        step_file = self.current_kind == "step"
        if freecad_file or (step_file and self._freecad_install() is not None):
            self.slicer_menu.addAction(tr("Open in FreeCAD"), self.open_in_freecad)
            self.slicer_menu.addSeparator()
        if not entries:
            a = self.slicer_menu.addAction(tr("No slicers found"))
            a.setEnabled(False)
        for sid, name in entries:
            as_stl = ((self.current_kind in SEND_AS_STL and not self.showing_embedded)
                      or (step_file and not sl.reads_step(sid)))
            label = (tr("Send to {slicer} as STL") if as_stl else tr("Open in {slicer}")).format(slicer=name)
            if sid == default_id:
                label += "   " + tr("(default)")
            self.slicer_menu.addAction(label, lambda s_id=sid: self.open_in_slicer(s_id))
        if self.zip and len(self.zip.arrangeable) >= 2 and entries:
            self.slicer_menu.addSeparator()
            idx = [i for i, e in enumerate(self.zip.entries) if e.kind in za.ARRANGEABLE]
            self.slicer_menu.addAction(tr("Send all models in the ZIP ({n})").format(n=len(idx)),
                                       lambda ix=idx: self.open_in_slicer(entries=ix))
        self.slicer_menu.addSeparator()
        self.slicer_menu.addAction(tr("Choose default slicer…"), self.open_settings)

    def open_in_slicer(self, slicer_id: Optional[str] = None, files: Optional[list] = None,
                       entries: Optional[list] = None):
        file_to_send = self.current_path
        if files is None and entries is None and self.current_kind == "zip":   # Show all: ticked models
            entries = self._show_all_entries()
        if entries is not None:
            files = self._files_to_send(entries)
            if not files:
                return
        if files is not None:
            file_to_send = files if len(files) > 1 else files[0]
        elif self.current_kind == "freecad" and self.current_path:
            if slicer_id is None:                  # main button / Ctrl+P: FreeCAD itself
                self.open_in_freecad()
                return
            file_to_send = self._stl_for_slicer()
            if not file_to_send:
                return
        elif self.current_kind in SEND_AS_STL and self.current_path and not self.showing_embedded:
            file_to_send = self._stl_for_slicer()
            if not file_to_send:
                return
        elif self.current_kind == "step" and self.current_path:
            target = sl.resolve(self.settings, slicer_id)[0]
            if target and not sl.reads_step(target):     # STEP for slicers that read it, STL otherwise
                file_to_send = self._stl_for_slicer()
                if not file_to_send:
                    return
        sid, name, exe = sl.resolve(self.settings, slicer_id)
        name = self._slicer_name(sid, name)
        if not sid:
            r = QMessageBox.question(
                self, tr("No slicer found"),
                tr("No supported slicer was found on this computer.") + "\n\n"
                + tr("Open Settings to choose your slicer program?"))
            if r == QMessageBox.Yes:
                self.open_settings()
            return
        if not exe:
            r = QMessageBox.question(
                self, tr("{slicer} not found").format(slicer=name),
                tr("{slicer} could not be found automatically.").format(slicer=name) + "\n\n"
                + tr("Do you want to locate its program file yourself?"))
            if r != QMessageBox.Yes:
                return
            path, _ = QFileDialog.getOpenFileName(self, tr("Locate {slicer}").format(slicer=name),
                                                  os.environ.get("ProgramFiles", "") or os.path.expanduser("~"),
                                                  sl.program_file_filter())
            if not path:
                return
            exe = os.path.normpath(path)
            if sid == sl.CUSTOM:
                custom = dict(self.settings.get("custom_slicer") or {})
                custom["path"] = exe
                self.settings.set("custom_slicer", custom)
            else:
                paths = dict(self.settings.get("slicer_paths") or {})
                paths[sid] = exe
                self.settings.set("slicer_paths", paths)
        try:
            sl.open_in_slicer(exe, file_to_send)
        except OSError as e:
            QMessageBox.critical(self, tr("Could not start {slicer}").format(slicer=name), str(e))
            return
        if isinstance(file_to_send, list):
            what = tr("{n} models").format(n=len(file_to_send))
        else:
            what = os.path.basename(file_to_send) if file_to_send else name
        self.statusBar().showMessage(tr("Opening {file} in {slicer}…").format(file=what, slicer=name), 6000)

    # ------------------------------------------------------------ export STL
    def _set_export_visible(self, on: bool):
        """Show or hide the Export STL button. The action follows, so Ctrl+E only works when
        there is something to export."""
        self.act_export_stl.setVisible(on)
        self.export_btn_act.setVisible(on)

    def _export_default(self) -> str:
        """What a click on Export STL does (Settings -> Files): "dialog", "combined" or "per_object"."""
        mode = self.settings.get("export_mode", "dialog")
        return mode if mode in EXPORT_MODES else "dialog"

    def _mark_export_default(self):
        """In the arrow's menu, show the choice a click on the button makes in bold."""
        default = {"combined": self.act_export_one, "per_object": self.act_export_each,
                   "dialog": self.act_export_choose}[self._export_default()]
        self.export_menu.setDefaultAction(default)

    def export_stl(self, mode: str | None = None):
        """Export STL. 3MF projects: read the objects again as raw geometry (in the background;
        big projects take a moment). FreeCAD and STEP files: the solids FreeCAD made for the view,
        which are already the shapes as FreeCAD shows them.
        mode: "dialog" (choose the objects and how), "combined" (all in one STL) or "per_object"
        (one STL each); None = the choice in Settings -> Files. A file with one object is always
        saved straight away."""
        path = self.current_path
        if not path or not self.act_export_stl.isEnabled():
            return
        self._export_mode = mode if mode in EXPORT_MODES else self._export_default()
        if self.current_kind in ("freecad", "step"):
            parts = list(getattr(self.model, "parts", None) or [])
            if parts:
                self._on_export_read(path, parts)
            return
        if self.current_kind != "3mf":
            return
        self.act_export_stl.setEnabled(False)
        self.statusBar().showMessage(tr("Reading the objects of {name}…").format(name=os.path.basename(path)))

        def work():
            try:
                self._export_signals.done.emit(path, read_3mf_for_export(path))
            except Exception as e:  # noqa: BLE001 - show any error to the user
                self._export_signals.failed.emit(path, f"{type(e).__name__}: {e}")

        threading.Thread(target=work, daemon=True).start()

    def _on_export_failed(self, path: str, msg: str):
        self.act_export_stl.setEnabled(True)
        self.statusBar().clearMessage()
        if path == self.current_path:
            QMessageBox.critical(self, tr("Could not export STL"), msg)

    def _on_export_read(self, path: str, parts):
        self.act_export_stl.setEnabled(True)
        self.statusBar().clearMessage()
        if path != self.current_path:           # another file was opened meanwhile
            return
        if not parts:
            QMessageBox.information(self, tr("Export STL"),
                                    tr("This 3MF file contains no printable objects to export."))
            return
        if len(parts) == 1:                     # nothing to choose: straight to Save
            self._save_combined_stl(parts)
            return
        mode = getattr(self, "_export_mode", "dialog")
        if mode == "combined":
            self._save_combined_stl(parts)
            return
        if mode == "per_object":
            self._save_stl_per_object(parts)
            return
        dlg = ExportStlDialog(parts, self)
        if dlg.exec() != ExportStlDialog.Accepted:
            return
        chosen = dlg.selected_parts()
        if dlg.per_object():
            self._save_stl_per_object(chosen)
        else:
            self._save_combined_stl(chosen)

    def _save_combined_stl(self, parts):
        folder = self._user_folder()
        base = os.path.splitext(os.path.basename(self.current_path or "model"))[0]
        if len(parts) == 1 and self.model is not None and len(self.model.parts) > 1:
            base = os.path.splitext(stl_file_names([parts[0].name])[0])[0]
        out, _ = QFileDialog.getSaveFileName(self, tr("Export STL"), os.path.join(folder, base + ".stl"),
                                             tr("STL models") + " (*.stl)")
        if not out:
            return
        if not out.lower().endswith(".stl"):
            out += ".stl"
        try:
            write_binary_stl(parts, out)
        except OSError as e:
            QMessageBox.critical(self, tr("Could not export STL"), str(e))
            return
        self.statusBar().showMessage(tr("Saved {path}").format(path=out), 8000)

    def _save_stl_per_object(self, parts):
        start = self._user_folder()
        folder = QFileDialog.getExistingDirectory(self, tr("Choose a folder for the STL files"), start)
        if not folder:
            return
        names = stl_file_names([p.name for p in parts])
        existing = [n for n in names if os.path.exists(os.path.join(folder, n))]
        if existing:
            shown = "\n".join(existing[:10]) + ("\n…" if len(existing) > 10 else "")
            box = QMessageBox(QMessageBox.Question, tr("Export STL"),
                              tr("These files already exist in this folder:") + "\n\n" + shown, parent=self)
            replace = box.addButton(tr("Replace"), QMessageBox.AcceptRole)
            box.addButton(QMessageBox.Cancel)
            box.setDefaultButton(QMessageBox.Cancel)
            box.exec()
            if box.clickedButton() is not replace:
                return
        try:
            for part, name in zip(parts, names):
                write_binary_stl([part], os.path.join(folder, name))
        except OSError as e:
            QMessageBox.critical(self, tr("Could not export STL"), str(e))
            return
        self.statusBar().showMessage(tr("Saved {n} STL files in {folder}").format(
            n=count(len(parts)), folder=folder), 8000)

    def save_screenshot(self):
        if self.stack.currentIndex() != 1:
            return
        base = os.path.splitext(os.path.basename(self.current_path or "view"))[0]
        start = os.path.join(self._user_folder(), base + ".png")
        path, _ = QFileDialog.getSaveFileName(self, tr("Save screenshot"), start,
                                              tr("PNG image") + " (*.png)")
        if path:
            # The picture shows the model, not the view cube.
            cube_on = self.view_cube.visible
            self.view_cube.set_visible(False)
            try:
                self.plotter.screenshot(path)
            finally:
                self.view_cube.set_visible(cube_on)
                self.plotter.render()
            self.statusBar().showMessage(tr("Saved {path}").format(path=path), 6000)

    def open_settings(self, page: str = ""):
        freecad_before = self.settings.get("freecad_path", "")
        dlg = SettingsDialog(self.settings, self, renderer_info(self.plotter), page=page)
        accepted = dlg.exec()
        self.refresh_update_badge()
        if accepted and dlg.restart_now:
            # After the dialog has closed, so nothing of it is left when the window goes.
            QTimer.singleShot(0, self.restart)
            return
        if accepted:
            self._update_slicer_button()
            # FreeCAD just chosen: show the open FreeCAD file in 3D now.
            if (self.current_kind in ("freecad", "step") and self.current_path and self.model is not None
                    and not self.model.parts and self.settings.get("freecad_path", "") != freecad_before):
                self.load(self.current_path)
            if (self.scene.plate_mode, self.scene.custom_plate) != (
                    self.settings.get("plate_mode", "printer"), self._plate_size()):
                self.scene.set_plate_mode(self.settings.get("plate_mode", "printer"), self._plate_size())
                self._mark_plate_mode()
                if self.stack.currentIndex() == 1:
                    self.plotter.render()
            show_bed = bool(self.settings.get("show_bed", True))
            if self.act_bed.isChecked() != show_bed:
                self.act_bed.setChecked(show_bed)
            show_cube = bool(self.settings.get("show_view_cube", True))
            if self.view_cube.visible != show_cube:
                self.set_view_cube_visible(show_cube)
            self._apply_grid_label_settings()

    def _spacing_mm(self, key: str) -> float:
        """A grid spacing from Settings in mm, for the unit in use (0 = automatic)."""
        try:
            if units.imperial():
                return float(self.settings.get(key + "_in", 0) or 0) * units.MM_PER_IN
            return float(self.settings.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _apply_grid_settings(self, render: bool = True):
        """Settings -> Viewer: grid line spacing, the scale numbers' spacing, and whether the two
        cutting planes cut each other."""
        self.scene.grid_minor = self._spacing_mm("grid_minor")
        self.scene.grid_major = self._spacing_mm("grid_major")
        self.scene.set_planes_cut_each_other(not bool(self.settings.get("cut_planes_whole", False)))
        self.grid_labels.set_step(self._spacing_mm("grid_labels_step"))
        if render:
            self.scene.apply_plate()

    def _apply_grid_label_settings(self):
        """Settings -> Viewer: the numbers on the grid, on or off; the grid's spacings; the unit."""
        unit_changed = units.current() != self.settings.get("units", "mm")
        units.set_unit(self.settings.get("units", "mm"))
        self._apply_grid_settings()
        show_numbers = bool(self.settings.get("show_grid_labels", False))
        if self.grid_labels.enabled != show_numbers:
            self.grid_labels.set_enabled(show_numbers)
        if unit_changed:
            self._apply_units()
        if self.stack.currentIndex() == 1:
            self.plotter.render()

    def _apply_units(self):
        """Another unit: every text with a length is written again."""
        self.retranslate_ui()
        self._refresh_panel()
        self._update_clip_label()
        self._mark_plate_mode()
        if self.measure.active:
            self.measure._update()
        self.check_nozzle.set_unit(units.current())

    # ------------------------------------------------------------ updates
    def start_update_checks(self):
        """Called once the window is shown (not for --screenshot)."""
        self._update_checker = update_ui.make_checker(self.settings, self)
        self._update_checker.finished.connect(self._update_check_done)
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(3600 * 1000)        # long sessions: look again every hour
        self._update_timer.timeout.connect(self._maybe_check_updates)
        self._update_timer.start()
        QTimer.singleShot(2500, self._first_update_step)

    def _first_update_step(self):
        # The very first start opens straight to the main window, with no questions on top of
        # it: people see the program before being asked anything (and catalogue screenshots
        # such as AppImageHub's, taken on a fresh system, show the real window). The update
        # question comes on the second start, the star message on the third.
        starts = int(self.settings.get("start_count", 0) or 0) + 1
        self.settings.set("start_count", starts)
        previous = up.just_updated(self.settings)           # updated since the last start?
        if previous:
            update_ui.show_updated(self, previous)
        if starts < 2:
            return
        if starts >= 3:
            self._maybe_ask_for_star()                      # new installs, once
        if self.settings.get("update_check") is None:       # ask once
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle(tr("Check for updates?"))
            box.setText(tr("Should PrintView3D check GitHub once a day for new versions?"))
            box.setInformativeText(tr("Only the newest version number is requested. No personal data or "
                                      "files are sent. You can change this any time in Settings → Updates."))
            yes = box.addButton(tr("Yes, check daily"), QMessageBox.YesRole)
            box.addButton(tr("No, thanks"), QMessageBox.NoRole)
            box.setDefaultButton(yes)
            box.exec()
            self.settings.set("update_check", box.clickedButton() is yes)
        self._maybe_check_updates()

    def _maybe_ask_for_star(self):
        """New installs, third start: invite people to star the project on GitHub.

        Shown once, whatever is clicked. Nothing is sent anywhere; the button only opens the
        project page in the browser. Settings → About keeps the link for later.
        """
        if self.settings.get("star_prompt_shown"):
            return
        self.settings.set("star_prompt_shown", True)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle(tr("Thanks for installing PrintView3D"))
        box.setText(tr("PrintView3D is free and open source."))
        box.setInformativeText(tr("If you like it, please give it a star on GitHub. Stars help other "
                                  "people find PrintView3D and show that the project is alive."))
        star = box.addButton(tr("Star on GitHub"), QMessageBox.AcceptRole)
        box.addButton(tr("No, thanks"), QMessageBox.RejectRole)
        box.setDefaultButton(star)
        box.exec()
        if box.clickedButton() is star:
            QDesktopServices.openUrl(QUrl(up.PROJECT_URL))

    def _maybe_check_updates(self):
        if up.check_is_due(self.settings):
            self._update_checker.start()

    def _update_check_done(self, rel, _err):
        self.refresh_update_badge()
        new = up.available(self.settings)
        if new is not None:
            self.statusBar().showMessage(
                tr("PrintView3D {version} is available. Click the version in the corner to update.").format(
                    version=new.version), 15000)

    def refresh_update_badge(self):
        new = up.available(self.settings)
        if new is not None:
            link = theme.colors()["link"]
            self.version_badge.setText(
                f'<span style="color:{theme.UPDATE_DOT}">●</span> <a href="updates" style="color:{link}; '
                f'text-decoration:none"><b>v</b>{__version__} → {new.version}</a>')
            self.version_badge.setToolTip(tr("PrintView3D {version} is available. Click to update.").format(
                version=new.version))
        elif up.up_to_date(self.settings):
            self.version_badge.setText(
                f'<span style="color:{theme.UP_TO_DATE_DOT}">●</span> <a href="updates" '
                f'style="color:{theme.colors()["muted"]}; text-decoration:none"><b>v</b>{__version__}</a>')
            self.version_badge.setToolTip(tr("PrintView3D {version} is up to date. Click for update settings.")
                                          .format(version=__version__))
        else:
            self.version_badge.setText(f'<a href="updates" style="color:{theme.colors()["muted"]}; '
                                       f'text-decoration:none"><b>v</b>{__version__}</a>')
            self.version_badge.setToolTip(tr("Version {version}. Click to check for updates.").format(
                version=__version__))

    # ------------------------------------------------------------- recent
    def _refresh_recent_menu(self):
        self.recent_menu.clear()
        self._clear_layout(self.welcome_recent)
        recent = [p for p in self.settings.get("recent_files", []) if os.path.isfile(p)]
        if not recent:
            a = self.recent_menu.addAction(tr("No recent files"))
            a.setEnabled(False)
        else:
            hdr = QLabel(tr("Recent files"))
            hdr.setObjectName("muted")
            hdr.setAlignment(Qt.AlignCenter)
            self.welcome_recent.addWidget(hdr)
        for i, p in enumerate(recent):
            self.recent_menu.addAction(f"{os.path.basename(p)}   —   {os.path.dirname(p)}",
                                       lambda path=p: self.load(path))
            if i < 6:
                b = QPushButton(os.path.basename(p))
                b.setToolTip(p)
                b.setFlat(True)
                b.setObjectName("link")
                b.clicked.connect(lambda _=False, path=p: self.load(path))
                self.welcome_recent.addWidget(b)
        if recent:
            self.recent_menu.addSeparator()
            self.recent_menu.addAction(tr("Clear list"), self._clear_recent)

    def _clear_recent(self):
        self.settings.clear_recent()
        self._refresh_recent_menu()

    # ------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if u.toLocalFile().lower().endswith(SUPPORTED_EXTENSIONS + za.ARCHIVE_EXTENSIONS):
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(SUPPORTED_EXTENSIONS + za.ARCHIVE_EXTENSIONS):
                self.load(p)
                return

    # ------------------------------------------------------------ one window
    def start_file_server(self):
        """Take files opened while this window is open (double-click, "Open with")."""
        from ..single_instance import FileServer
        if self.file_server is None:
            self.file_server = FileServer(self._file_from_other_start, parent=self)
        self.file_server.listen()

    def _file_from_other_start(self, path: str):
        """A file double-clicked while PrintView3D was already open: show it here, in front."""
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        self.load(path)

    # ------------------------------------------------------------ restart
    def restart(self):
        """Start PrintView3D again with the open file, then close this one."""
        from PySide6.QtCore import QProcess
        from .. import restart
        program, args = restart.command(self.zip.path if self.zip else self.current_path)
        if self.file_server is not None:            # so the new start can take over
            self.file_server.close()
        if not QProcess.startDetached(program, args):
            if self.file_server is not None:
                self.file_server.listen()
            QMessageBox.warning(self, tr("Restart needed"),
                                tr("PrintView3D could not restart by itself. Close it and start it again."))
            return
        self.close()
        QApplication.quit()

    def closeEvent(self, e):
        try:
            self.plotter.close()
        except Exception:
            pass
        super().closeEvent(e)

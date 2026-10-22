"""Main application window."""

from __future__ import annotations

import os
import sys
import threading
from typing import Optional

import numpy as np
from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QDesktopServices, QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QSpinBox, QSplitter, QStackedWidget, QToolBar,
    QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__
from .. import freecad as fc
from .. import slicer as sl
from ..gpu import renderer_info
from ..i18n import count, ltr, num, tr
from ..loaders import (
    FEATURES, GcodeData, ModelData, SEND_AS_STL, SUPPORTED_EXTENSIONS, file_kind, load_file,
    parse_gcode_text, read_embedded_gcode,
)
from ..loaders.gcode import FEATURE_INDEX
from ..settings import Settings
from .labels import feature_label, meta_label, meta_value
from . import theme, update_ui
from .. import updates as up
from .scene import Scene
from .settings_dialog import SettingsDialog

RESOURCES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
GCODE_META_ORDER = ("Print time", "Filament (g)", "Filament (mm)", "Filament type", "Layer height",
                    "Nozzle", "Printer", "Printer profile", "Slicer")


def resource(name: str) -> str:
    return os.path.join(RESOURCES, name)


def file_filter() -> str:
    return ";;".join([
        tr("3D files") + " (*.stl *.3mf *.obj *.ply *.off *.glb *.gltf *.step *.stp *.STEP *.STP "
                         "*.gcode *.gco *.g *.FCStd *.fcstd)",
        tr("STL models") + " (*.stl)",
        tr("3MF projects") + " (*.3mf)",
        tr("Other 3D models") + " (*.obj *.ply *.off *.glb *.gltf)",
        tr("G-code") + " (*.gcode *.gco *.g)",
        tr("FreeCAD documents") + " (*.FCStd *.fcstd)",
        tr("STEP CAD files") + " (*.step *.stp *.STEP *.STP)",
        tr("All files") + " (*)",
    ])


def _swatch(color: str, size: int = 12) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(QColor(color))
    return QIcon(pm)


def _plate_name(member: str) -> str:
    """'Metadata/plate_2.gcode' -> 'Plate 2' (translated)."""
    stem = os.path.splitext(os.path.basename(member))[0]
    digits = "".join(ch for ch in stem if ch.isdigit())
    return tr("Plate {n}").format(n=digits) if digits else stem


class _LoadSignals(QObject):
    progress = Signal(int, float)
    done = Signal(int, object)
    failed = Signal(int, str)


class _KeySwallower(QObject):
    """Stops VTK's built-in single-letter shortcuts (wireframe, quit, ...)."""

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            return True
        return False


class MainWindow(QMainWindow):
    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        self.settings = settings or Settings()
        self.current_path: Optional[str] = None
        self.current_kind = ""
        self.model: Optional[ModelData] = None
        self.gcode: Optional[GcodeData] = None
        self.showing_embedded = False
        self._embedded_member = ""
        self._file_size_mb = 0.0
        self._load_token = 0

        self.setWindowTitle(APP_NAME)
        self.setObjectName("mainWindow")
        self.mica = False                   # Windows 11 Mica, switched on by enable_mica() at start
        # Windows: the .ico holds every size the taskbar and Alt+Tab need.
        self.setWindowIcon(QIcon(resource("icon.ico" if sys.platform == "win32" else "icon.png")))
        self.resize(1320, 840)
        self.setAcceptDrops(True)

        self._signals = _LoadSignals()
        self._signals.progress.connect(self._on_progress)
        self._signals.done.connect(self._on_loaded)
        self._signals.failed.connect(self._on_failed)

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
        self._update_theme_button()
        self.refresh_update_badge()
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
        self.choose_theme(theme.next_theme(theme.current()))

    def _update_theme_button(self):
        if not hasattr(self, "theme_btn"):
            return
        self.theme_btn.setIcon(theme.theme_icon())
        for key, a in self.theme_actions.items():
            a.setText(tr(theme.THEME_NAMES[key]))
            a.setChecked(key == theme.setting())
        self.act_next_theme.setText(tr("Next theme") + "\tCtrl+T")
        self.theme_btn.setToolTip(tr("Theme: {name} (Ctrl+T: next theme)").format(
            name=tr(theme.THEME_NAMES[theme.current()])))

    def _system_theme_changed(self, *_):
        if theme.setting() == "auto":
            self.apply_theme("auto")

    # =================================================================== UI
    def _build_toolbar(self):
        tb = QToolBar()
        tb.setObjectName("mainToolbar")          # the Mica style rules name it (theme.MICA_CSS)
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(tb)

        self.act_open = QAction(self, shortcut=QKeySequence.Open, triggered=self.open_dialog)
        tb.addAction(self.act_open)

        self.recent_menu = QMenu(self)
        self.recent_btn = QToolButton()
        self.recent_btn.setMenu(self.recent_menu)
        self.recent_btn.setPopupMode(QToolButton.InstantPopup)
        tb.addWidget(self.recent_btn)

        tb.addSeparator()
        self.slicer_btn = QToolButton()
        self.slicer_btn.setObjectName("slicerButton")
        self.slicer_btn.clicked.connect(lambda: self.open_in_slicer())
        # The small arrow: send the file to another slicer just once.
        self.slicer_menu = QMenu(self)
        self.slicer_menu.aboutToShow.connect(self._fill_slicer_menu)
        self.slicer_btn.setMenu(self.slicer_menu)
        self.slicer_btn.setPopupMode(QToolButton.MenuButtonPopup)
        tb.addWidget(self.slicer_btn)
        tb.addSeparator()

        self.view_actions = []
        for view, key in ((None, "F"), ("iso", "1"), ("top", "2"), ("front", "3"), ("right", "4")):
            act = QAction(self)
            act.triggered.connect(lambda _=False, v=view: self.set_view(v))
            tb.addAction(act)
            self.view_actions.append((act, key, view))

        self.act_bed = QAction(self, checkable=True)
        self.act_bed.setChecked(bool(self.settings.get("show_bed", True)))
        self.act_bed.toggled.connect(self._toggle_bed)
        tb.addAction(self.act_bed)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        self.act_screenshot = QAction(self, triggered=self.save_screenshot)
        self.act_settings = QAction(self, triggered=self.open_settings)
        self.act_about = QAction(self, triggered=lambda: self.open_settings("about"))
        for a in (self.act_screenshot, self.act_settings, self.act_about):
            tb.addAction(a)

        # Theme: icon at the end of the toolbar; its menu lists every theme.
        self.theme_menu = QMenu(self)
        self.theme_group = QActionGroup(self)
        self.theme_actions = {}
        for key in theme.THEME_NAMES:
            a = QAction(self, checkable=True)
            a.triggered.connect(lambda _=False, k=key: self.choose_theme(k))
            self.theme_group.addAction(a)
            self.theme_menu.addAction(a)
            self.theme_actions[key] = a
        self.theme_menu.addSeparator()
        self.act_next_theme = QAction(self, triggered=self.next_theme)
        self.theme_menu.addAction(self.act_next_theme)
        self.theme_btn = QToolButton()
        self.theme_btn.setObjectName("themeButton")
        self.theme_btn.setIconSize(QSize(18, 18))
        self.theme_btn.setMenu(self.theme_menu)
        self.theme_btn.setPopupMode(QToolButton.InstantPopup)
        tb.addWidget(self.theme_btn)

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
        # The 3D view, or (FreeCAD file without FreeCAD) a large preview picture.
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.plotter.interactor)
        self.view_stack.addWidget(self._build_preview_page())
        splitter.addWidget(self.view_stack)

        self.side = QWidget()
        self.side_layout = QVBoxLayout(self.side)
        self.side_layout.setContentsMargins(10, 8, 10, 10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.side)
        scroll.setMinimumWidth(290)
        scroll.setMaximumWidth(420)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1000, 310])
        self.stack.addWidget(splitter)

        self._build_side_panel()
        self.setCentralWidget(self.stack)

    def _build_side_panel(self):
        L = self.side_layout

        self.name_label = QLabel()
        self.name_label.setObjectName("fileName")
        self.name_label.setWordWrap(True)
        L.addWidget(self.name_label)
        self.kind_label = QLabel()
        self.kind_label.setObjectName("muted")
        L.addWidget(self.kind_label)

        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setObjectName("thumbnail")
        L.addWidget(self.thumb_label)

        self.details_box = QGroupBox()
        self.details_form = QFormLayout(self.details_box)
        L.addWidget(self.details_box)

        self.objects_box = QGroupBox()
        self.objects_layout = QVBoxLayout(self.objects_box)
        L.addWidget(self.objects_box)

        self.embedded_box = QGroupBox()
        self.embedded_layout = QVBoxLayout(self.embedded_box)
        L.addWidget(self.embedded_box)

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
        for act, key, _ in self.view_actions:
            QShortcut(QKeySequence(key), self, activated=act.trigger)
        QShortcut(QKeySequence(Qt.Key_Up), self, activated=lambda: self.step_layer(1))
        QShortcut(QKeySequence(Qt.Key_Down), self, activated=lambda: self.step_layer(-1))
        QShortcut(QKeySequence(Qt.Key_PageUp), self, activated=lambda: self.step_layer(10))
        QShortcut(QKeySequence(Qt.Key_PageDown), self, activated=lambda: self.step_layer(-10))
        QShortcut(QKeySequence(Qt.Key_Home), self, activated=lambda: self.set_layer(0))
        QShortcut(QKeySequence(Qt.Key_End), self, activated=lambda: self.set_layer(10 ** 9))

    # ========================================================= language
    def retranslate_ui(self):
        """(Re)set every fixed text. Called at start and when the language changes."""
        self.act_open.setText(tr("Open…"))
        self.recent_btn.setText(tr("Recent"))
        view_names = {None: tr("Fit"), "iso": tr("Iso"), "top": tr("Top"),
                      "front": tr("Front"), "right": tr("Right")}
        for act, key, view in self.view_actions:
            act.setText(view_names[view])
            act.setToolTip(tr("{view} view ({key})").format(view=view_names[view], key=key))
        self.act_bed.setText(tr("Plate"))
        self.act_bed.setToolTip(tr("Show / hide the build plate grid"))
        self.act_screenshot.setText(tr("Screenshot"))
        self.act_settings.setText(tr("Settings"))
        self.act_about.setText(tr("About"))
        self._update_theme_button()
        self.refresh_update_badge()

        self.welcome_sub.setText(tr("Drop a 3D model or G-code file here, or open one."))
        self.welcome_open.setText(tr("Open file…"))

        self.details_box.setTitle(tr("Details"))
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
        self.name_label.setText("")
        self.kind_label.setText("")
        self.thumb_label.hide()
        while self.details_form.rowCount():
            self.details_form.removeRow(0)
        self._clear_layout(self.objects_layout)
        self._clear_layout(self.embedded_layout)
        self._clear_layout(self.features_layout)
        self.feature_checks = {}
        for box in (self.objects_box, self.embedded_box, self.layers_box, self.features_box):
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
            self.name_label.setText(os.path.basename(self.current_path or ""))
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
            self.name_label.setText(os.path.basename(self.current_path or ""))
            self._fill_model_panel(self.model)
            if self.view_stack.currentIndex() == 1:
                self._show_freecad_preview(self.model)

    def _add_detail(self, key: str, value: str):
        k = QLabel(key)
        k.setObjectName("formKey")
        v = QLabel(str(value))
        v.setWordWrap(True)
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.details_form.addRow(k, v)

    def _set_thumbnail(self, data: Optional[bytes]):
        if not data:
            self.thumb_label.hide()
            return
        pm = QPixmap()
        if pm.loadFromData(data) and not pm.isNull() and pm.width() > 8:
            self.thumb_label.setPixmap(pm.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.thumb_label.show()
        else:
            self.thumb_label.hide()

    def _kind_text(self) -> str:
        if self.showing_embedded:
            return tr("Sliced toolpaths · {plate}").format(plate=_plate_name(self._embedded_member))
        names = {"stl": "STL", "3mf": "3MF", "obj": "OBJ", "ply": "PLY", "off": "OFF", "gltf": "glTF",
                 "gcode": tr("G-code"), "freecad": "FreeCAD", "step": "STEP"}
        return tr("{kind} · {size} MB").format(kind=names.get(self.current_kind, self.current_kind.upper()),
                                               size=num(self._file_size_mb, 1))

    # ============================================================ loading
    def open_dialog(self):
        start = os.path.dirname(self.current_path) if self.current_path else ""
        if not start:
            recent = self.settings.get("recent_files", [])
            start = os.path.dirname(recent[0]) if recent else os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(self, tr("Open 3D file"), start, file_filter())
        if path:
            self.load(path)

    def load(self, path: str):
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            QMessageBox.warning(self, tr("File not found"),
                                tr("The file no longer exists:") + f"\n{path}")
            return
        kind = file_kind(path)
        if not kind:
            QMessageBox.warning(self, tr("Unsupported file"),
                                tr("PrintView3D can open STL, 3MF, OBJ, PLY, OFF, glTF/GLB, STEP, G-code and FreeCAD files."))
            return
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

    def load_sync(self, path: str):
        """Load without a worker thread (used for --screenshot)."""
        path = os.path.abspath(path)
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
        path, kind, data = payload
        self.progress.hide()
        self.slicer_btn.setEnabled(True)
        self.current_path = path
        self.current_kind = kind
        self._file_size_mb = os.path.getsize(path) / (1024 * 1024)
        self.showing_embedded = False
        self.settings.add_recent(path)
        self._refresh_recent_menu()
        self.setWindowTitle(f"{os.path.basename(path)} — {APP_NAME}")
        self.stack.setCurrentIndex(1)

        self.scene.clear()
        self.view_stack.setCurrentIndex(0)
        self._reset_side_panel()
        self.name_label.setText(os.path.basename(path))

        if isinstance(data, GcodeData):
            self.model = None
            self._show_gcode(data)
        else:
            self.model = data
            self.gcode = None
            self._show_model(data)
        self.scene.set_bed_visible(self.act_bed.isChecked())
        self.scene.set_view("iso")
        self._update_slicer_button()
        msg = tr("Opened {path}").format(path=path)
        if kind in ("freecad", "step") and not getattr(data, "parts", None):
            msg = self._freecad_status_text(data)
        self.statusBar().showMessage(msg, 10000)

    # ------------------------------------------------------------- model
    def _show_model(self, m: ModelData):
        self._model_actors = self.scene.show_model(m)
        if m.freecad is not None and not m.parts:   # FreeCAD file without FreeCAD
            self._show_freecad_preview(m)
        self._fill_model_panel(m)

    def _fill_model_panel(self, m: ModelData):
        self.kind_label.setText(self._kind_text())
        if m.freecad is not None and not m.parts:
            self.thumb_label.hide()                 # shown large on the preview page
        else:
            self._set_thumbnail(m.thumbnail)
        actors = getattr(self, "_model_actors", [])
        b = m.bounds()
        if b:
            self._add_detail(tr("Size (X×Y×Z)"), ltr(tr("{x} × {y} × {z} mm").format(
                x=num(b[1] - b[0]), y=num(b[3] - b[2]), z=num(b[5] - b[4]))))
        if b and max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) < 1.0:
            self._add_detail(tr("Note"), tr("Very small: the file may use metres instead of millimetres. "
                                            "Your slicer can scale it."))
        if m.parts:
            self._add_detail(tr("Triangles"), count(m.n_triangles))
        if len(m.parts) == 1:
            vol = self._mesh_volume(m.parts[0])
            if vol:
                self._add_detail(tr("Volume"), tr("{v} cm³").format(v=num(vol / 1000)))
        for k, v in m.meta.items():
            self._add_detail(meta_label(k), meta_value(v))

        if len(m.parts) > 1:
            for i, (part, actor) in enumerate(zip(m.parts, actors)):
                cb = QCheckBox(tr("{name}  ({n} triangles)").format(name=part.name, n=count(part.n_triangles)))
                cb.setIcon(_swatch(Scene.part_color(part, i, len(m.parts))))
                cb.setChecked(bool(actor.GetVisibility()))
                cb.toggled.connect(lambda on, a=actor: (a.SetVisibility(on), self.plotter.render()))
                self.objects_layout.addWidget(cb)
            self.objects_box.setTitle(tr("Objects ({n})").format(n=len(m.parts)))
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
        self.name_label.setText(os.path.basename(self.current_path or ""))
        self._show_gcode(g)
        self.scene.set_bed_visible(self.act_bed.isChecked())
        self.scene.set_view("iso")
        self.statusBar().clearMessage()

    # ------------------------------------------------------------- gcode
    def _show_gcode(self, g: GcodeData):
        self.gcode = g
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
        self._set_thumbnail(g.thumbnail)

        b = g.extrusion_bounds
        if b:
            self._add_detail(tr("Print size"), ltr(tr("{x} × {y} × {z} mm").format(
                x=num(b[1] - b[0], 1), y=num(b[3] - b[2], 1), z=num(b[5]))))
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
        self.layer_info.setText(tr("<b>Layer {n}</b> of {total}  ·  Z = {z} mm").format(
            n=count(i + 1), total=count(g.n_layers), z=num(g.layer_z[i])))

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

    # ============================================================ actions
    def set_view(self, view: Optional[str]):
        if self.stack.currentIndex() != 1:
            return
        self.scene.set_view(view or self.scene._view)

    def _toggle_bed(self, on: bool):
        self.scene.set_bed_visible(on)
        self.settings.set("show_bed", on)
        self.plotter.render()

    # ------------------------------------------------------------ slicer
    def _slicer_name(self, sid: str, name: str) -> str:
        return tr("custom slicer") if (sid == sl.CUSTOM and name == "custom slicer") else name

    def _update_slicer_button(self):
        if self.current_kind == "freecad" and not self.showing_embedded:
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
        self.slicer_menu.addSeparator()
        self.slicer_menu.addAction(tr("Choose default slicer…"), self.open_settings)

    def open_in_slicer(self, slicer_id: Optional[str] = None):
        file_to_send = self.current_path
        if self.current_kind == "freecad" and self.current_path:
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
        what = os.path.basename(file_to_send) if file_to_send else name
        self.statusBar().showMessage(tr("Opening {file} in {slicer}…").format(file=what, slicer=name), 6000)

    def save_screenshot(self):
        if self.stack.currentIndex() != 1:
            return
        base = os.path.splitext(os.path.basename(self.current_path or "view"))[0]
        start = os.path.join(os.path.dirname(self.current_path or os.path.expanduser("~")), base + ".png")
        path, _ = QFileDialog.getSaveFileName(self, tr("Save screenshot"), start,
                                              tr("PNG image") + " (*.png)")
        if path:
            self.plotter.screenshot(path)
            self.statusBar().showMessage(tr("Saved {path}").format(path=path), 6000)

    def open_settings(self, page: str = ""):
        freecad_before = self.settings.get("freecad_path", "")
        dlg = SettingsDialog(self.settings, self, renderer_info(self.plotter), page=page)
        accepted = dlg.exec()
        self.refresh_update_badge()
        if accepted:
            self._update_slicer_button()
            # FreeCAD just chosen: show the open FreeCAD file in 3D now.
            if (self.current_kind in ("freecad", "step") and self.current_path and self.model is not None
                    and not self.model.parts and self.settings.get("freecad_path", "") != freecad_before):
                self.load(self.current_path)
            show_bed = bool(self.settings.get("show_bed", True))
            if self.act_bed.isChecked() != show_bed:
                self.act_bed.setChecked(show_bed)

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
                if u.toLocalFile().lower().endswith(SUPPORTED_EXTENSIONS):
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(SUPPORTED_EXTENSIONS):
                self.load(p)
                return

    def closeEvent(self, e):
        try:
            self.plotter.close()
        except Exception:
            pass
        super().closeEvent(e)

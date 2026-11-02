"""Settings dialog: a sidebar with one page per topic.

Language · Appearance · Slicer · FreeCAD · Files (default program) · Viewer (and graphics) ·
Updates · About. MainWindow.open_settings(page="updates") opens a given page.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QDateTime, QLocale, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from .. import APP_NAME, __version__, file_assoc, gpu, i18n
from .. import updates as up
from .. import freecad as fc
from .. import slicer as sl
from ..i18n import tr
from . import theme
from . import update_ui
from .labels import assoc_status, plate_mode_label

PAGES = ["language", "appearance", "slicer", "freecad", "files", "viewer", "updates", "about"]


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None, gpu_info=None, page: str = ""):
        super().__init__(parent)
        self.settings = settings
        self.restart_now = False            # OK chose "Restart now" (MainWindow.open_settings restarts)
        self.setWindowTitle(tr("Settings"))
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        outer = QVBoxLayout(self)
        body = QHBoxLayout()
        outer.addLayout(body, 1)
        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setIconSize(QSize(20, 20))
        self.nav.setFixedWidth(200)
        self.nav.setUniformItemSizes(True)
        self.nav.setSpacing(1)
        self.pages = QStackedWidget()
        body.addWidget(self.nav)
        body.addWidget(self.pages, 1)
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self._page_keys: list[str] = []

        # ---------------- Language ----------------
        g0 = QGroupBox(tr("Language"))
        l0 = QFormLayout(g0)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(tr("Automatic (system language)"), "auto")
        completion = i18n.completion()
        for code, name in i18n.LANGUAGES.items():
            label = name
            if code != "en" and completion.get(code, 0) < 50:
                label += "  " + tr("(incomplete)")
            self.lang_combo.addItem(label, code)
        self.lang_combo.setCurrentIndex(max(0, self.lang_combo.findData(settings.get("language", "en"))))
        k0 = QLabel(tr("Language"))
        k0.setObjectName("formKey")
        l0.addRow(k0, self.lang_combo)
        guide = f'<a href="{up.TRANSLATING_URL}">{tr("How to translate on GitHub")}</a>'
        help_lbl = QLabel(tr("Missing or wrong translation? Anyone can correct it on GitHub: {guide}")
                          .format(guide=guide))
        help_lbl.setObjectName("muted")
        help_lbl.setWordWrap(True)
        help_lbl.setOpenExternalLinks(True)
        l0.addRow(help_lbl)
        self._add_page("language", tr("Language"), [g0])

        # ---------------- Appearance ----------------
        # A mode (Light / Dark / System) and four style cards, each a small picture of PrintView3D
        # in that style and mode. Clicking switches every window right away; Cancel puts back the
        # theme from when Settings opened.
        gt = QGroupBox(tr("Theme"))
        lt = QVBoxLayout(gt)
        lt.setSpacing(10)
        self._theme_at_open = settings.get("theme", "auto")
        if not theme.is_valid_choice(self._theme_at_open):
            self._theme_at_open = "auto"
        self._theme_choice = self._theme_at_open
        self._style, self._mode = theme.split_choice(self._theme_at_open)
        mode_row = QHBoxLayout()
        self.mode_selector = Segmented([(m, tr(theme.MODE_NAMES[m]), m) for m in theme.MODES])
        self.mode_selector.set_value(self._mode)
        self.mode_selector.changed.connect(self._choose_mode)
        mode_row.addWidget(self.mode_selector)
        mode_hint = QLabel(tr("System follows the light or dark setting of your computer."))
        mode_hint.setObjectName("muted")
        mode_hint.setWordWrap(True)
        mode_row.addSpacing(8)
        mode_row.addWidget(mode_hint, 1)
        lt.addLayout(mode_row)
        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_cards: dict[str, QToolButton] = {}
        for style in theme.STYLES:
            card = QToolButton()
            card.setObjectName("themeCard")
            card.setCheckable(True)
            card.setCursor(Qt.PointingHandCursor)
            card.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            card.setIconSize(QSize(112, 70))
            card.setText(tr(theme.STYLE_NAMES[style]))
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            card.setChecked(style == self._style)
            card.clicked.connect(lambda _=False, k=style: self._choose_style(k))
            self.theme_group.addButton(card)
            self.theme_cards[style] = card
            cards.addWidget(card)
        self._draw_theme_cards()
        lt.addLayout(cards)
        theme_note = QLabel(tr("Pick a style and a mode to try it right away. OK keeps it, Cancel goes back."))
        theme_note.setObjectName("muted")
        theme_note.setWordWrap(True)
        lt.addWidget(theme_note)

        ga = QGroupBox(tr("Window transparency"))
        la = QVBoxLayout(ga)
        la.setSpacing(8)
        from .. import win_mica
        self.backdrop_selector = Segmented([("off", tr("Off"), "off"), ("mica", tr("Mica"), "mica"),
                                            ("acrylic", tr("Acrylic"), "acrylic")])
        self.backdrop_selector.set_value(win_mica.choice(settings) if win_mica.supported() else "off")
        self.backdrop_selector.setEnabled(win_mica.supported())
        backdrop_row = QHBoxLayout()
        backdrop_row.addWidget(self.backdrop_selector)
        backdrop_hint = QLabel(tr("Mica: a soft tint of your wallpaper. Acrylic: frosted glass."))
        backdrop_hint.setObjectName("muted")
        backdrop_hint.setWordWrap(True)
        backdrop_row.addSpacing(8)
        backdrop_row.addWidget(backdrop_hint, 1)
        la.addLayout(backdrop_row)
        mica_note = QLabel(tr("Windows 11 only. Takes effect after restarting PrintView3D. Windows shows a "
                              "plain colour while the window is not active.")
                           if win_mica.supported() else tr("Needs Windows 11."))
        mica_note.setObjectName("muted")
        mica_note.setWordWrap(True)
        la.addWidget(mica_note)
        self._add_page("appearance", tr("Appearance"), [gt, ga], keep_titles=True)

        # ---------------- Slicer ----------------
        self._paths = dict(settings.get("slicer_paths") or {})
        self._custom = dict(settings.get("custom_slicer") or {})
        self._installed = sl.detect_installed(self._paths)
        g1 = QGroupBox(tr("Slicer"))
        l1 = QVBoxLayout(g1)
        form = QFormLayout()
        self.slicer_combo = QComboBox()
        for s_ in sl.SLICERS:
            tag = tr("installed") if s_.id in self._installed else tr("not found")
            self.slicer_combo.addItem(f"{s_.name}   ({tag})", s_.id)
        self.slicer_combo.addItem(tr("Custom program…"), sl.CUSTOM)
        k = QLabel(tr("Default slicer"))
        k.setObjectName("formKey")
        form.addRow(k, self.slicer_combo)
        self.custom_name = QLineEdit(self._custom.get("name", ""))
        self.custom_name.setPlaceholderText(tr("Name shown on the button, e.g. SuperSlicer"))
        self.custom_name_label = QLabel(tr("Name"))
        self.custom_name_label.setObjectName("formKey")
        form.addRow(self.custom_name_label, self.custom_name)
        l1.addLayout(form)
        row = QHBoxLayout()
        self.slicer_edit = QLineEdit()
        browse = QPushButton(tr("Browse…"))
        browse.clicked.connect(self._browse)
        self.detect_btn = QPushButton(tr("Detect"))
        self.detect_btn.clicked.connect(self._detect)
        row.addWidget(self.slicer_edit, 1)
        row.addWidget(browse)
        row.addWidget(self.detect_btn)
        l1.addLayout(row)
        self.slicer_status = QLabel()
        self.slicer_status.setObjectName("muted")
        self.slicer_status.setWordWrap(True)
        l1.addWidget(self.slicer_status)
        self._add_page("slicer", tr("Slicer"), [g1])

        # ---------------- FreeCAD ----------------
        gf = QGroupBox(tr("FreeCAD"))
        lf = QVBoxLayout(gf)
        fc_help = QLabel(tr("FreeCAD files (.FCStd) are shown in 3D with the help of your installed "
                            "FreeCAD. Without it, PrintView3D shows the preview picture and the object list."))
        fc_help.setObjectName("muted")
        fc_help.setWordWrap(True)
        lf.addWidget(fc_help)
        row_f = QHBoxLayout()
        self.freecad_edit = QLineEdit(settings.get("freecad_path", ""))
        self.freecad_edit.setPlaceholderText(tr("Found automatically"))
        self.freecad_edit.textChanged.connect(self._update_freecad_status)
        row_f.addWidget(self.freecad_edit, 1)
        fb = QPushButton(tr("Browse…"))
        fb.clicked.connect(self._browse_freecad)
        row_f.addWidget(fb)
        lf.addLayout(row_f)
        self.freecad_status = QLabel()
        self.freecad_status.setObjectName("muted")
        self.freecad_status.setWordWrap(True)
        lf.addWidget(self.freecad_status)
        self._add_page("freecad", tr("FreeCAD"), [gf])
        self._update_freecad_status()

        current_id = sl.resolve(settings, installed=self._installed)[0] or sl.SLICERS[0].id
        self._current_id = current_id
        self.slicer_combo.setCurrentIndex(max(0, self.slicer_combo.findData(current_id)))
        self._load_slicer_fields()
        self.slicer_combo.currentIndexChanged.connect(self._slicer_changed)
        self.slicer_edit.textChanged.connect(self._update_slicer_status)

        # ---------------- Opening files ----------------
        go = QGroupBox(tr("Opening files"))
        lo = QVBoxLayout(go)
        self.new_window_cb = QCheckBox(tr("Open each file in a new window"))
        self.new_window_cb.setChecked(bool(settings.get("new_window", False)))
        lo.addWidget(self.new_window_cb)
        nw_note = QLabel(tr("Off: a file you double-click while PrintView3D is open is shown in the window "
                            "that is already open. On: every file gets its own window. Starting "
                            "PrintView3D without a file always opens a new window."))
        nw_note.setObjectName("muted")
        nw_note.setWordWrap(True)
        lo.addWidget(nw_note)

        # ---------------- Export STL ----------------
        ge = QGroupBox(tr("Export STL"))
        le = QFormLayout(ge)
        self.export_combo = QComboBox()
        for label, mode in ((tr("Show the list of objects"), "dialog"),
                            (tr("Save everything as one STL"), "combined"),
                            (tr("Save one STL per object"), "per_object")):
            self.export_combo.addItem(label, mode)
        current = settings.get("export_mode", "dialog")
        self.export_combo.setCurrentIndex(max(0, self.export_combo.findData(current)))
        ke = QLabel(tr("When I click Export STL"))
        ke.setObjectName("formKey")
        le.addRow(ke, self.export_combo)
        ex_note = QLabel(tr("{key} does the same. The arrow next to the button always offers all three "
                            "ways. A file with only one object is always saved straight away.").format(
                                key=_key("Ctrl+E")))
        ex_note.setObjectName("muted")
        ex_note.setWordWrap(True)
        le.addRow(ex_note)

        # ---------------- File associations ----------------
        g2 = QGroupBox(tr("Default program for 3D files"))
        l2 = QVBoxLayout(g2)
        if file_assoc.needs_confirmation():
            info_text = tr("Register PrintView3D so it can open .stl, .3mf and .gcode files when you "
                           "double-click them. Windows then asks you to confirm it as the default app — "
                           "that last step is done by Windows itself and can be changed back at any time.")
        else:
            info_text = tr("Add PrintView3D to your applications menu and to \"Open with\", and make it "
                           "the default app for .stl, .3mf and .gcode files. Remove registration undoes it.")
        info = QLabel(info_text + " " + tr('OBJ, PLY, OFF, glTF and STEP files are only added to "Open with".'))
        info.setWordWrap(True)
        info.setObjectName("muted")
        l2.addWidget(info)
        self.assoc_form = QFormLayout()
        self.assoc_form.setVerticalSpacing(6)
        l2.addLayout(self.assoc_form)
        self.assoc_labels = {}
        for ext in file_assoc.EXTENSIONS:
            lab = QLabel("-")
            self.assoc_labels[ext] = lab
            key = QLabel(ext)
            key.setObjectName("formKey")
            self.assoc_form.addRow(key, lab)
        btns = QHBoxLayout()
        self.reg_btn = QPushButton(tr("Register && choose as default…") if file_assoc.needs_confirmation()
                                   else tr("Register && make default"))
        self.reg_btn.setObjectName("primary")
        self.reg_btn.clicked.connect(self._register)
        self.unreg_btn = QPushButton(tr("Remove registration"))
        self.unreg_btn.clicked.connect(self._unregister)
        btns.addWidget(self.reg_btn)
        btns.addWidget(self.unreg_btn)
        btns.addStretch(1)
        l2.addLayout(btns)
        self.assoc_note = QLabel()
        self.assoc_note.setWordWrap(True)
        self.assoc_note.setObjectName("muted")
        l2.addWidget(self.assoc_note)
        # macOS gives files to the open PrintView3D by itself, so the choice does not apply there.
        self._add_page("files", tr("Files"), [ge, g2] if sys.platform == "darwin" else [go, ge, g2],
                       keep_titles=True)

        # ---------------- Viewer ----------------
        g3 = QGroupBox(tr("Viewer"))
        l3 = QVBoxLayout(g3)
        self.travel_cb = QCheckBox(tr("Show travel moves when opening G-code"))
        self.travel_cb.setChecked(bool(settings.get("show_travel")))
        self.bed_cb = QCheckBox(tr("Show build plate grid"))
        self.bed_cb.setChecked(bool(settings.get("show_bed", True)))
        self.cube_cb = QCheckBox(tr("Show the view cube (top-right corner of the 3D view)"))
        self.cube_cb.setChecked(bool(settings.get("show_view_cube", True)))
        l3.addWidget(self.travel_cb)
        l3.addWidget(self.bed_cb)
        # Which plate (also in the Plate button's menu), issue #61.
        from .scene import PLATE_MODES
        plate_form = QFormLayout()
        self.plate_combo = QComboBox()
        for mode in PLATE_MODES:
            self.plate_combo.addItem(plate_mode_label(mode).rstrip("…"), mode)
        self.plate_combo.setCurrentIndex(max(0, self.plate_combo.findData(settings.get("plate_mode", "printer"))))
        kp = QLabel(tr("Build plate"))
        kp.setObjectName("formKey")
        plate_form.addRow(kp, self.plate_combo)
        size = settings.get("plate_size", [300, 300])
        self.plate_size_row = QWidget()
        size_layout = QHBoxLayout(self.plate_size_row)
        size_layout.setContentsMargins(0, 0, 0, 0)
        self.plate_w_spin, self.plate_d_spin = QSpinBox(), QSpinBox()
        for spin, value in ((self.plate_w_spin, size[0]), (self.plate_d_spin, size[1])):
            spin.setRange(10, 5000)
            spin.setSingleStep(10)
            spin.setSuffix(" mm")
            try:
                spin.setValue(int(round(float(value))))
            except (TypeError, ValueError):
                spin.setValue(300)
        size_layout.addWidget(self.plate_w_spin)
        size_layout.addWidget(QLabel("×"))
        size_layout.addWidget(self.plate_d_spin)
        size_layout.addStretch(1)
        ks = QLabel(tr("Plate size"))
        ks.setObjectName("formKey")
        plate_form.addRow(ks, self.plate_size_row)
        self.plate_combo.currentIndexChanged.connect(
            lambda _=0: self.plate_size_row.setEnabled(self.plate_combo.currentData() == "custom"))
        self.plate_size_row.setEnabled(self.plate_combo.currentData() == "custom")
        l3.addLayout(plate_form)
        l3.addWidget(self.cube_cb)

        # ---------------- Graphics ----------------
        g4 = QGroupBox(tr("Graphics"))
        l4 = QVBoxLayout(g4)
        gpu_name = (gpu_info or {}).get("GPU") or tr("unknown")
        self.gpu_label = QLabel(tr("Drawing with: {gpu}").format(gpu=f"<b>{gpu_name}</b>"))
        self.gpu_label.setWordWrap(True)
        l4.addWidget(self.gpu_label)
        self.gpu_cb = QCheckBox(tr("Use the high-performance graphics card (recommended on laptops)"))
        self.gpu_cb.setEnabled(gpu.is_supported())
        self.gpu_cb.setChecked(gpu.high_performance_enabled())
        self.gpu_cb.setVisible(sys.platform == "win32")
        l4.addWidget(self.gpu_cb)
        if gpu.is_supported():
            hint = tr("Takes effect after restarting PrintView3D.")
        elif sys.platform == "win32":
            hint = tr("Available in the installed PrintView3D.exe.")
        else:
            hint = tr("On laptops with two graphics chips, start PrintView3D from the applications menu "
                      "(after Register on the Files page) — the menu entry asks for the dedicated GPU — or "
                      "use your desktop's \"Launch using Dedicated Graphics Card\" option.")
        if gpu.looks_integrated(gpu_name):
            hint = tr("This looks like the built-in (slower) graphics. Tick the box and restart "
                      "for smoother rotation.") + " " + hint
        self.gpu_hint = QLabel(hint)
        self.gpu_hint.setWordWrap(True)
        self.gpu_hint.setObjectName("muted")
        l4.addWidget(self.gpu_hint)
        self._add_page("viewer", tr("Viewer"), [g3, g4], keep_titles=True)

        self._add_page("updates", tr("Updates"), [self._build_updates()])
        self._add_page("about", tr("About"), [self._build_about(gpu_info), self._build_shortcuts()],
                       keep_titles=True)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setObjectName("primary")     # in the theme's primary colour
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        outer.addWidget(bb)

        self._update_assoc_status()
        self._refresh_updates()
        self.nav.setCurrentRow(self._page_keys.index(page) if page in self._page_keys else 0)
        self._initial_size()

    # ---------------------------------------------------------------- pages
    def _add_page(self, key: str, title: str, widgets: list, keep_titles: bool = False):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(16, 0, 6, 0)
        head = QLabel(title)
        head.setObjectName("pageTitle")
        v.addWidget(head)
        for w in widgets:
            if isinstance(w, QGroupBox) and not keep_titles:
                w.setTitle("")                          # the page title already says it
            v.addWidget(w)
        v.addStretch(1)
        scroll = QScrollArea()                          # long pages scroll on small screens
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        self.pages.addWidget(scroll)
        item = QListWidgetItem(theme.nav_icon(key), title)
        item.setData(Qt.UserRole, key)
        # Fixed row height. (Height from style-sheet padding is measured differently by
        # Windows' drawing, which made the highlight bigger than its row.)
        item.setSizeHint(QSize(0, self.nav.fontMetrics().height() + 20))
        self.nav.addItem(item)
        self._page_keys.append(key)

    def _initial_size(self):
        screen = (self.parent().screen() if self.parent() is not None else QApplication.primaryScreen())
        avail = screen.availableGeometry() if screen is not None else None
        w, h = 860, 580
        if avail is not None:
            w, h = min(w, int(avail.width() * 0.9)), min(h, int(avail.height() * 0.9))
        self.resize(w, h)

    def show_page(self, key: str):
        if key in self._page_keys:
            self.nav.setCurrentRow(self._page_keys.index(key))

    # -------------------------------------------------------------- updates
    def _build_updates(self) -> QGroupBox:
        g = QGroupBox()
        v = QVBoxLayout(g)
        self.upd_version = QLabel()
        v.addWidget(self.upd_version)
        self.upd_status = QLabel()
        self.upd_status.setObjectName("muted")
        self.upd_status.setWordWrap(True)
        v.addWidget(self.upd_status)
        row = QHBoxLayout()
        self.upd_install = QPushButton(update_ui.install_button_text())
        self.upd_install.setObjectName("primary")
        self.upd_install.clicked.connect(self._install_update)
        self.upd_notes = QPushButton(tr("What's new"))
        self.upd_notes.clicked.connect(lambda: self._available and update_ui.show_whats_new(self, self._available))
        self.upd_skip = QPushButton(tr("Skip this version"))
        self.upd_skip.clicked.connect(self._skip_update)
        self.upd_check = QPushButton(tr("Check for updates now"))
        self.upd_check.clicked.connect(self._check_now)
        for b in (self.upd_install, self.upd_notes, self.upd_skip, self.upd_check):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        v.addSpacing(6)
        self.upd_auto = QCheckBox(tr("Check for updates automatically (once a day)"))
        self.upd_auto.setChecked(up.auto_check_enabled(self.settings))
        v.addWidget(self.upd_auto)
        note = QLabel(tr("Only asks GitHub for the newest version number. No personal data or files "
                         "are sent.") + f' <a href="{up.PRIVACY_URL}">' + tr("Read more") + "</a>")
        note.setObjectName("muted")
        note.setWordWrap(True)
        note.setOpenExternalLinks(True)
        v.addWidget(note)
        if up.install_kind() != "installer":
            how = QLabel(tr("This copy of PrintView3D is not the installed Windows version, so updates "
                            "open the download page."))
            how.setObjectName("muted")
            how.setWordWrap(True)
            v.addWidget(how)
        self._checker = update_ui.make_checker(self.settings, self)
        self._checker.finished.connect(self._check_done)
        return g

    def _refresh_updates(self, checking: bool = False):
        self._available = up.available(self.settings)
        rel = self._available
        last = float(self.settings.get("update_last_check") or 0)
        when = self._when(last) if last else tr("never")
        ok = float(self.settings.get("update_last_ok") or 0)
        if rel:
            self.upd_version.setText(f'<span style="color:{theme.UPDATE_DOT}">●</span>&nbsp; '
                                     + tr("<b>Version {new} is available</b> (you have {current})").format(
                                         new=rel.version, current=__version__))
        elif up.up_to_date(self.settings):
            self.upd_version.setText(f'<span style="color:{theme.UP_TO_DATE_DOT}">●</span>&nbsp; '
                                     + tr("You have version {version}").format(version=f"<b>{__version__}</b>"))
        else:
            self.upd_version.setText(tr("You have version {version}").format(version=f"<b>{__version__}</b>"))
        if checking:
            self.upd_status.setText(tr("Checking…"))
        elif rel:
            self.upd_status.setText(tr("Last checked: {when}").format(when=when))
        elif ok and ok >= last:
            self.upd_status.setText("✔ " + tr("You are up to date · last checked {when}").format(when=when))
        elif last:                          # the last check could not reach GitHub
            self.upd_status.setText(tr("Could not check for updates · last tried {when}").format(when=when))
        else:
            self.upd_status.setText(tr("Not checked yet."))
        for b in (self.upd_install, self.upd_notes, self.upd_skip):
            b.setVisible(bool(rel))
        self.upd_check.setEnabled(not checking)
        row = self._page_keys.index("updates") if "updates" in self._page_keys else -1
        if row >= 0:
            self.nav.item(row).setIcon(theme.nav_icon("updates", dot=bool(rel)))

    # ---------------------------------------------------------------- theme
    def _apply_theme_now(self, choice: str):
        """Switch every window (and the 3D view) to the theme, as the toolbar button does."""
        parent = self.parent()
        if hasattr(parent, "apply_theme"):
            parent.apply_theme(choice)
        else:
            theme.apply_theme(QApplication.instance(), choice)
        for row in range(self.nav.count()):                 # sidebar icons take the new text colour
            key = self.nav.item(row).data(Qt.UserRole)
            dot = key == "updates" and bool(getattr(self, "_available", None))
            self.nav.item(row).setIcon(theme.nav_icon(key, dot=dot))

    def _choose_theme(self, choice: str):
        """Show the theme now (OK keeps it, Cancel goes back)."""
        self._style, self._mode = theme.split_choice(choice)
        self.theme_cards[self._style].setChecked(True)
        self.mode_selector.set_value(self._mode)
        if choice != self._theme_choice:
            self._theme_choice = choice
            self._apply_theme_now(choice)
        self._draw_theme_cards()

    def _choose_style(self, style: str):
        """A style card was clicked."""
        self._choose_theme(theme.make_choice(style, self._mode))

    def _choose_mode(self, mode: str):
        """Light, Dark or System was clicked: the same style in that mode."""
        self._choose_theme(theme.make_choice(self._style, mode))

    def _draw_theme_cards(self):
        """Each card shows its style in the chosen mode (System: as the computer is set now)."""
        for style, card in self.theme_cards.items():
            name = theme.theme_for(style, self._mode)
            card.setIcon(QIcon(theme.theme_preview(name, 112, 70)))
            card.setToolTip(theme.display_name(name))
        for selector in (self.mode_selector, getattr(self, "backdrop_selector", None)):
            if selector is not None:
                selector.refresh_icons()                    # their symbols use the text colour

    def theme_choice(self) -> str:
        """The theme chosen on the Appearance page."""
        return self._theme_choice

    def reject(self):
        """Cancel, Esc or the window's cross: back to the theme from when Settings opened."""
        if self._theme_choice != self._theme_at_open:
            self._choose_theme(self._theme_at_open)
        super().reject()

    @staticmethod
    def _when(ts: float) -> str:
        """'today 14:02' or '14 Nov 2026, 14:02' in the user's language."""
        dt = QDateTime.fromSecsSinceEpoch(int(ts))
        loc = QLocale()
        hm = loc.toString(dt.time(), "HH:mm")
        if dt.date() == QDateTime.currentDateTime().date():
            return tr("today {time}").format(time=hm)
        return loc.toString(dt.date(), "d MMM yyyy") + ", " + hm

    def _check_now(self):
        self._refresh_updates(checking=True)
        self._checker.start()

    def _check_done(self, rel, err):
        self._refresh_updates()
        if err:
            self.upd_status.setText(tr("Could not check for updates: {error}").format(error=err))
        parent = self.parent()
        if hasattr(parent, "refresh_update_badge"):
            parent.refresh_update_badge()

    def _skip_update(self):
        if self._available:
            self.settings.set("update_skip", self._available.version)
        self._refresh_updates()
        parent = self.parent()
        if hasattr(parent, "refresh_update_badge"):
            parent.refresh_update_badge()

    def _install_update(self):
        if self._available:
            self._save_update_choice()
            update_ui.install(self, self._available)

    def _save_update_choice(self):
        self.settings.set("update_check", self.upd_auto.isChecked())

    # ---------------------------------------------------------------- about
    def _build_about(self, gpu_info) -> QGroupBox:
        g = QGroupBox()
        v = QVBoxLayout(g)
        v.addWidget(QLabel(f"<b>{APP_NAME} {__version__}</b>"))
        about = QLabel(tr("A lightweight viewer for STL, 3MF and G-code files, with one-click "
                          "hand-off to your slicer (Creality Print, OrcaSlicer, Bambu Studio, "
                          "PrusaSlicer, Cura and others).") + "<br><br>"
                       + tr("Open source under the MIT License.") + "<br>"
                       + f'<a href="{up.PROJECT_URL}">github.com/{up.REPO}</a>' + "<br><br>"
                       + tr("Like PrintView3D? {star} It helps other people find it.").format(
                           star=f'<a href="{up.PROJECT_URL}">{tr("Give it a star on GitHub.")}</a>'))
        about.setWordWrap(True)
        about.setOpenExternalLinks(True)
        v.addWidget(about)
        built = QLabel(tr("Built with Python, Qt (PySide6) and PyVista / VTK.") + "<br>"
                       + "<br>".join(f"{k}: {val}" for k, val in (gpu_info or {}).items()))
        built.setObjectName("muted")
        built.setWordWrap(True)
        v.addWidget(built)
        return g

    def _build_shortcuts(self) -> QGroupBox:
        """Keyboard shortcuts and mouse controls of the main window (keep in step with
        MainWindow._build_shortcuts and the README)."""
        g = QGroupBox(tr("Keyboard and mouse"))
        grid = QGridLayout(g)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        row = 0
        for heading, items in ((tr("Keyboard"), shortcut_rows()), (tr("Mouse"), mouse_rows())):
            head = QLabel(heading)
            head.setObjectName("formKey")
            head.setStyleSheet("font-weight: 600;" + (" margin-top: 8px;" if row else ""))
            grid.addWidget(head, row, 0, 1, 2)
            row += 1
            for keys, action in items:
                caps = QWidget()
                h = QHBoxLayout(caps)
                h.setContentsMargins(0, 0, 0, 0)
                h.setSpacing(4)
                for i, k in enumerate(keys):
                    if i:
                        sep = QLabel("/")
                        sep.setObjectName("muted")
                        h.addWidget(sep)
                    cap = QLabel(i18n.ltr(k))
                    cap.setObjectName("keyCap")
                    h.addWidget(cap)
                h.addStretch(1)
                grid.addWidget(caps, row, 0)
                text = QLabel(action)
                text.setWordWrap(True)
                text.setStyleSheet("font-weight: 400;")     # not the box title's bold
                grid.addWidget(text, row, 1)
                row += 1
        return g

    # ---------------------------------------------------------------- slicer
    def _store_slicer_fields(self):
        """Remember what was typed for the slicer that is currently selected."""
        sid, txt = self._current_id, self.slicer_edit.text().strip()
        if sid == sl.CUSTOM:
            self._custom = {"name": self.custom_name.text().strip(), "path": txt}
        elif txt and txt != self._installed.get(sid, ""):
            self._paths[sid] = txt                       # manual choice
        else:
            self._paths.pop(sid, None)                   # auto-detected

    def _load_slicer_fields(self):
        sid = self._current_id
        is_custom = sid == sl.CUSTOM
        self.custom_name.setVisible(is_custom)
        self.custom_name_label.setVisible(is_custom)
        self.detect_btn.setEnabled(not is_custom)
        self.slicer_edit.blockSignals(True)
        if is_custom:
            self.slicer_edit.setText(self._custom.get("path", ""))
            self.slicer_edit.setPlaceholderText(tr("Path to the slicer program"))
        else:
            self.slicer_edit.setText(self._paths.get(sid) or self._installed.get(sid, ""))
            self.slicer_edit.setPlaceholderText(tr("Not found automatically — use Browse… to select it"))
        self.slicer_edit.blockSignals(False)
        self._update_slicer_status()

    def _slicer_changed(self, _index):
        self._store_slicer_fields()
        self._current_id = self.slicer_combo.currentData()
        self._load_slicer_fields()

    def _display_name(self, sid: str) -> str:
        if sid == sl.CUSTOM:
            return self.custom_name.text().strip() or tr("custom slicer")
        return sl.slicer_name(sid)

    def _browse(self):
        start = (os.path.dirname(self.slicer_edit.text()) or os.environ.get("ProgramFiles", "")
                 or os.path.expanduser("~"))
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Locate {slicer}").format(slicer=self._display_name(self._current_id)),
            start, sl.program_file_filter())
        if path:
            self.slicer_edit.setText(os.path.normpath(path))

    def _browse_freecad(self):
        start = (os.path.dirname(self.freecad_edit.text()) or os.environ.get("ProgramFiles", "")
                 or os.path.expanduser("~"))
        path, _ = QFileDialog.getOpenFileName(self, tr("Locate FreeCAD"), start, sl.program_file_filter())
        if path:
            self.freecad_edit.setText(os.path.normpath(path))

    def _update_freecad_status(self, *_):
        found = fc.find_freecad(self.freecad_edit.text().strip())
        if found:
            self.freecad_status.setText("✔ " + tr("FreeCAD found: {where}").format(where=found.where))
        else:
            self.freecad_status.setText(tr("FreeCAD was not found. Install it from freecad.org "
                                           "(free), or choose its program file with Browse."))

    def _detect(self):
        sid = self._current_id
        found = sl.find_slicer(sid, "")
        if found:
            self._installed[sid] = found
            self.slicer_edit.setText(found)
        else:
            QMessageBox.information(
                self, tr("Not found"),
                tr("{slicer} could not be found automatically.").format(slicer=self._display_name(sid))
                + "\n" + tr("Use Browse… to select its program file."))

    def _update_slicer_status(self):
        txt = self.slicer_edit.text().strip()
        if not txt:
            self.slicer_status.setText(tr("No program selected."))
        elif not os.path.isfile(txt):
            self.slicer_status.setText("✖ " + tr("This file does not exist"))
        elif self._current_id != sl.CUSTOM and txt == self._installed.get(self._current_id):
            self.slicer_status.setText("✔ " + tr("Detected automatically"))
        else:
            self.slicer_status.setText("✔ " + tr("Found"))

    # --------------------------------------------------------- associations
    def _update_assoc_status(self):
        supported = file_assoc.is_supported()
        self.reg_btn.setEnabled(supported)
        self.unreg_btn.setEnabled(supported and file_assoc.is_registered())
        if not supported:
            for lab in self.assoc_labels.values():
                lab.setText(tr("Not available"))
            self.assoc_note.setText(tr("File associations are available on Windows and Linux."))
            return
        for ext, st in file_assoc.status().items():
            self.assoc_labels[ext].setText(assoc_status(st))
        notes = []
        if not file_assoc.is_frozen():
            notes.append(tr("You are running from source: registration will point to this Python "
                            "installation. For everyday use, register from the built PrintView3D program."))
        else:
            reg_cmd = file_assoc.registered_command()
            if reg_cmd and file_assoc.this_program().lower() not in reg_cmd.lower():
                notes.append(tr("The registration points to a different copy of PrintView3D. "
                                "Click Register again to point it to this one."))
        self.assoc_note.setText("\n".join(notes))

    def _register(self):
        if file_assoc.needs_confirmation():
            QMessageBox.information(
                self, tr("Almost done"),
                tr("PrintView3D will be added to \"Open with\".") + "\n\n"
                + tr("Windows Settings opens next. Set PrintView3D as the default for "
                     ".stl, .3mf and .gcode there (click each file type and choose PrintView3D)."))
        try:
            file_assoc.make_default()
        except OSError as e:
            QMessageBox.warning(self, tr("Registration failed"), str(e))
            return
        self._update_assoc_status()
        if not file_assoc.needs_confirmation():
            QMessageBox.information(
                self, tr("Done"),
                tr("PrintView3D is now in your applications menu and opens .stl, .3mf and .gcode "
                   "files when you double-click them."))

    def _unregister(self):
        if QMessageBox.question(self, tr("Remove registration"),
                                tr("Remove PrintView3D from \"Open with\" and default apps?")) != QMessageBox.Yes:
            return
        file_assoc.unregister()
        self._update_assoc_status()

    # ------------------------------------------------------------------ save
    def _save(self):
        self._store_slicer_fields()
        sid = self._current_id
        if sid == sl.CUSTOM and not os.path.isfile(self._custom.get("path", "")):
            QMessageBox.warning(self, tr("Custom slicer"), tr("Select the program file of your slicer first."))
            return
        self.settings.set("slicer_id", sid)
        self.settings.set("slicer_paths", self._paths)
        self.settings.set("custom_slicer", self._custom)
        self.settings.set("freecad_path", self.freecad_edit.text().strip())
        self.settings.set("show_travel", self.travel_cb.isChecked())
        self.settings.set("show_bed", self.bed_cb.isChecked())
        self.settings.set("plate_mode", self.plate_combo.currentData())
        self.settings.set("plate_size", [self.plate_w_spin.value(), self.plate_d_spin.value()])
        self.settings.set("show_view_cube", self.cube_cb.isChecked())
        if sys.platform != "darwin":        # not on the Mac's Files page (its box is never shown)
            self.settings.set("new_window", self.new_window_cb.isChecked())
        self.settings.set("export_mode", self.export_combo.currentData())
        self._save_update_choice()
        parent = self.parent()
        restart_for = []                    # settings changed now that only apply after a restart
        if gpu.is_supported() and self.gpu_cb.isChecked() != gpu.high_performance_enabled():
            try:
                gpu.set_high_performance(self.gpu_cb.isChecked())
                if self.gpu_cb.isChecked() != getattr(parent, "gpu_at_start", not self.gpu_cb.isChecked()):
                    restart_for.append("gpu")
            except OSError as e:
                QMessageBox.warning(self, tr("Could not change graphics setting"), str(e))
        lang = self.lang_combo.currentData()
        if lang != self.settings.get("language", "en"):
            self.settings.set("language", lang)
            # Takes effect immediately: every window re-sets its texts.
            i18n.apply_language(QApplication.instance(), lang)
        if self.backdrop_selector.isEnabled():
            from .. import win_mica
            backdrop = self.backdrop_selector.value()
            before = win_mica.choice(self.settings)
            self.settings.set("backdrop", backdrop)
            if backdrop != before and backdrop != getattr(parent, "backdrop_at_start", before):
                restart_for.append("backdrop")
        choice = self._theme_choice
        if choice != self.settings.get("theme", "auto"):
            self.settings.set("theme", choice)      # already shown live (see _preview_theme)
        if restart_for:
            self.restart_now = self._ask_restart(restart_for)
        self.accept()

    def _ask_restart(self, what: list[str]) -> bool:
        """Restart now / Later. True for Restart now."""
        if what == ["backdrop"]:
            text = tr("The new window transparency is used after PrintView3D restarts.")
        elif what == ["gpu"]:
            text = tr("The new graphics card setting is used after PrintView3D restarts.")
        else:
            text = tr("The new window transparency and graphics card setting are used after "
                      "PrintView3D restarts.")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(tr("Restart needed"))
        box.setText(text)
        if getattr(self.parent(), "current_path", None):
            box.setInformativeText(tr("The open file opens again after the restart."))
        now = box.addButton(tr("Restart now"), QMessageBox.AcceptRole)
        later = box.addButton(tr("Later"), QMessageBox.RejectRole)
        box.setDefaultButton(now)
        box.setEscapeButton(later)
        box.exec()
        return box.clickedButton() is now


def _key(seq: str) -> str:
    """A shortcut as the system writes it (Ctrl+O on Windows/Linux, ⌘O on a Mac)."""
    return QKeySequence(seq).toString(QKeySequence.NativeText)


def shortcut_rows() -> list[tuple[list[str], str]]:
    """(keys, what they do) for the About page, in the order people need them."""
    view = tr("{view} view")
    return [
        ([_key("Ctrl+O")], tr("Open a file")),
        ([_key("Ctrl+W")], tr("Close the file (back to the start page)")),
        ([_key("Ctrl+P")], tr("Open the file in your slicer")),
        ([_key("Ctrl+E")], tr("Export STL (3MF, FreeCAD and STEP)")),
        ([_key("Ctrl+T")], tr("Next theme style")),
        ([_key("Ctrl+Shift+T")], tr("Switch between light and dark")),
        (["F"], view.format(view=tr("Fit"))),
        (["1"], view.format(view=tr("Iso"))),
        (["2"], view.format(view=tr("Top"))),
        (["3"], view.format(view=tr("Front"))),
        (["4"], view.format(view=tr("Right"))),
        (["W"], tr("Wireframe on / off (models)")),
        (["X"], tr("X-ray (see-through) on / off (models)")),
        (["C"], tr("Clip from the top on / off (models)")),
        (["↑", "↓"], tr("Next / previous layer (G-code), or file (ZIP)")),
        ([_key("PgUp"), _key("PgDown")], tr("10 layers up / down")),
        ([_key("Home"), _key("End")], tr("First / last layer")),
    ]


def mouse_rows() -> list[tuple[list[str], str]]:
    return [
        ([tr("Left-drag")], tr("Rotate (around the point you press on the model)")),
        ([tr("Right-drag"), tr("Middle-drag")], tr("Move (pan)")),
        ([tr("Shift + left-drag")], tr("Move (pan)")),
        ([tr("Mouse wheel")], tr("Zoom towards the mouse pointer")),
        ([tr("Click the view cube")], tr("Jump to the view of that face")),
        ([tr("Drag the view cube")], tr("Rotate (its ring: turn without tilting)")),
    ]


class Segmented(QFrame):
    """A row of choices where exactly one is chosen (Light | Dark | System), each with a small
    symbol. Looks like one control; the chosen part is filled (see theme: QFrame#segmented)."""

    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str, str]], parent=None):
        super().__init__(parent)
        self.setObjectName("segmented")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons: dict[str, QToolButton] = {}
        self._kinds: dict[str, str] = {}
        for key, text, kind in options:
            b = QToolButton()
            b.setObjectName("segment")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            b.setIconSize(QSize(16, 16))
            b.setText(text)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self._group.addButton(b)
            row.addWidget(b)
            self.buttons[key] = b
            self._kinds[key] = kind
        self.refresh_icons()

    def value(self) -> str:
        for key, b in self.buttons.items():
            if b.isChecked():
                return key
        return next(iter(self.buttons))

    def set_value(self, key: str):
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def refresh_icons(self):
        for key, b in self.buttons.items():
            b.setIcon(theme.segment_icon(self._kinds[key]))

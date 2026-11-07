"""Own keyboard shortcuts (Settings -> Keyboard and mouse), keys the system keeps, and the
start page's recent files with their preview picture."""

import base64
import os
import zipfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d import units  # noqa: E402
from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE = os.path.join(HERE, "data", "cube_binary.stl")
# A 2 x 1 PNG (red, blue).
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAIAAAB7QOjdAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAD0lE"
                       "QVQImWP4z8DAwPAfAAcAAf/89wURAAAAAElFTkSuQmCC")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    from PySide6.QtCore import QEvent
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    w.resize(1280, 800)
    w.show()
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()
    units.set_unit("mm")


def _dialog(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    return SettingsDialog(window.settings, window, {}, page="keys")


def _record(dlg, kid, seq):
    from PySide6.QtGui import QKeySequence
    dlg.key_edits[kid].setKeySequence(QKeySequence(seq))      # as if the key was pressed


# ------------------------------------------------------------------ defaults
def test_defaults(app):
    from printview3d.ui import keys
    d = keys.DEFAULT
    assert (d["view"], d["check"], d["clip_top"], d["settings"], d["fit"]) == ("V", "C", "T", "S", "F")
    assert not keys.conflicts(d)                                 # no key twice
    assert all(not keys.problem(k) for k in d.values())          # none the system keeps
    assert set(keys.descriptions()) == set(keys.IDS)
    # Written as Qt writes them ("Del", not "Delete"): otherwise a default counts as changed and
    # is saved, and Reset to defaults would not empty the setting.
    assert all(keys.normalize(k) == k for k in d.values())


def test_window_uses_the_defaults(window):
    w = window
    assert w.act_view.text() == "View (V)" and w.act_check.text() == "Check (C)"
    assert w.act_clip.shortcut().toString() == "T" and w.act_clip.text() == "Clip from the top (T)"
    assert w.act_settings.shortcut().toString() == "S" and w.act_settings in w.actions()
    assert w.act_settings.toolTip() == "Settings (S)"


# ------------------------------------------------------------------ Settings page
def test_keys_page_sits_above_updates_and_about_has_no_keys(window):
    dlg = _dialog(window)
    pages = dlg._page_keys
    assert pages.index("keys") == pages.index("updates") - 1
    assert dlg.nav.item(pages.index("keys")).text() == "Keyboard and mouse"
    about = dlg.pages.widget(pages.index("about")).widget()
    from PySide6.QtWidgets import QKeySequenceEdit, QLabel
    assert not about.findChildren(QKeySequenceEdit)
    assert not [lb for lb in about.findChildren(QLabel) if lb.objectName() == "keyCap"]
    dlg.close()


def test_own_key_is_saved_and_shown_everywhere(window):
    from PySide6.QtGui import QKeySequence, QShortcut
    w = window
    dlg = _dialog(window)
    _record(dlg, "measure", "Shift+M")
    _record(dlg, "fit", "Ctrl+Shift+F")
    dlg._save(close=True)
    assert w.settings.get("shortcuts") == {"measure": "Shift+M", "fit": "Ctrl+Shift+F"}   # only the changes
    w._settings_applied()
    assert w.act_measure.shortcut().toString() == "Shift+M"
    # as the system writes it: "Shift+M" on Windows and Linux, "⇧M" on a Mac
    shift_m, ctrl_shift_f = QKeySequence("Shift+M").toString(QKeySequence.NativeText), \
        QKeySequence("Ctrl+Shift+F").toString(QKeySequence.NativeText)
    assert w.act_measure.text() == f"Measure ({shift_m})" and w.act_measure.toolTip().endswith(f"({shift_m})")
    assert w.act_fit.text() == f"Fit ({ctrl_shift_f})"
    fit = [s for s in w.findChildren(QShortcut) if s.key() == QKeySequence("Ctrl+Shift+F")]
    assert len(fit) == 1 and not [s for s in w.findChildren(QShortcut) if s.key() == QKeySequence("F")]
    # kept for the next start
    from printview3d.ui import main_window as mw
    w2 = mw.MainWindow(w.settings)
    assert w2.act_measure.shortcut().toString() == "Shift+M"
    w2.close()
    w2.deleteLater()


def test_no_key(window):
    w = window
    dlg = _dialog(window)
    dlg.key_edits["measure"].clear()
    dlg._save(close=True)
    w._settings_applied()
    assert w.act_measure.shortcut().isEmpty() and w.act_measure.text() == "Measure"


def test_key_used_twice_is_refused(window):
    dlg = _dialog(window)
    _record(dlg, "measure", "W")                                  # W is Wireframe's
    assert dlg.key_edits["measure"].keySequence().toString() == "M"   # kept the one before
    assert not dlg.key_notes["measure"].isHidden()
    assert "Wireframe" in dlg.key_notes["measure"].text()
    _record(dlg, "measure", "N")                                  # a free one: taken, the note goes
    assert dlg._key_values["measure"] == "N" and dlg.key_notes["measure"].isHidden()
    dlg.close()


@pytest.mark.parametrize("seq, platform", [
    ("Meta+E", "win32"),            # the Windows key
    ("Meta+L", "linux"),            # Super
    ("Alt+F4", "win32"), ("Alt+Tab", "win32"), ("Ctrl+Alt+Del", "win32"), ("Ctrl+Shift+Esc", "win32"),
    ("Ctrl+Alt+T", "linux"), ("Ctrl+Alt+F2", "linux"),
    ("Ctrl+Q", "darwin"), ("Ctrl+H", "darwin"), ("Ctrl+Space", "darwin"), ("Ctrl+Shift+4", "darwin"),
    ("Tab", "win32"), ("Esc", "linux"), ("Return", "darwin"), ("Space", "win32"), ("Print", "win32"),
])
def test_system_keys_are_refused(seq, platform):
    from printview3d.ui import keys
    assert keys.problem(seq, platform)


@pytest.mark.parametrize("seq, platform", [
    ("Ctrl+Q", "win32"), ("Ctrl+H", "linux"), ("Shift+M", "darwin"), ("F5", "win32"), ("Alt+M", "win32"),
    ("Meta+E", "darwin"),           # on a Mac Qt's Meta is the Control key: Control+E is free
])
def test_other_keys_are_fine(seq, platform):
    from printview3d.ui import keys
    assert keys.problem(seq, platform) == ""


def test_system_key_refused_in_settings(window):
    dlg = _dialog(window)
    _record(dlg, "measure", "Meta+E" if os.sys.platform != "darwin" else "Ctrl+Q")
    assert dlg.key_edits["measure"].keySequence().toString() == "M"
    assert "system" in dlg.key_notes["measure"].text()
    dlg.close()


def test_reset_to_defaults(window):
    w = window
    dlg = _dialog(window)
    _record(dlg, "measure", "Shift+M")
    dlg._save(close=True)
    dlg = _dialog(window)
    assert dlg.key_edits["measure"].keySequence().toString() == "Shift+M"
    dlg.keys_reset_btn.click()
    assert dlg.key_edits["measure"].keySequence().toString() == "M"
    dlg._save(close=True)
    assert w.settings.get("shortcuts") == {}


def test_saved_junk_falls_back(window):
    from printview3d.ui import keys
    window.settings.set("shortcuts", {"measure": 5, "fit": "Ctrl+Shift+F"})
    k = keys.current(window.settings)
    assert k["measure"] == "M" and k["fit"] == "Ctrl+Shift+F"


def test_mouse_rows_are_fixed(window):
    from PySide6.QtWidgets import QKeySequenceEdit
    dlg = _dialog(window)
    assert not dlg._build_mouse().findChildren(QKeySequenceEdit)
    dlg.close()


# ------------------------------------------------------------------ start page
def test_recent_file_preview_card_stays_in_one_place(app, window, tmp_path):
    from printview3d.ui import main_window as mw
    with_pic = tmp_path / "with_picture.3mf"
    with zipfile.ZipFile(with_pic, "w") as z:
        z.writestr("3D/3dmodel.model", "<model/>")
        z.writestr("Metadata/thumbnail.png", PNG)
    gcode = tmp_path / "a much longer name of a printed file, so it wraps.gcode"
    gcode.write_text("; generated by test\n; thumbnail begin 2x1 100\n; "
                     + base64.b64encode(PNG).decode() + "\n; thumbnail end\nG1 X1 Y1\n", encoding="utf-8")
    w = window
    for p in (str(with_pic), str(gcode), CUBE):
        w.settings.add_recent(p)
    w._refresh_recent_menu()
    app.processEvents()                                        # the new list is shown and laid out
    buttons = {b.path: b for b in w.findChildren(mw._RecentButton) if not b.isHidden()}
    card = w.recent_preview
    assert card.isHidden()                                     # nothing read before the hover
    places = []
    for p, has_picture in ((str(with_pic), True), (str(gcode), True), (os.path.abspath(CUBE), False)):
        b = buttons[os.path.abspath(p)]
        assert b.toolTip() == ""                               # the card, not a tooltip
        w._recent_hover(b.path)
        assert card.isVisible() and card.path == os.path.abspath(p)
        assert (not card.picture.pixmap().isNull()) is has_picture, p
        if not has_picture:
            assert card.picture.text() == "No preview picture"
        assert card.name.text().replace("\u200b", "") == os.path.basename(p)
        assert card.folder.text().replace("\u200b", "") == os.path.dirname(os.path.abspath(p))
        places.append((card.geometry().getRect(), card.picture.geometry().getRect()))
    assert len(set(places)) == 1                               # same place, same size, every file
    # In the start page's bottom right corner.
    page = w.welcome_page
    assert page.width() - card.geometry().right() - 1 == mw.PREVIEW_MARGIN
    assert page.height() - card.geometry().bottom() - 1 == mw.PREVIEW_MARGIN
    w._recent_hover(None)
    assert card.isHidden()


def test_long_folders_wrap_and_are_shortened_to_fit(app):
    from PySide6.QtGui import QFont, QFontMetrics
    from printview3d.ui import main_window as mw
    fm = QFontMetrics(QFont())
    deep = "C:\\" + "\\".join(f"folder number {i}" for i in range(40))
    short = mw.fit_lines(deep, fm, 200, 4)
    assert "…" in short and short.startswith("C:\\folder") and short.endswith("folder number 39")
    assert mw.fit_lines("C:\\Users", fm, 200, 4) == "C:\\Users"
    assert mw.breakable_path("C:\\a/b") == "C:\\\u200ba/\u200bb"


def test_read_thumbnail(tmp_path):
    from printview3d.loaders import read_thumbnail
    gcode = tmp_path / "a.gcode"
    small, big = PNG, PNG + b"x"                               # any bytes after a PNG's end are ignored
    gcode.write_text("; thumbnail begin 1x1 10\n; " + base64.b64encode(small).decode()
                     + "\n; thumbnail end\n; thumbnail begin 4x4 10\n; " + base64.b64encode(big).decode()
                     + "\n; thumbnail end\nG1 X0\n", encoding="utf-8")
    assert read_thumbnail(str(gcode)) == big
    assert read_thumbnail(CUBE) is None
    bad = tmp_path / "bad.3mf"
    bad.write_bytes(b"not a zip")
    assert read_thumbnail(str(bad)) is None

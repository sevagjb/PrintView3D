"""The cursor while the view is turned, panned or zoomed, and Settings as a window that lets the
main window keep working."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE = os.path.join(HERE, "data", "cube_binary.stl")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    from PySide6.QtCore import QEvent
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    w.resize(1200, 760)
    w.show()
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _mouse(w, monkeypatch, start=(300, 300)):
    pos = [start]
    monkeypatch.setattr(w.controls.iren, "GetEventPosition", lambda: pos[0], raising=False)
    monkeypatch.setattr(w.controls.iren, "GetShiftKey", lambda: 0, raising=False)
    return pos


def _cursor(w):
    widget = w.plotter.interactor
    return widget.cursor() if widget.testAttribute(_qt().WA_SetCursor) else None


def _qt():
    from PySide6.QtCore import Qt
    return Qt


# ------------------------------------------------------------ cursors
def test_turning_the_view_shows_the_turn_cursor_and_gives_it_back(window, monkeypatch):
    from printview3d.ui.camera_controls import drawn_cursor
    w = window
    w.load_sync(CUBE)
    pos = _mouse(w, monkeypatch)
    assert _cursor(w) is None                                   # pointing: the normal arrow
    w.controls._left_down()
    pos[0] = (340, 310)
    w.controls._move()
    c = _cursor(w)
    assert c is not None and c.shape() == _qt().BitmapCursor
    assert c.pixmap().cacheKey() == drawn_cursor("rotate").pixmap().cacheKey()
    w.controls._button_up()
    assert _cursor(w) is None                                   # released: the normal arrow again


def test_a_click_without_moving_keeps_the_normal_cursor(window, monkeypatch):
    w = window
    w.load_sync(CUBE)
    _mouse(w, monkeypatch)
    w.controls._left_down()
    assert _cursor(w) is None                                   # pressed only: nothing changes yet
    w.controls._button_up()
    assert _cursor(w) is None


def test_panning_shows_the_move_cursor(window, monkeypatch):
    w = window
    w.load_sync(CUBE)
    pos = _mouse(w, monkeypatch)
    w.controls._pan_down()
    pos[0] = (330, 280)
    w.controls._move()
    assert _cursor(w).shape() == _qt().SizeAllCursor
    w.controls._button_up()
    assert _cursor(w) is None


def test_the_wheel_shows_the_zoom_cursor_until_it_stops(window, monkeypatch):
    from printview3d.ui.camera_controls import drawn_cursor
    w = window
    w.load_sync(CUBE)
    _mouse(w, monkeypatch)
    w.controls._wheel(1.15)
    assert _cursor(w).pixmap().cacheKey() == drawn_cursor("zoom").pixmap().cacheKey()
    assert w.controls._zoom_cursor_timer.isActive()
    w.controls._zoom_cursor_timer.timeout.emit()               # the wheel stopped
    assert _cursor(w) is None


def test_measuring_gets_its_cross_back_after_a_turn(window, monkeypatch):
    w = window
    w.load_sync(CUBE)
    w.act_measure.setChecked(True)
    pos = _mouse(w, monkeypatch, (5, 5))                        # a corner: off the model
    w.controls._left_down()
    pos[0] = (60, 40)                                           # a drag: turns the view
    w.controls._move()
    assert w.controls.mode == "rotate"
    assert _cursor(w).shape() == _qt().BitmapCursor
    w.controls._button_up()
    assert _cursor(w).shape() == _qt().CrossCursor


# ------------------------------------------------------------ Settings, not modal
@pytest.fixture
def no_gpu_info(monkeypatch):
    """The graphics card's details (for About) cannot be read from an offscreen window."""
    from printview3d.ui import main_window as mw
    monkeypatch.setattr(mw, "renderer_info", lambda plotter: {})


def test_settings_lets_the_main_window_keep_working(window, app, no_gpu_info):
    w = window
    w.open_settings()
    dlg = w.settings_dialog
    assert dlg is not None and dlg.isVisible() and not dlg.isModal()
    assert app.activeModalWidget() is None
    # Opened again: the same window, on the page asked for
    w.open_settings("about")
    assert w.settings_dialog is dlg
    assert dlg._page_keys[dlg.nav.currentRow()] == "about"
    w.load_sync(CUBE)                                           # the main window still works
    assert w.model is not None
    dlg.reject()
    app.processEvents()
    assert w.settings_dialog is None


def test_settings_ok_still_applies(window, app, no_gpu_info):
    w = window
    w.open_settings()
    dlg = w.settings_dialog
    dlg.bed_cb.setChecked(not w.act_bed.isChecked())
    want = dlg.bed_cb.isChecked()
    dlg._save()                                                 # OK
    app.processEvents()
    assert w.settings_dialog is None
    assert w.act_bed.isChecked() == want


# ------------------------------------------------------------ screenshots
def _no_capture(w, monkeypatch):
    """An offscreen test window cannot read its picture back: write a stand-in file instead."""
    monkeypatch.setattr(w.plotter, "screenshot", lambda path, *a, **k: open(path, "wb").write(b"png"))


def test_screenshot_asks_where_by_default(window, monkeypatch, tmp_path):
    from printview3d.ui import main_window as mw
    w = window
    w.load_sync(CUBE)
    _no_capture(w, monkeypatch)
    asked = []
    target = str(tmp_path / "asked.png")
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: asked.append(a) or (target, "")))
    w.save_screenshot()
    assert len(asked) == 1 and os.path.isfile(target)


def test_screenshot_saves_straight_to_the_chosen_folder(window, monkeypatch, tmp_path):
    from printview3d.ui import main_window as mw
    w = window
    w.load_sync(CUBE)
    _no_capture(w, monkeypatch)
    folder = tmp_path / "shots" / "new"                        # made when it is not there yet
    w.settings.set("screenshot_auto", True)
    w.settings.set("screenshot_folder", str(folder))
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: pytest.fail("asked although saving straight away")))
    w.save_screenshot()
    w.save_screenshot()                                        # the same second: a second name
    files = sorted(os.listdir(folder))
    assert len(files) == 2 and all(f.startswith("cube_binary ") and f.endswith(".png") for f in files)


def test_screenshot_without_a_folder_uses_pictures(window, monkeypatch, tmp_path):
    from printview3d.ui import main_window as mw
    w = window
    w.load_sync(CUBE)
    w.settings.set("screenshot_auto", True)
    monkeypatch.setattr(mw, "default_screenshot_folder", lambda: str(tmp_path / "Pictures"))
    path = w._auto_screenshot_path("model")
    assert os.path.dirname(path) == str(tmp_path / "Pictures") and path.endswith(".png")


def test_settings_files_page_has_the_screenshot_folder(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog, default_screenshot_folder
    w = window
    dlg = SettingsDialog(w.settings, w, {}, page="files")
    assert not dlg.shot_auto_cb.isChecked() and not dlg.shot_row.isEnabled()     # default: ask
    assert dlg.shot_edit.placeholderText() == default_screenshot_folder()
    dlg.shot_auto_cb.setChecked(True)
    assert dlg.shot_row.isEnabled()
    dlg.shot_edit.setText(r"C:\shots" if os.name == "nt" else "/tmp/shots")
    dlg._save(close=False)
    assert w.settings.get("screenshot_auto") is True
    assert w.settings.get("screenshot_folder") == dlg.shot_edit.text()
    dlg.reject()


# ------------------------------------------------------------ the Viewer page
def test_viewer_page_is_build_plate_tools_start_page_graphics(window):
    from PySide6.QtWidgets import QGroupBox
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    page = dlg.pages.widget(dlg._page_keys.index("viewer")).widget()
    boxes = [b for b in page.findChildren(QGroupBox) if b.parent() is page]
    assert [b.title() for b in boxes] == ["Build plate", "Measure, View and Check", "Start page", "Graphics"]
    plate, other, start = boxes[0], boxes[1], boxes[2]
    assert start.isAncestorOf(dlg.recent_preview_cb)
    for cb in (dlg.bed_cb, dlg.plate_axes_cb, dlg.grid_labels_cb, dlg.plate_combo):
        assert plate.isAncestorOf(cb)
    for cb in (dlg.travel_cb, dlg.cube_cb, dlg.line_slider, dlg.ghost_slider, dlg.plane_slider,
               dlg.cut_planes_cb, dlg.clip_handles_cb, dlg.check_colors_cb):
        assert other.isAncestorOf(cb)
    assert dlg.check_colors_cb.text() == "Remember the colours of the Check section on restart"
    dlg.reject()


def test_viewer_page_needs_no_scroll_bar(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    dlg.show()
    app.processEvents()
    scroll = dlg.pages.widget(dlg._page_keys.index("viewer"))
    fits = scroll.widget().sizeHint().height() <= scroll.viewport().height()
    # Settings may be at most 90 % of the screen's height. The offscreen screen of the tests is
    # only 800 px high, and with the taller fonts of macOS and Linux the page needs more than
    # that leaves (691 and 670 px for 665 px): there it scrolls, as on any small screen.
    limit = int(dlg.screen().availableGeometry().height() * 0.9)
    assert fits or dlg.height() >= limit - 1
    dlg.reject()


# ------------------------------------------------------------ Check model's Close
def test_check_close_shows_its_key_and_ends_check(window):
    from printview3d.ui import keys
    w = window
    w.load_sync(CUBE)
    w.act_check.setChecked(True)
    assert w.check_close_btn.text() == "Close (C)"
    w.check_close_btn.click()
    assert not w.act_check.isChecked()
    # another key for Check: the button says that one
    w.settings.set("shortcuts", {"check": "J"})
    w._apply_shortcuts()
    w.retranslate_ui()
    assert w.check_close_btn.text() == "Close (J)"
    assert keys.current(w.settings)["check"] == "J"

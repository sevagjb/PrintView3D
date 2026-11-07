"""Home (Ctrl+W): close the open file, back to the start page, and let go of the file's data."""

import gc
import os
import time
import weakref
import zipfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d import APP_NAME  # noqa: E402
from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TWO_PARTS = os.path.join(DATA, "two_parts.3mf")
GCODE = os.path.join(DATA, "cylinder.gcode")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    """A main window that is closed and really deleted afterwards."""
    from PySide6.QtCore import QEvent
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _assert_on_start_page(w):
    assert w.stack.currentIndex() == 0
    assert w.current_path is None and w.current_kind == ""
    assert w.model is None and w.gcode is None and w.zip is None
    assert w.windowTitle() == APP_NAME
    assert not w.act_home.isEnabled()
    assert not w.export_btn_act.isVisible()
    assert not w.scene.p.actors                                  # nothing left in the 3D view
    for box in (w.zip_box, w.objects_box, w.embedded_box, w.layers_box, w.features_box):
        assert box.isHidden()


def test_home_in_toolbar_and_menu_recent_in_the_menu_only(window):
    """#66: Home and Open stay next to the menu; Recent is in the menu (and on the start page)."""
    from PySide6.QtWidgets import QToolButton
    w = window
    in_toolbar = [b.defaultAction() for b in w.findChildren(QToolButton)]
    menus = [b.menu() for b in w.findChildren(QToolButton)]
    assert w.home_btn.defaultAction() is w.act_home
    assert w.act_open in in_toolbar
    assert w.recent_menu not in menus and not hasattr(w, "recent_btn")
    assert w.recent_menu.menuAction() in w.main_menu.actions()
    assert w.act_home in w.main_menu.actions()
    assert w.act_home.shortcut().toString() == "Ctrl+W"
    assert w.act_home.text() and "start page" in w.act_home.toolTip()
    assert not w.act_home.isEnabled()                            # start page: nothing to close
    w.go_home()                                                  # harmless anyway
    _assert_on_start_page(w)


@pytest.mark.parametrize("path", [TWO_PARTS, GCODE], ids=["3mf", "gcode"])
def test_home_closes_the_file_and_frees_its_data(window, path):
    w = window
    w.load_sync(path)
    assert w.stack.currentIndex() == 1 and w.act_home.isEnabled()
    data = weakref.ref(w.model if w.model is not None else w.gcode)
    w.act_home.trigger()                                         # the button or Ctrl+W
    _assert_on_start_page(w)
    gc.collect()
    assert data() is None, "the closed file's data is still held somewhere"
    # PyVista remembers the last mesh it drew; that copy must go too (a big G-code's toolpaths).
    assert getattr(w.plotter, "mesh", None) is None and getattr(w.plotter, "mapper", None) is None
    # The file just closed is first in the start page's recent list.
    assert w.settings.get("recent_files")[0] == os.path.abspath(path)
    assert w.welcome_recent.count() >= 2                         # "Recent files" + the file


def test_open_again_after_home(window):
    w = window
    w.load_sync(TWO_PARTS)
    w.go_home()
    w.load_sync(GCODE)
    assert w.stack.currentIndex() == 1 and w.current_kind == "gcode"
    assert not w.layers_box.isHidden()                           # the G-code's layer panel
    assert w.act_home.isEnabled()
    assert os.path.basename(GCODE) in w.windowTitle()


def test_home_while_a_file_is_still_loading(app, window):
    """Home pressed before a slow file has finished: the window stays on the start page."""
    w = window
    w.load(GCODE)                                                # loads in the background
    w.go_home()
    end = time.time() + 5
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)
    _assert_on_start_page(w)


def test_home_after_a_zip(window, tmp_path):
    w = window
    z = tmp_path / "models.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.write(TWO_PARTS, "two_parts.3mf")
        f.write(os.path.join(DATA, "cube_binary.stl"), "cube.stl")
    w.load_sync(str(z))
    assert w.zip is not None
    w.go_home()
    _assert_on_start_page(w)
    assert w.settings.get("recent_files")[0] == str(z)


def test_shortcut_listed_on_about_page(app):
    from printview3d.ui import keys
    assert keys.DEFAULT["home"] == "Ctrl+W"

"""Settings opens at one size from everywhere (the Settings button, Customize toolbar, Updates,
About...), and a toolbar button's right-click opens Settings at that button's own settings."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d import units  # noqa: E402
from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE = os.path.join(HERE, "data", "cube_binary.stl")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _close(app, w):
    from PySide6.QtCore import QEvent
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


@pytest.fixture
def window(app, tmp_path):
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    w.resize(1500, 800)
    w.show()
    w.load_sync(CUBE)
    app.processEvents()
    yield w
    _close(app, w)
    units.set_unit("mm")


def _open(app, settings, parent, **kw):
    from printview3d.ui.settings_dialog import SettingsDialog
    d = SettingsDialog(settings, parent, None, **kw)
    d.show()
    app.processEvents()
    return d


# ------------------------------------------------------------------ one size from everywhere
def test_settings_opens_at_the_same_size_from_every_page(app, tmp_path):
    """Opened on a page other than Viewer, the hidden Viewer page used to look wide enough, so the
    window came out narrower and Viewer's Build plate columns went one under the other."""
    from PySide6.QtWidgets import QMainWindow
    main = QMainWindow()
    main.resize(1500, 900)
    main.show()
    s = Settings(str(tmp_path / "s.json"))
    sizes, stacked = {}, {}
    for page in ("viewer", "toolbar", "updates", "about", "appearance", "files", "language"):
        d = _open(app, s, main, page=page)
        sizes[page] = (d.width(), d.height())
        d.show_page("viewer")
        app.processEvents()
        stacked[page] = d.plate_columns.stacked
        _close(app, d)
    assert len(set(sizes.values())) == 1, sizes
    assert len(set(stacked.values())) == 1, stacked
    _close(app, main)


def test_opening_on_another_page_keeps_that_page(app, tmp_path):
    from PySide6.QtWidgets import QMainWindow
    main = QMainWindow()
    main.resize(1500, 900)
    main.show()
    d = _open(app, Settings(str(tmp_path / "s.json")), main, page="toolbar")
    assert d._page_keys[d.pages.currentIndex()] == "toolbar"
    assert d._page_keys[d.nav.currentRow()] == "toolbar"
    _close(app, d)
    _close(app, main)


# ------------------------------------------------------------------ sections
@pytest.mark.parametrize("section, page", [("plate", "viewer"), ("measure", "viewer"),
                                           ("screenshots", "files"), ("export", "files")])
def test_section_opens_its_page_with_the_box_in_view(app, tmp_path, section, page):
    from PySide6.QtWidgets import QMainWindow
    main = QMainWindow()
    main.resize(1500, 900)
    main.show()
    d = _open(app, Settings(str(tmp_path / "s.json")), main, section=section)
    assert d._page_keys[d.pages.currentIndex()] == page
    _, box = d._sections[section]
    view = d.pages.currentWidget().viewport()
    top = box.mapTo(view, box.rect().topLeft()).y()
    assert 0 <= top < view.height()
    _close(app, d)
    _close(app, main)


# ------------------------------------------------------------------ toolbar right-click
def test_each_toolbar_button_offers_its_own_settings(window):
    w = window
    expect = {
        w.settings_btn: ("", ""),
        w.theme_btn: ("appearance", ""),
        w.screenshot_btn: ("", "screenshots"),
        w.slicer_btn: ("slicer", ""),
        w.export_btn: ("", "export"),
        w.plate_btn: ("", "plate"),
        w.check_btn: ("", "measure"),
        w.view_btn: ("", "measure"),
        w.measure_btn: ("", "measure"),
    }
    for b, where in expect.items():
        got = w._toolbar_button_settings(b)
        assert got is not None and got[1:] == where, (b.objectName(), got)
        assert got[0]                                           # a menu text
    for b in (w.home_btn, w.open_btn, w.toolbar.widgetForAction(w.act_fit), w.toolbar_spacer, None):
        assert w._toolbar_button_settings(b) is None


def test_right_click_finds_the_button_under_the_mouse(window):
    w, tb = window, window.toolbar
    for b in (w.theme_btn, w.measure_btn, w.plate_btn, w.screenshot_btn):
        if not b.isVisible():
            continue
        under = tb.childAt(b.mapTo(tb, b.rect().center()))
        assert w._toolbar_button_settings(under) == w._toolbar_button_settings(b)


def test_right_click_menu_has_the_buttons_settings_then_customize(window, monkeypatch):
    from PySide6.QtWidgets import QMenu
    from printview3d.ui import main_window as mw
    w, tb = window, window.toolbar
    shown = []

    class Menu(QMenu):                              # records the menu instead of showing it
        def exec(self, *a):
            shown.append(list(self.actions()))

    monkeypatch.setattr(mw, "QMenu", Menu)
    opened = []
    monkeypatch.setattr(w, "open_settings", lambda page="", section="": opened.append((page, section)))
    w._toolbar_context_menu(w.theme_btn.mapTo(tb, w.theme_btn.rect().center()))
    acts = shown[-1]
    assert len(acts) == 2 and acts[1] is w.act_customize_toolbar
    acts[0].trigger()
    assert opened == [("appearance", "")]
    w._toolbar_context_menu(w.home_btn.mapTo(tb, w.home_btn.rect().center()))
    assert shown[-1] == [w.act_customize_toolbar]

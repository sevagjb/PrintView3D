"""Settings -> Toolbar: hiding toolbar buttons (the order never changes), how the view buttons are
labelled, the joined group, the menu entries that keep everything reachable, and the Settings page
(live preview, OK keeps, Cancel goes back)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d import units  # noqa: E402
from printview3d.settings import Settings  # noqa: E402
from printview3d.ui import toolbar_prefs as tp  # noqa: E402

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
    w.resize(1500, 800)
    w.show()
    w.load_sync(CUBE)
    app.processEvents()
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()
    units.set_unit("mm")


def _shown_order(w):
    """The toolbar's visible buttons, left to right, by id."""
    tb = w.toolbar
    ids = {w.menu_btn: "menu", w.home_btn: "home", w.open_btn: "open", w.slicer_btn: "slicer",
           w.export_btn: "export", w.plate_btn: "plate", w.check_btn: "check", w.view_btn: "view",
           w.measure_btn: "measure", tb.widgetForAction(w.act_fit): "fit", w.screenshot_btn: "screenshot",
           w.theme_btn: "theme", w.settings_btn: "settings"}
    out = []
    for a in tb.actions():
        b = tb.widgetForAction(a)
        if b in ids and a.isVisible():
            out.append(ids[b])
    return out


# ------------------------------------------------------------------ the settings
def test_prefs_ignore_unknown_and_always_shown_buttons(tmp_path):
    s = Settings(str(tmp_path / "s.json"))
    s.set("toolbar_hidden", ["plate", "fit", "menu", "slicer", "export", "nonsense", "check"])
    s.set("toolbar_labels", "huge")
    assert tp.hidden(s) == {"check"} and tp.label_style(s) == "full" and not tp.joined(s)
    tp.save(s, {"settings", "home", "plate"}, "icon", True)
    assert s.get("toolbar_hidden") == ["home", "settings"]           # toolbar order, Plate dropped
    assert tp.label_style(s) == "icon" and tp.joined(s)


def test_labels_and_join_positions():
    assert tp.button_label("full", "Plate", "Plate (P)", "P") == "Plate (P)"
    assert tp.button_label("name", "Plate", "Plate (P)", "P") == "Plate"
    assert tp.button_label("key", "Plate", "Plate (P)", "P") == "P"
    assert tp.button_label("key", "Plate", "Plate", "") == "Plate"   # no key: the name stays
    assert tp.join_positions(["a"]) == {"a": "only"}
    assert tp.join_positions(["a", "b", "c"]) == {"a": "first", "b": "middle", "c": "last"}


# ------------------------------------------------------------------ the window
def test_hiding_keeps_the_order_plate_first_fit_last(window):
    full = _shown_order(window)
    assert full == [b for b, _ in tp.BUTTONS if b != "export"]     # Export STL: 3MF and CAD files only
    window.apply_toolbar_layout({"home", "check", "measure", "theme"}, "full", False)
    assert _shown_order(window) == ["menu", "open", "slicer", "plate", "view", "fit",
                                    "screenshot", "settings"]
    window.apply_toolbar_layout(set(tp.HIDEABLE), "full", False)
    assert _shown_order(window) == ["menu", "slicer", "plate", "fit"]
    window.apply_toolbar_layout(set(), "full", False)
    assert _shown_order(window) == full


def test_hidden_buttons_keep_their_keys_and_menu_entries(window):
    window.apply_toolbar_layout({"check", "view", "measure", "settings", "theme"}, "full", False)
    texts = [a.text().split("\t")[0] for a in window.main_menu.actions()]
    for name in ("Check", "View", "Measure", "Settings", "Theme", "Customize toolbar…"):
        assert name in texts, name
    assert not window.act_check.shortcut().isEmpty()                 # C still works
    window.act_check.trigger()
    assert window.menu_mirrors["check"].isChecked()                  # the menu follows the switch
    window.menu_mirrors["check"].trigger()
    assert not window.act_check.isChecked()                          # and the switch follows the menu
    assert window.menu_mirrors["check"].text() == "Check\tC"


def test_label_styles(window):
    from PySide6.QtCore import Qt
    for style, plate, fit in (("full", "Plate (P)", "Fit (F)"), ("name", "Plate", "Fit"), ("key", "P", "F")):
        window.apply_toolbar_layout(set(), style, False)
        assert window.act_bed.iconText() == plate and window.act_fit.iconText() == fit
        assert window.check_btn.toolButtonStyle() == Qt.ToolButtonTextBesideIcon
    assert window.act_check.text() == "Check (C)"                    # the full name stays for menus
    window.apply_toolbar_layout(set(), "icon", False)
    for b in window.toolbar_view_buttons.values():
        assert b.toolButtonStyle() == Qt.ToolButtonIconOnly and b.property("iconOnly") is True
        assert b.iconSize().width() == 22
    # icon only: the icons without the gap for text (square)
    pm = window.act_check.icon().availableSizes()
    assert not pm or pm[0].width() == pm[0].height()


def test_joined_group_follows_what_is_shown(window):
    tb = window.toolbar
    window.apply_toolbar_layout(set(), "name", True)
    assert tb.property("joinedGroup") is True
    pos = {k: b.property("joinPos") for k, b in window.toolbar_view_buttons.items()}
    assert pos == {"plate": "first", "check": "middle", "view": "middle", "measure": "middle", "fit": "last"}
    window.apply_toolbar_layout({"check", "view", "measure"}, "name", True)
    assert window.plate_btn.property("joinPos") == "first"
    assert tb.widgetForAction(window.act_fit).property("joinPos") == "last"
    # cube off: Iso ... Right come back and join the group at its start
    window.set_view_cube_visible(False)
    iso = next(a for a, _, v in window.view_actions if v == "iso")
    assert tb.widgetForAction(iso).property("joinPos") == "first"
    assert window.plate_btn.property("joinPos") == "middle"
    window.set_view_cube_visible(True)
    assert window.plate_btn.property("joinPos") == "first"
    window.apply_toolbar_layout(set(), "full", False)
    assert tb.property("joinedGroup") is False
    assert all(not b.property("joinPos") for b in window.toolbar_view_buttons.values())


def test_saved_choice_is_used_at_start(app, tmp_path):
    from printview3d.ui import main_window as mw
    s = Settings(str(tmp_path / "settings.json"))
    tp.save(s, {"home", "measure"}, "name", True)
    w = mw.MainWindow(s)
    try:
        w.show()
        app.processEvents()
        assert not w.toolbar_slots["home"].isVisible() and not w.toolbar_slots["measure"].isVisible()
        assert w.toolbar_slots["check"].isVisible()
        assert w.act_bed.iconText() == "Plate" and w.toolbar.property("joinedGroup") is True
    finally:
        w.close()


def test_right_click_offers_customize(window):
    from PySide6.QtCore import Qt
    assert window.toolbar.contextMenuPolicy() == Qt.CustomContextMenu
    assert window.act_customize_toolbar.text() == "Customize toolbar…"


# ------------------------------------------------------------------ the Settings page
def test_settings_page_previews_live_ok_keeps_cancel_goes_back(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog
    d = SettingsDialog(window.settings, window, page="toolbar")
    d.show()
    app.processEvents()
    assert d._page_keys[d.nav.currentRow()] == "toolbar"
    always = [cb.text() for cb in d.findChildren(type(d.toolbar_joined_cb)) if not cb.isEnabled()]
    assert any(t.startswith("Plate") for t in always) and any(t.startswith("Fit") for t in always)
    assert set(d.toolbar_checks) == set(tp.HIDEABLE)
    d.toolbar_checks["measure"].setChecked(False)
    d.toolbar_labels_combo.setCurrentIndex(tp.LABEL_STYLES.index("key"))
    app.processEvents()
    assert not window.toolbar_slots["measure"].isVisible()           # shown right away
    assert window.act_bed.iconText() == "P"
    assert d.toolbar_preview.pixmap() is not None and not d.toolbar_preview.pixmap().isNull()
    d.reject()                                                       # Cancel: back as it was
    app.processEvents()
    assert window.toolbar_slots["measure"].isVisible() and window.act_bed.iconText() == "Plate (P)"
    assert window.settings.get("toolbar_hidden") == []

    d = SettingsDialog(window.settings, window, page="toolbar")
    d.toolbar_checks["home"].setChecked(False)
    d.toolbar_joined_cb.setChecked(True)
    d._save()                                                        # OK
    app.processEvents()
    assert window.settings.get("toolbar_hidden") == ["home"] and window.settings.get("toolbar_joined")
    assert not window.toolbar_slots["home"].isVisible()

    d = SettingsDialog(window.settings, window, page="toolbar")
    d._reset_toolbar()
    d._save()
    assert window.settings.get("toolbar_hidden") == [] and not window.settings.get("toolbar_joined")
    assert window.toolbar_slots["home"].isVisible()

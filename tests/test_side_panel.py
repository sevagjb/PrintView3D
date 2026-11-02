"""The information panel: Objects stays in reach when a project has a long description or
many objects (issue #62)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
BUSY = os.path.join(DATA, "busy_project.3mf")         # 12 objects, long description
TWO_PARTS = os.path.join(DATA, "two_parts.3mf")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    from PySide6.QtCore import QEvent
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    w.resize(1280, 760)
    w.show()
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _settle(app):
    for _ in range(10):
        app.processEvents()


def _long_values(w):
    from printview3d.ui.main_window import _LongValue
    return w.details_box.findChildren(_LongValue)


def test_objects_box_comes_before_details(window, app):
    w = window
    w.load_sync(BUSY)
    _settle(app)
    L = w.side_layout
    assert L.indexOf(w.objects_box) < L.indexOf(w.details_box)


def test_objects_box_visible_without_scrolling(window, app):
    """In 0.23.0 the Objects box of this file started about 1250 px down a 700 px panel."""
    w = window
    w.load_sync(BUSY)
    _settle(app)
    assert w.objects_box.isVisible()
    top = w.objects_box.mapTo(w.side, w.objects_box.rect().topLeft()).y()
    viewport = w.side.parentWidget()
    assert top + 60 < viewport.height()                  # its title and first rows are on screen


def test_long_description_is_folded_and_unfolds(window, app):
    w = window
    w.load_sync(BUSY)
    _settle(app)
    values = _long_values(w)
    assert len(values) == 1                              # only the description is long
    desc = values[0]
    assert desc.is_clamped() and desc.toggle.isVisible()
    assert desc.label.height() <= desc.collapsed_height()
    assert "Show more" in desc.toggle.text()
    folded = desc.label.height()

    desc.toggle.linkActivated.emit("#")
    _settle(app)
    assert desc.expanded and "Show less" in desc.toggle.text()
    assert desc.label.height() > folded * 2              # the whole text

    desc.toggle.linkActivated.emit("#")
    _settle(app)
    assert not desc.expanded and desc.label.height() <= desc.collapsed_height()


def test_long_value_text_is_complete_and_selectable(window, app):
    """Folding only limits the height: copying the description still gives all of it."""
    from PySide6.QtCore import Qt
    import zipfile
    w = window
    w.load_sync(BUSY)
    _settle(app)
    desc = _long_values(w)[0]
    with zipfile.ZipFile(BUSY) as z:
        assert "No glue or screws" in z.read("3D/3dmodel.model").decode()
    assert "No glue or screws" in desc.label.text()
    assert desc.label.textInteractionFlags() & Qt.TextSelectableByMouse


def test_short_details_stay_plain(window, app):
    w = window
    w.load_sync(TWO_PARTS)
    _settle(app)
    assert _long_values(w) == []


def test_many_objects_scroll_inside_their_box(window, app):
    from PySide6.QtCore import Qt
    w = window
    w.load_sync(BUSY)
    _settle(app)
    assert w.objects_layout.count() == 12
    sa = w.objects_scroll
    assert sa.verticalScrollBarPolicy() == Qt.ScrollBarAsNeeded
    assert sa.verticalScrollBar().maximum() > 0          # 2 of the 12 rows are below
    assert sa.height() < sa.widget().sizeHint().height()


def test_few_objects_shown_in_full(window, app):
    from PySide6.QtCore import Qt
    w = window
    w.load_sync(TWO_PARTS)
    _settle(app)
    assert w.objects_layout.count() == 2
    sa = w.objects_scroll
    assert sa.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert sa.height() >= sa.widget().sizeHint().height()


def test_panel_rebuilds_in_another_language(window, app):
    """A language change rebuilds the panel: Objects is still first and the link translated."""
    import sys
    from printview3d import i18n
    sys.path.insert(0, os.path.join(HERE, "..", "tools"))
    import i18n as tool                                  # tools/i18n.py
    tool.cmd_compile()                                   # the .qm files the app loads
    w = window
    w.load_sync(BUSY)
    _settle(app)
    try:
        i18n.apply_language(app, "nl")
        w._on_language_changed()
        _settle(app)
        L = w.side_layout
        assert L.indexOf(w.objects_box) < L.indexOf(w.details_box)
        assert w.objects_layout.count() == 12
        assert "Meer tonen" in _long_values(w)[0].toggle.text()
    finally:
        i18n.apply_language(app, "en")
        w._on_language_changed()


def test_preview_picture_folds_away_and_stays_folded(window, app):
    """The file's own preview picture can be folded away with the link above it; the choice is
    remembered for the next files and the next start (issue #62)."""
    w = window
    w.load_sync(BUSY)
    _settle(app)
    assert w.thumb_toggle.isVisible() and w.thumb_label.isVisible()
    w.thumb_toggle.linkActivated.emit("#")                    # a click on the link
    _settle(app)
    assert w.thumb_toggle.isVisible() and not w.thumb_label.isVisible()
    assert w.settings.get("thumbnail_open") is False
    assert Settings(w.settings.path).get("thumbnail_open") is False   # saved
    w.load_sync(BUSY)
    _settle(app)
    assert w.thumb_toggle.isVisible() and not w.thumb_label.isVisible()
    w.thumb_toggle.linkActivated.emit("#")
    _settle(app)
    assert w.thumb_label.isVisible()


def test_no_preview_link_without_a_picture(window, app):
    w = window
    w.load_sync(TWO_PARTS)                                    # this 3MF has no picture
    _settle(app)
    assert not w.thumb_toggle.isVisible() and not w.thumb_label.isVisible()


def test_preview_link_arrow_follows_the_text_direction(window, app):
    from PySide6.QtCore import Qt
    w = window
    w.load_sync(BUSY)
    w.set_thumbnail_open(False)
    assert "▸" in w.thumb_toggle.text()
    w.setLayoutDirection(Qt.RightToLeft)
    w.set_thumbnail_open(False)
    assert "◂" in w.thumb_toggle.text()

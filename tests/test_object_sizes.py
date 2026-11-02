"""Objects list: each object's size (issue #59), and a side panel that fits its view in every
language (long field names wrap, long words break instead of being cut off)."""

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
BUSY = os.path.join(DATA, "busy_project.3mf")         # 12 cubes of 12, 18, 24 and 30 mm
LONG = os.path.join(DATA, "larger_than_plate.3mf")    # rail 420 x 40 x 12, bracket 60 x 60 x 30


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
    for _ in range(20):
        app.processEvents()


def _rows(w):
    from PySide6.QtWidgets import QCheckBox, QLabel
    out = []
    for i in range(w.objects_layout.count()):
        row = w.objects_layout.itemAt(i).widget()
        cb = row.findChild(QCheckBox)
        size = row.findChild(QLabel, "objectSize")
        out.append((cb.text(), size.text() if size else "", row.toolTip()))
    return out


def test_part_size():
    from printview3d.loaders.mesh import MeshPart
    v = np.array([[1, 2, 3], [11, 2, 3], [1, 14.5, 3], [1, 2, 33]], np.float32)
    assert MeshPart("p", v, np.zeros((0, 3), np.int64)).size() == pytest.approx((10, 12.5, 30))
    assert MeshPart("empty", np.zeros((0, 3), np.float32), np.zeros((0, 3), np.int64)).size() is None


def test_short_lengths(app):
    from printview3d import i18n
    from printview3d.ui.main_window import _short_mm, _size_mm
    assert _short_mm(12.0) == "12" and _short_mm(12.02) == "12" and _short_mm(12.5) == "12.5"
    assert _size_mm((20, 12.5, 3)) == "20 × 12.5 × 3 mm"
    try:
        i18n.apply_language(app, "nl")
        assert _short_mm(12.5) == "12,5"                 # decimal comma where that is the custom
    finally:
        i18n.apply_language(app, "en")


def test_every_object_shows_its_size(window, app):
    w = window
    w.load_sync(BUSY)
    _settle(app)
    rows = _rows(w)
    assert len(rows) == 12
    assert rows[0] == ("Base plate left", "12 × 12 × 12 mm", "Base plate left\n12 × 12 × 12 mm\n12 triangles")
    assert [r[1] for r in rows[:4]] == ["12 × 12 × 12 mm", "18 × 18 × 18 mm", "24 × 24 × 24 mm", "30 × 30 × 30 mm"]


def test_sizes_of_different_shapes(window, app):
    w = window
    w.load_sync(LONG)
    _settle(app)
    sizes = {name: size for name, size, _ in _rows(w)}
    assert sizes == {"Long shelf rail": "420 × 40 × 12 mm", "Bracket": "60 × 60 × 30 mm"}


def test_checkbox_still_hides_the_object(window, app):
    from PySide6.QtWidgets import QCheckBox
    w = window
    w.load_sync(LONG)
    _settle(app)
    cb = w.objects_box.findChildren(QCheckBox)[1]
    cb.setChecked(False)
    assert not w.scene.model_actors[1].GetVisibility()
    cb.setChecked(True)
    assert w.scene.model_actors[1].GetVisibility()


def test_long_object_names_do_not_widen_the_panel(window, app):
    w = window
    w.load_sync(BUSY)
    _settle(app)
    assert w.side.minimumSizeHint().width() <= w.side.parentWidget().width()


@pytest.mark.parametrize("code", ["en", "ar", "nl", "de", "fr", "es", "ro"])
def test_side_panel_fits_its_view_in_every_language(window, app, code):
    """In 0.24.0 the Arabic panel was 345 px wide in a 294 px view: the long field name
    "ملف تعريف الخيط (الفلمنت)" did not wrap, and right-to-left cut the overflow off on the left."""
    import sys
    from printview3d import i18n
    sys.path.insert(0, os.path.join(HERE, "..", "tools"))
    import i18n as tool                                  # tools/i18n.py
    tool.cmd_compile()
    w = window
    try:
        i18n.apply_language(app, code)
        w._on_language_changed()
        w.load_sync(BUSY)
        _settle(app)
        assert w.side.width() <= w.side.parentWidget().width()
        assert w.side.minimumSizeHint().width() <= w.side.parentWidget().width()
    finally:
        i18n.apply_language(app, "en")
        w._on_language_changed()


def test_long_words_in_details_can_wrap(window, app):
    from PySide6.QtWidgets import QFormLayout, QLabel
    w = window
    w.load_sync(BUSY)
    _settle(app)
    f = w.details_form
    values = [f.itemAt(r, QFormLayout.ItemRole.FieldRole).widget() for r in range(f.rowCount())]
    created = next(v for v in values if isinstance(v, QLabel) and "BambuStudio" in v.text())
    assert "​" in created.text()                   # break chances in the long version name
    assert created.text().replace("​", "") == "BambuStudio-02.03.00.70"
    short = next(v for v in values if isinstance(v, QLabel) and v.text() == "PLA")
    assert "​" not in short.text()                 # short values stay as they are
    keys = [f.itemAt(r, QFormLayout.ItemRole.LabelRole).widget() for r in range(f.rowCount())]
    assert all(k.wordWrap() for k in keys)

"""Settings -> Viewer: the Build plate box in two columns (the plate on the left, the grid's numbers
and lines on the right), and one column when the window is too narrow for both."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_build_plate_box_has_two_columns(app, tmp_path):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(Settings(str(tmp_path / "settings.json")), page="viewer")
    dlg.resize(1100, 900)
    dlg.show()
    app.processEvents()
    try:
        def pos(w):
            return w.mapTo(dlg, w.rect().topLeft())
        left = [dlg.bed_cb, dlg.plate_axes_cb, dlg.plate_combo, dlg.plate_size_row]
        right = [dlg.grid_labels_cb, dlg.grid_step_combo, dlg.grid_minor_combo, dlg.grid_major_combo]
        for a, b in zip(left, right):                     # row by row, side by side
            assert abs(pos(a).y() + a.height() / 2 - pos(b).y() - b.height() / 2) <= 3
            assert pos(b).x() > pos(a).x() + a.width()
        tops = [pos(w).y() for w in left]
        assert tops == sorted(tops) and len(set(tops)) == 4
        # the right dropdowns are one column; Plate and the plate size are equally wide
        assert len({pos(c).x() for c in right[1:]}) == 1 and len({c.width() for c in right[1:]}) == 1
        assert dlg.plate_combo.width() == dlg.plate_size_row.width()
    finally:
        dlg.close()
        dlg.deleteLater()


def test_build_plate_columns_go_under_each_other_in_a_narrow_window(app, tmp_path):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(Settings(str(tmp_path / "settings.json")), page="viewer")
    dlg.show()
    try:
        for width, stacked in ((1100, False), (620, True), (1100, False)):
            dlg.resize(width, 800)
            for _ in range(4):
                app.processEvents()
            assert dlg.plate_columns.stacked is stacked, width
            y = lambda w: w.mapTo(dlg, w.rect().topLeft()).y()
            x = lambda w: w.mapTo(dlg, w.rect().topLeft()).x()
            if stacked:                                   # nothing cut off: one list, lined up
                assert y(dlg.grid_labels_cb) > y(dlg.plate_size_row)
                assert x(dlg.grid_minor_combo) == x(dlg.plate_combo)
            else:
                assert abs(y(dlg.grid_labels_cb) - y(dlg.bed_cb)) <= 3
    finally:
        dlg.close()
        dlg.deleteLater()

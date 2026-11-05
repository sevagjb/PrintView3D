"""Millimetre numbers along the plate's major grid lines (Settings -> Viewer, off by default)."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import DEFAULTS, Settings  # noqa: E402
from printview3d.ui import grid_labels as gl  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE = os.path.join(HERE, "data", "cube_binary.stl")        # 20 mm cube at 0..20


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


# ------------------------------------------------------------ the numbers
def test_major_step_follows_the_grid():
    assert gl.major_step(220, 220) == 50                   # a normal plate: every 50 mm
    assert gl.major_step(40, 40) == 25                     # a tiny one
    assert gl.major_step(800, 800) == 250                  # a huge one


@pytest.mark.parametrize("lo,hi,major,expected", [
    (0, 220, 50, [50, 100, 150, 200]),
    (0, 120, 50, [50, 100]),                               # a 120 mm plate: two numbers
    (-100, 100, 50, [-100, -50, 50, 100]),                 # zero is not written
    (0, 500, 50, [100, 200, 300, 400, 500]),               # a 500 mm plate: thinned to every 100 mm
    (0, 1000, 250, [250, 500, 750, 1000]),
    (10, 40, 25, [10, 15, 20, 25, 30, 35, 40]),            # too small for two 25 mm lines: every 5 mm
    (0, 60, 50, [25, 50]),                                 # a 60 mm area: half the major step
    (-20, 40, 50, [-20, -10, 10, 20, 30, 40]),                      # around a small model
])
def test_label_values(lo, hi, major, expected):
    assert gl.label_values(lo, hi, major) == expected


@pytest.mark.parametrize("size", [60, 120, 180, 220, 256, 300, 350, 500, 600, 1000])
def test_every_plate_gets_a_few_readable_numbers(size):
    major = gl.major_step(size, size)
    vals = gl.label_values(0, size, major)
    assert 2 <= len(vals) <= gl.MAX_LABELS


# ------------------------------------------------------------ the setting
def test_off_by_default_and_in_the_viewer_settings(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    assert DEFAULTS["show_grid_labels"] is False and not w.grid_labels.enabled
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    assert not dlg.grid_labels_cb.isChecked()
    # next to the "Show build plate grid" checkbox
    layout = dlg.bed_cb.parentWidget().layout()
    assert layout.indexOf(dlg.grid_labels_cb) == layout.indexOf(dlg.bed_cb) + 1
    dlg.grid_labels_cb.setChecked(True)
    dlg._save()
    assert w.settings.get("show_grid_labels") is True


def test_turning_it_on_shows_numbers_and_off_hides_them(window):
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)
    w.scene.set_view("iso", render=True)
    g = w.grid_labels
    g.set_enabled(False)
    assert g.items == [] and g.sprites.shown() == 0
    g.set_enabled(True)
    texts = [t for t, _ in g.items]
    assert texts and all(t.endswith(" mm") for t in texts) and g.sprites.shown() == len(texts)
    g.set_enabled(False)
    assert g.sprites.shown() == 0


def test_numbers_are_in_the_plate_colour_and_have_no_box(window):
    from printview3d.ui import theme
    from vtkmodules.util.numpy_support import vtk_to_numpy
    w = window
    w.load_sync(CUBE)
    g = w.grid_labels
    assert g._fg == gl._rgb(theme.colors()["plate_edge"])
    tex, width, height = g._picture("50 mm", 1.0)
    px = vtk_to_numpy(tex.GetInput().GetPointData().GetScalars()).reshape(height, width, 4)
    assert px[0, 0, 3] == 0 and height <= 18               # transparent corners: no box, and small


def test_numbers_sit_on_the_edges_nearest_the_camera(window):
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)
    g = w.grid_labels
    g.set_enabled(True)
    b = w.scene.bed_bounds
    n_x = len(gl.label_values(b[0], b[1], gl.major_step(b[1] - b[0], b[3] - b[2])))   # X numbers come first
    cx, cy = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2
    cam = w.plotter.renderer.GetActiveCamera()
    cam.SetPosition(cx + 80, cy - 200, b[4] + 150)          # in front, to the right
    g._layout()
    assert all(a[1] == b[2] for t, a in g.items[:n_x])      # X numbers along the front edge ...
    assert all(a[0] == b[1] for t, a in g.items[n_x:])      # ... Y numbers along the right edge
    cam.SetPosition(cx - 80, cy + 300, b[4] + 150)          # from behind, to the left
    g._layout()
    assert all(a[1] == b[3] for t, a in g.items[:n_x])      # the other edges now
    assert all(a[0] == b[0] for t, a in g.items[n_x:])


def test_hidden_from_under_the_plate_and_with_the_plate_hidden(window):
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)
    g = w.grid_labels
    g.set_enabled(True)
    cam = w.plotter.renderer.GetActiveCamera()
    z = w.scene.bed_bounds[4]
    cam.SetPosition(100, -200, z + 100)
    g._layout()
    assert g.items
    cam.SetPosition(100, -200, z - 100)                     # under the plate
    g._layout()
    assert g.items == [] and g.sprites.shown() == 0
    cam.SetPosition(100, -200, z + 100)
    w.act_bed.setChecked(False)                             # plate hidden: no numbers either
    g._layout()
    assert g.items == []


def test_infinite_grid_numbers_stay_near_the_model(window):
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)
    w.choose_plate_mode("infinite")
    g = w.grid_labels
    g.set_enabled(True)
    b = w.scene.bed_bounds                                  # the area the grid is drawn for, around the model
    assert b[1] - b[0] < 200
    assert g.items and all(abs(a[0]) < 200 and abs(a[1]) < 200 for t, a in g.items)


# ------------------------------------------------------------ a spacing of your own
def test_a_fixed_step_is_exactly_that_step():
    assert gl.label_values(0, 100, 50, step=10) == [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert gl.label_values(-20, 40, 50, step=20) == [-20, 20, 40]
    assert gl.label_values(0, 220, 50, step=0) == [50, 100, 150, 200]           # 0: automatic
    assert len(gl.label_values(0, 220, 50, step=5)) == 44                        # not thinned
    assert gl.label_values(0, 10000, 250, step=5) == []                          # absurdly many: none


def test_the_spacing_setting_changes_the_numbers(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)
    g = w.grid_labels
    g.set_enabled(True)
    auto = [t for t, _ in g.items]
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    assert dlg.grid_step_combo.currentData() == 0 and dlg.grid_step_combo.itemData(0) == 0
    assert [dlg.grid_step_combo.itemData(i) for i in range(dlg.grid_step_combo.count())] == [0, 5, 10, 20, 25, 50, 100]
    dlg.grid_labels_cb.setChecked(True)
    dlg.grid_step_combo.setCurrentIndex(dlg.grid_step_combo.findData(5))
    dlg._save()
    w._apply_grid_label_settings()                          # what open_settings does after OK
    assert w.settings.get("grid_labels_step") == 5 and g.step == 5
    five = [t for t, _ in g.items]
    assert "5 mm" in five and len(five) > len(auto)


def test_the_spacing_choice_is_greyed_out_while_the_numbers_are_off(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(window.settings, window, {}, page="viewer")
    assert not dlg.grid_step_row.isEnabled()
    dlg.grid_labels_cb.setChecked(True)
    assert dlg.grid_step_row.isEnabled()


def test_viewer_settings_line_up(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(window.settings, window, {}, page="viewer")
    dlg.resize(900, 800)
    dlg.show()
    for _ in range(4):
        app.processEvents()
    x = lambda wd: wd.mapTo(dlg, wd.rect().topLeft()).x()
    assert x(dlg.grid_step_combo) == x(dlg.plate_combo)                     # the two dropdowns
    sliders = (dlg.ghost_slider, dlg.plane_slider, dlg.line_slider)
    assert len({x(sl) for sl in sliders}) == 1                              # the sliders start ...
    assert len({x(sl) + sl.width() for sl in sliders}) == 1                 # ... and end together
    dlg.close()


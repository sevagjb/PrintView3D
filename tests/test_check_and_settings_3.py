"""Fixes from a bug review: the loose-parts count, pieces really inside another piece, the arrows
of the nozzle and loose-size fields, those fields in inches and other languages, an even grid
whatever the spacings, and 0 on the plate."""

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d import units  # noqa: E402
from printview3d.settings import Settings  # noqa: E402
from printview3d.ui import print_check as pc  # noqa: E402
from test_print_check import box  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CUBE = os.path.join(DATA, "cube_binary.stl")
INSIDE = os.path.join(DATA, "inside_view.3mf")


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


# ------------------------------------------------------------ the mesh check
def test_loose_count_is_the_loose_pieces():
    from printview3d.loaders import load_file
    hollow = load_file(INSIDE).parts[0]                   # two pieces: the part and its hollow
    r = pc.mesh_report(hollow.vertices, hollow.faces)
    assert r["pieces"] == 2 and r["loose_pieces"] == 0
    v1, f1 = box()
    v2, f2 = box(x0=50, dx=3, dy=3, dz=3)                 # a 3 mm crumb: loose
    v3, f3 = box(x0=80, dx=12, dy=12, dz=12)              # a 12 mm block: an object of its own
    r = pc.mesh_report(np.vstack([v1, v2, v3]), np.vstack([f1, f2 + 8, f3 + 16]))
    assert r["pieces"] == 3 and r["loose_pieces"] == 1 and r["loose"].sum() == 12


def test_the_count_shown_matches_the_coloured_parts(window):
    w = window
    w.load_sync(INSIDE)
    w.act_check.trigger()
    if w.check.mesh_busy:                                 # the mesh check runs in the background
        import time
        from PySide6.QtWidgets import QApplication
        end = time.time() + 20
        while w.check.mesh_busy and time.time() < end:
            QApplication.processEvents()
            time.sleep(0.02)
    assert w.check.counts()["loose"] == 0


def _tetra_and_crumb(flip_crumb: bool):
    """A 40 mm corner piece (a tetrahedron) and a 2 mm cube in its empty corner: in its box, but
    not in the piece."""
    tv = np.array([[0, 0, 0], [40, 0, 0], [0, 40, 0], [0, 0, 40]], float)
    tf = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    cv, cf = box(x0=30, y0=30, z0=30, dx=2, dy=2, dz=2)
    if flip_crumb:
        cf = cf[:, ::-1]
    return np.vstack([tv, cv]), np.vstack([tf, cf + 4])


def test_a_piece_in_the_box_but_outside_the_part_is_reported():
    v, f = _tetra_and_crumb(flip_crumb=True)
    r = pc.mesh_report(v, f)
    assert r["inside_out"] == 1 and r["flipped"][4:].all() and not r["flipped"][:4].any()
    assert r["loose_pieces"] == 1 and r["loose"][4:].all()
    v, f = _tetra_and_crumb(flip_crumb=False)
    r = pc.mesh_report(v, f)
    assert r["inside_out"] == 0 and r["loose_pieces"] == 1


def test_a_piece_really_inside_is_still_a_cavity():
    tv = np.array([[0, 0, 0], [40, 0, 0], [0, 40, 0], [0, 0, 40]], float)
    tf = np.array([[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]])
    cv, cf = box(x0=3, y0=3, z0=3, dx=2, dy=2, dz=2)      # near the corner: inside the tetrahedron
    r = pc.mesh_report(np.vstack([tv, cv]), np.vstack([tf, cf[:, ::-1] + 4]))
    assert r["inside_out"] == 0 and r["loose_pieces"] == 0 and not r["flipped"].any()


def test_inside_points():
    v, f = box()                                          # 0 .. 20 mm
    tris = v[f]
    pts = np.array([[10, 10, 10], [25, 10, 10], [1, 1, 1], [10, 10, -1], [19.9, 0.1, 10]])
    assert pc.inside(pts, tris).tolist() == [True, False, True, False, True]


# ------------------------------------------------------------ the nozzle and loose-size fields
def test_the_arrows_change_the_check_at_once(window, app):
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    w.check_nozzle.stepUp()
    app.processEvents()
    assert w.check.nozzle == pytest.approx(0.45) and w.settings.get("check_nozzle") == pytest.approx(0.45)
    w.check_loose.stepUp()
    app.processEvents()
    assert w.check.loose_max == pytest.approx(5.5) and w.settings.get("check_loose_max") == pytest.approx(5.5)
    assert not w.check_nozzle.keyboardTracking()          # typing counts on Enter, not per digit


def test_both_fields_follow_the_units_without_drifting(window, app):
    w = window
    w.settings.set("units", "in")
    units.set_unit("in")
    w._apply_units()
    assert w.check_loose.suffix().strip() == "in"
    assert w.check_nozzle.suffix().strip() == "mm"        # nozzles are sold in mm: stays mm
    assert w.check_loose.value() == pytest.approx(5.0 / 25.4, abs=0.01)
    w.settings.set("units", "mm")
    units.set_unit("mm")
    w._apply_units()
    assert w.check_nozzle.suffix().strip() == "mm"
    # there and back again: still exactly 0.4 and 5 mm, nothing rounded through inches
    assert w.check.nozzle == pytest.approx(0.4) and w.check_nozzle.mm() == pytest.approx(0.4)
    assert w.check.loose_max == pytest.approx(5.0) and w.check_loose.mm() == pytest.approx(5.0)


def test_the_unit_name_follows_the_language(window, monkeypatch):
    from printview3d.ui import length_spin
    w = window
    monkeypatch.setattr(length_spin, "tr", lambda s: "MM" if s == "mm" else s)
    w.retranslate_ui()
    assert w.check_nozzle.suffix() == " MM" and w.check_loose.suffix() == " MM"


# ------------------------------------------------------------ the grid
def test_main_lines_always_fall_on_fine_lines():
    from printview3d.ui.scene import Scene, is_multiple
    assert Scene.even_spacing(20, 50, True, False) == (20, 100)       # fine 20, main automatic
    assert Scene.even_spacing(10, 25, False, True) == (5, 25)         # main 25, fine automatic
    assert Scene.even_spacing(10, 50, True, True) == (10, 50)         # already even: kept
    assert Scene.even_spacing(20, 25, True, True) == (20, 100)        # both chosen (by hand): fine wins
    for minor in (1, 2, 5, 10, 20, 50):
        for major in (10, 20, 25, 50, 100, 200, 250):
            for chosen in ((True, True), (True, False), (False, True)):
                m, big = Scene.even_spacing(minor, major, *chosen)
                assert is_multiple(big, m), (minor, major, chosen)


def test_an_uneven_choice_draws_an_even_grid(window):
    from vtkmodules.util.numpy_support import vtk_to_numpy
    w = window
    w.settings.set("grid_minor", 20)
    w.settings.set("grid_major", 0)
    w._settings_applied()
    w.load_sync(CUBE)
    sc = w.scene
    xs = set()
    for name in ("bed_minor", "bed_major"):
        a = sc.p.actors.get(name)
        if a is not None:
            pts = vtk_to_numpy(a.GetMapper().GetInput().GetPoints().GetData())
            xs |= set(np.round(pts[:, 0] - sc.bed_bounds[0], 3).tolist())
    gaps = np.diff(sorted(xs))
    assert len(gaps) and np.allclose(gaps, gaps[0])               # every line the same distance apart


def test_settings_offers_only_main_spacings_on_fine_lines(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(window.settings, window, {}, page="viewer")
    major = dlg.grid_major_combo
    major.setCurrentIndex(major.findData(50.0))
    dlg.grid_minor_combo.setCurrentIndex(dlg.grid_minor_combo.findData(20.0))
    enabled = {major.itemData(i) for i in range(1, major.count()) if major.model().item(i).isEnabled()}
    assert enabled == {20.0, 100.0, 200.0}
    assert major.currentIndex() == 0                              # 50 no longer fits: Automatic
    dlg.grid_minor_combo.setCurrentIndex(0)                        # automatic fine lines: all allowed
    assert all(major.model().item(i).isEnabled() for i in range(major.count()))
    dlg.close()


def test_zero_is_written_once_at_the_plate_corner(window):
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)
    g = w.grid_labels
    g.set_enabled(True)
    w.scene.draw_bed((-100.0, 100.0, -80.0, 120.0), 0.0)
    cam = w.plotter.renderer.GetActiveCamera()
    cam.SetPosition(-300, -300, 200)                              # looking from the front-left
    zeros = [a for t, a, _c in g.wanted() if t == "0 mm"]
    assert zeros == [(-100.0, -80.0, 0.0)]                         # once, at the corner
    cam.SetPosition(300, -300, 200)                               # from the front-right: two edges
    zeros = sorted(a for t, a, _c in g.wanted() if t == "0 mm")
    assert zeros == [(-100.0, -80.0, 0.0), (100.0, -80.0, 0.0)]

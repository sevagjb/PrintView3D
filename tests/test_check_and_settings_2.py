"""Sliver triangles, hollow parts and loose parts in the mesh check; the grid seen from below; the
line where the cutting planes meet; Settings layout; shortcuts; the side panel at its narrowest;
Open file or ZIP; the X/Y/Z arrows on the plate; positive grid numbers only."""

import os
import shutil
import zipfile

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402
from printview3d.ui import print_check as pc  # noqa: E402
from test_print_check import box  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CUBE = os.path.join(DATA, "cube_binary.stl")
INSIDE = os.path.join(DATA, "inside_view.3mf")
# A real file full of zero-area triangles. Not part of the repository: its test runs where it is.
ADAPTOR = os.path.join(DATA, "adaptorvacuum.3mf")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _make(app, tmp_path, **settings):
    from printview3d.ui import main_window as mw
    s = Settings(str(tmp_path / "settings.json"))
    for k, v in settings.items():
        s.set(k, v)
    w = mw.MainWindow(s)
    w.resize(1280, 800)
    w.show()
    return w


@pytest.fixture
def window(app, tmp_path):
    from PySide6.QtCore import QEvent
    w = _make(app, tmp_path)
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


# ------------------------------------------------------------ the mesh check
def test_sliver_triangles_are_not_problems():
    v, f = box()
    v = np.vstack([v, [[10, 0, 0]]])                      # a point on the front-bottom edge
    sliver = np.array([[0, 1, 8]])                        # three corners on one line: no area
    r = pc.mesh_report(v, np.vstack([f, sliver]))
    assert r["slivers"] == 1
    assert len(r["nonmanifold"]) == 0 and not r["flipped"].any()


def test_a_hollow_part_is_not_inside_out_nor_loose():
    outer_v, outer_f = box()
    inner_v, inner_f = box(x0=5, y0=5, z0=5, dx=10, dy=10, dz=10)
    v = np.vstack([outer_v, inner_v])
    f = np.vstack([outer_f, inner_f[:, ::-1] + 8])        # the cavity: normals pointing into it
    r = pc.mesh_report(v, f)
    assert r["pieces"] == 2 and r["inside_out"] == 0
    assert not r["flipped"].any() and not r["loose"].any()


def test_loose_parts_have_a_size_limit():
    v1, f1 = box()
    v2, f2 = box(x0=50, dx=3, dy=3, dz=3)                 # a 3 mm crumb next to the model
    v3, f3 = box(x0=80, dx=12, dy=12, dz=12)              # a 12 mm block: an object of its own
    v = np.vstack([v1, v2, v3])
    f = np.vstack([f1, f2 + 8, f3 + 16])
    r = pc.mesh_report(v, f, loose_max=5)
    assert r["loose"][12:24].all() and not r["loose"][24:].any() and not r["loose"][:12].any()
    r = pc.mesh_report(v, f, loose_max=20)
    assert r["loose"][12:].all()


@pytest.mark.skipif(not os.path.exists(ADAPTOR), reason="adaptorvacuum.3mf is not in the repository")
def test_a_real_file_full_of_slivers():
    from printview3d.loaders import load_file
    p = load_file(ADAPTOR).parts[0]
    r = pc.mesh_report(p.vertices, p.faces)
    assert r["slivers"] > 100                             # the file is full of them ...
    assert len(r["open"]) == 0 and len(r["nonmanifold"]) == 0 and not r["flipped"].any()   # ... and is fine


def test_a_real_hollow_file():
    from printview3d.loaders import load_file
    hollow = load_file(INSIDE).parts[0]
    r = pc.mesh_report(hollow.vertices, hollow.faces)
    assert r["pieces"] == 2 and not r["flipped"].any() and not r["loose"].any()


def test_check_section_names_size_limit_and_place(window):
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    assert w.check_box.title() == "Check model" and w.act_check.text() == "Check (C)"
    names = {k: r[0].text() for k, r in w.check_rows.items()}
    assert names["open"] == "Holes" and names["nonmanifold"] == "Tangled edges"
    assert names["flipped"] == "Inside-out faces"
    tip = w.check_rows["nonmanifold"][0].toolTip()
    assert tip.startswith("<p><b>Non-manifold edges</b>")       # the technical term first, in bold
    assert "Technical term" not in tip
    assert w.check_rows["flipped"][0].toolTip().startswith("<p>")                # rich text: wraps
    nl = w.check_nozzle.parentWidget().layout()                 # "0.40 mm nozzle"
    assert nl.indexOf(w.check_nozzle) < nl.indexOf(w.check_nozzle_label)
    w.check_loose.set_mm(12)
    w._check_loose_changed()
    assert w.settings.get("check_loose_max") == 12 and w.check.loose_max == 12
    lay = w.side_layout
    order = [lay.itemAt(i).widget() for i in range(lay.count())]
    assert order.index(w.measure_box) < order.index(w.check_box) < order.index(w.details_box)


def test_check_colours_kept_when_asked(app, tmp_path, monkeypatch):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QColorDialog
    w = _make(app, tmp_path, check_keep_colors=True)
    try:
        w.load_sync(CUBE)
        w.act_check.trigger()
        monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *a, **k: QColor("#123456")))
        w.check_rows["thin"][2].click()
        assert w.settings.get("check_colors") == {"thin": "#123456"}
    finally:
        w.close()
    w2 = _make(app, tmp_path)
    try:
        assert w2.check.colors["thin"] == "#123456" and w2.check_rows["thin"][2].color == "#123456"
    finally:
        w2.close()


def test_tooltips_come_sooner(app):
    from PySide6.QtWidgets import QStyle
    from printview3d.ui import theme
    theme.apply_theme(app, "dark")
    assert app.style().styleHint(QStyle.SH_ToolTip_WakeUpDelay) == theme.TOOLTIP_DELAY_MS < 700


# ------------------------------------------------------------ 3D view
def test_grid_lines_stay_behind_the_model_from_below(window):
    from printview3d.ui.scene import BELOW_LIFT
    w = window
    w.load_sync(CUBE)
    cam = w.plotter.renderer.GetActiveCamera()
    cam.SetPosition(10, -60, -80)                         # under the plate
    w.scene._update_plate_side()
    major = w.scene.p.actors["bed_major"]
    assert major.GetPosition()[2] == pytest.approx(BELOW_LIFT) and BELOW_LIFT > 0.02
    cam.SetPosition(10, -60, 80)
    w.scene._update_plate_side()
    assert major.GetPosition()[2] == 0


def test_the_planes_line_stays_inside_the_flat_plane(window):
    w = window
    w.load_sync(INSIDE)
    b = w.scene.focus_bounds
    w.act_clip.trigger()
    w.act_clip_face.trigger()
    w.settings.set("cut_planes_whole", True)
    w._apply_grid_label_settings()
    pts = np.asarray(w.scene._cut_line[0].points)
    pad = max(2.0, 0.04 * max(b[1] - b[0], b[3] - b[2], b[5] - b[4]))
    assert all(b[0] - pad - 1e-6 <= x <= b[1] + pad + 1e-6 and b[2] - pad - 1e-6 <= y <= b[3] + pad + 1e-6
               for x, y, _z in pts)


# ------------------------------------------------------------ Settings
def test_settings_layout(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(window.settings, window, {}, page="viewer")
    dlg.show()
    for _ in range(4):
        app.processEvents()
    lay = dlg.travel_cb.parentWidget().layout()
    assert lay.indexOf(dlg.cube_cb) == lay.indexOf(dlg.travel_cb) + 1          # right after travel moves
    # Under the planes option: dragging the cuts, then the Check colours.
    assert lay.indexOf(dlg.clip_handles_cb) == lay.indexOf(dlg.cut_planes_cb) + 1
    assert lay.indexOf(dlg.check_colors_cb) == lay.indexOf(dlg.clip_handles_cb) + 1
    # The window is as tall as the tallest page of settings needs, up to 90 % of the screen: those
    # pages have no scroll bar. The long list of keys doesn't make it taller: it scrolls.
    limit = int(dlg.screen().availableGeometry().height() * 0.9)
    for i in range(dlg.pages.count()):
        dlg.pages.setCurrentIndex(i)
        app.processEvents()
        bar = dlg.pages.widget(i).verticalScrollBar().maximum()
        if dlg._page_keys[i] == "keys":
            assert bar > 0                                # longer than the window: it scrolls
            continue
        if dlg._page_keys[i] == "about":
            continue
        if dlg.height() < limit - 1:
            assert bar == 0, dlg._page_keys[i]
    assert dlg._page_keys[dlg.pages.count() - 1] == "about"
    # the Viewer page's dropdowns line up: all as wide as the widest
    widths = {c.width() for c in (dlg.grid_step_combo, dlg.grid_minor_combo, dlg.grid_major_combo, dlg.plate_combo)}
    assert len(widths) == 1
    plate_lay = dlg.bed_cb.parentWidget().layout()                 # the Build plate box
    assert plate_lay.indexOf(dlg.plate_axes_cb) == plate_lay.indexOf(dlg.bed_cb) + 1
    assert dlg.plate_axes_cb.text().startswith("Also show")    # in addition to the corner marker
    dlg.close()


def test_settings_opens_on_the_last_page(window, app):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(window.settings, window, {})
    dlg.show_page("files")
    dlg.close()
    assert window.settings.get("settings_page") == "files"
    dlg = SettingsDialog(window.settings, window, {})
    assert dlg._page_keys[dlg.nav.currentRow()] == "files"
    dlg.close()
    dlg = SettingsDialog(window.settings, window, {}, page="about")      # asked for: that one
    assert dlg._page_keys[dlg.nav.currentRow()] == "about"
    dlg.close()


# ------------------------------------------------------------ shortcuts
def test_every_section_button_has_a_key(window):
    w = window
    keys = {w.act_bed: "P", w.act_check: "C", w.act_view: "V", w.act_measure: "M",
            w.measure_actions["distance"]: "D", w.measure_actions["angle"]: "A", w.measure_actions["circle"]: "O"}
    for act, key in keys.items():
        assert act.shortcut().toString() == key and act in w.actions()
        assert f"({key})" in act.text() and f"({key})" not in act.toolTip()   # on the button, not the tooltip
    for act in (w.act_bed, w.act_check, w.act_view, w.act_measure):
        assert act.text().endswith(")")                   # "Measure (M)" on the toolbar
    # the side panel's buttons too: "Wireframe (W)", "Distance (D)", "Reset view (R)"
    assert w.act_wireframe.text().endswith("(W)") and w.measure_actions["distance"].text().endswith("(D)")
    assert w.view_reset_btn.text().endswith("(R)")
    # Fit has its own key again: F
    assert w.act_fit.text() == "Fit (F)" and "(F)" not in w.act_fit.toolTip()
    from printview3d.ui import keys as k
    listed = set(k.DEFAULT.values())
    assert all(key in listed for key in ("P", "C", "V", "D", "A", "O", "F", "T", "S"))


def test_r_fits_g_code_too(window):
    w = window
    w.load_sync(os.path.join(DATA, "cylinder.gcode"))
    assert w.act_reset_view.isEnabled()
    calls = []
    w.set_view = lambda v, animate=False: calls.append(v)
    w.act_reset_view.trigger()
    assert calls == [None]


def test_the_measure_keys_pick_the_kind(window):
    w = window
    w.load_sync(CUBE)
    w.measure_actions["angle"].trigger()                  # A
    assert w.measure.active and w.measure.mode == "angle"


# ------------------------------------------------------------ the side panel at its narrowest
def test_nothing_is_cut_off_at_the_narrowest(window, app):
    w = window
    w.load_sync(INSIDE)
    for a in (w.act_check, w.act_view, w.act_measure):
        a.setChecked(True)
    i = w.splitter.indexOf(w.side_scroll)
    total = sum(w.splitter.sizes())
    w.splitter.setSizes([total - 10, 10] if i == 1 else [10, total - 10])
    for _ in range(6):
        app.processEvents()
    room = w.side_scroll.viewport().width()
    assert w.side.width() <= room                         # the panel's content fits its view
    for box in (w.check_box, w.measure_box, w.view_box, w.objects_box):
        right = box.mapTo(w.side, box.rect().topRight()).x()
        assert right <= room, box.title()


# ------------------------------------------------------------ menu
def test_open_file_or_zip_and_folders_without_archives(window, tmp_path):
    w = window
    assert w.act_open.text() == "Open file or ZIP…" and w.act_open.toolTip().startswith("Open file or ZIP…")
    assert not hasattr(w, "act_open_archive")
    menu = w.main_menu.actions()
    assert menu.index(w.act_open_folder) == menu.index(w.act_open) + 1
    d = tmp_path / "f"
    d.mkdir()
    shutil.copy(CUBE, d / "a.stl")
    with zipfile.ZipFile(d / "b.zip", "w") as z:
        z.write(CUBE, "x.stl")
    assert [os.path.basename(f) for f in w.folder_files(str(d))] == ["a.stl"]


# ------------------------------------------------------------ the grid and the plate
def test_highlights_leave_the_grid_where_it_is(window):
    """The Check highlights are drawn just in front of the model; nothing else may move. VTK's
    offset mode is shared by every mapper and pulled the plate's lines 4 depth units forward,
    through the model when zoomed out."""
    from vtkmodules.vtkCommonCore import reference
    from vtkmodules.vtkRenderingCore import vtkMapper
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    part = w.check.parts[0]
    w.check._add_faces("check_overhang_0", part, np.ones(len(part.faces), bool), "#ff0000")
    assert "check_overhang_0" in w.check._actors
    f, u = reference(1.0), reference(1.0)
    vtkMapper.GetResolveCoincidentTopologyLineOffsetParameters(f, u)
    assert (float(f), float(u)) == (0.0, 0.0)
    vtkMapper.GetResolveCoincidentTopologyPolygonOffsetParameters(f, u)
    assert (float(f), float(u)) == (0.0, 0.0)


def test_highlights_do_not_show_through_the_model(window):
    """A highlight's pull towards the camera is constant: no slope part, which grows without limit
    on faces seen edge-on and showed hidden overhangs (under fingers, lips) through the model."""
    from vtkmodules.vtkCommonCore import reference
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    part = w.check.parts[0]
    w.check._add_faces("check_overhang_0", part, np.ones(len(part.faces), bool), "#ff0000")
    f, u = reference(1.0), reference(1.0)
    w.check._actors["check_overhang_0"].GetMapper().GetRelativeCoincidentTopologyPolygonOffsetParameters(f, u)
    assert float(f) == 0.0 and float(u) < 0.0


def test_grid_numbers_count_from_the_plate_corner(window):
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)
    g = w.grid_labels
    g.set_enabled(True)
    w.scene.draw_bed((-100.0, 100.0, -80.0, 120.0), 0.0)     # a plate around the origin
    assert w.scene.grid_origin == (-100.0, -80.0)            # 0 is its front-left corner
    items = g.wanted()
    assert items and all(not t.startswith("-") for t, _a, _c in items)
    xs = {round(a[0], 6): t for t, a, _c in items if a[1] in (-80.0, 120.0)}
    assert xs[-50.0] == "50 mm" and xs[0.0] == "100 mm"       # counted from the corner
    # the grid lines start at the corner too: the numbers sit on major lines
    from vtkmodules.util.numpy_support import vtk_to_numpy
    pts = vtk_to_numpy(w.scene.p.actors["bed_major"].GetMapper().GetInput().GetPoints().GetData())
    assert -50.0 in set(np.round(pts[:, 0], 6))


def test_infinite_grid_counts_from_the_model(window):
    w = window
    w.load_sync(CUBE)
    w.choose_plate_mode("infinite")
    b = w.scene.focus_bounds
    assert w.scene.grid_origin == pytest.approx((b[0], b[2]))
    g = w.grid_labels
    g.set_enabled(True)
    w.plotter.ren_win.SetSize(800, 600)
    items = g.wanted()
    assert items and all(not t.startswith("-") for t, _a, _c in items)


def test_angle_and_nozzle_fields_line_up(window):
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    w.side.adjustSize()
    a = w.check_angle.mapTo(w.side, w.check_angle.rect().topLeft()).x()
    n = w.check_nozzle.mapTo(w.side, w.check_nozzle.rect().topLeft()).x()
    assert a == n and w.check_angle.width() == w.check_nozzle.width()


def test_xyz_arrows_on_the_plate(window):
    w = window
    w.load_sync(CUBE)                                 # 0 .. 20 mm
    assert not [n for n in w.scene.p.actors if n.startswith("plate_axis")]     # off by default
    w.settings.set("show_plate_axes", True)
    w._settings_applied()
    names = [n for n in w.scene.p.actors if n.startswith("plate_axis")]
    assert len(names) == 6                            # three arrows, three letters
    b = w.scene.focus_bounds
    (ox, oy, _z), length = w.scene.plate_axes_frame()
    assert length <= 0.5 * (b[1] - b[0])              # small: well under the model's size
    # beside the back-right corner, just outside the model; it stays there as the view turns
    assert b[1] < ox < b[1] + 5 and b[3] < oy < b[3] + 5
    cam = w.plotter.renderer.GetActiveCamera()
    for pos in ((-100, -100, 80), (200, 200, 80), (-100, 200, 80)):
        cam.SetPosition(*pos)
        w.plotter.render()
        assert w.scene.p.actors["plate_axis_X"].GetPosition() == pytest.approx((ox, oy, _z))
    w.act_bed.setChecked(False)                       # on the plate: hidden with it
    assert not w.scene.p.actors["plate_axis_X"].GetVisibility()
    w.act_bed.setChecked(True)
    assert not w.scene.p.actors["plate_axis_Z"].GetUseBounds()     # Fit sees the model only
    w.settings.set("show_plate_axes", False)
    w._settings_applied()
    assert not [n for n in w.scene.p.actors if n.startswith("plate_axis")]

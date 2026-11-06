"""Sliver triangles, hollow parts and loose parts in the mesh check; the grid seen from below; the
line where the cutting planes meet; Settings layout; shortcuts; the side panel at its narrowest;
Open archive."""

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


def test_the_real_files():
    from printview3d.loaders import load_file
    p = load_file(ADAPTOR).parts[0]
    r = pc.mesh_report(p.vertices, p.faces)
    assert r["slivers"] > 100                             # the file is full of them ...
    assert len(r["open"]) == 0 and len(r["nonmanifold"]) == 0 and not r["flipped"].any()   # ... and is fine
    hollow = load_file(INSIDE).parts[0]
    r = pc.mesh_report(hollow.vertices, hollow.faces)
    assert r["pieces"] == 2 and not r["flipped"].any() and not r["loose"].any()


def test_check_section_names_size_limit_and_place(window):
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    assert w.check_box.title() == "Check model" and w.act_check.text() == "Check (K)"
    names = {k: r[0].text() for k, r in w.check_rows.items()}
    assert names["open"] == "Holes" and names["nonmanifold"] == "Tangled edges"
    assert names["flipped"] == "Inside-out faces"
    assert "non-manifold edges" in w.check_rows["nonmanifold"][0].toolTip()     # the technical term
    assert w.check_rows["flipped"][0].toolTip().startswith("<p>")                # rich text: wraps
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
    w.load_sync(ADAPTOR)
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
    assert lay.indexOf(dlg.check_colors_cb) == lay.indexOf(dlg.cut_planes_cb) + 1
    # The window is as tall as the tallest page needs, up to 90 % of the screen: every page that
    # fits in that has no scroll bar (only About's long list of keys may scroll on a small screen).
    limit = int(dlg.screen().availableGeometry().height() * 0.9)
    for i in range(dlg.pages.count()):
        dlg.pages.setCurrentIndex(i)
        app.processEvents()
        bar = dlg.pages.widget(i).verticalScrollBar().maximum()
        if dlg._page_keys[i] == "about" and dlg.height() >= limit - 1:
            continue
        assert bar == 0, dlg._page_keys[i]
    assert dlg._page_keys[dlg.pages.count() - 1] == "about"
    dlg.close()


# ------------------------------------------------------------ shortcuts
def test_every_section_button_has_a_key(window):
    w = window
    keys = {w.act_bed: "P", w.act_check: "K", w.act_view: "I", w.act_measure: "M",
            w.measure_actions["distance"]: "D", w.measure_actions["angle"]: "A", w.measure_actions["circle"]: "O"}
    for act, key in keys.items():
        assert act.shortcut().toString() == key and act in w.actions()
        assert f"({key})" in act.toolTip()
    for act in (w.act_bed, w.act_check, w.act_view, w.act_measure, w.act_fit):
        assert act.text().endswith(")")                   # "Measure (M)" on the toolbar
    from printview3d.ui.settings_dialog import shortcut_rows
    listed = [k for row, _ in shortcut_rows() for k in row]
    assert all(k in listed for k in ("P", "K", "I", "D", "A", "O"))


def test_the_measure_keys_pick_the_kind(window):
    w = window
    w.load_sync(CUBE)
    w.measure_actions["angle"].trigger()                  # A
    assert w.measure.active and w.measure.mode == "angle"


# ------------------------------------------------------------ the side panel at its narrowest
def test_nothing_is_cut_off_at_the_narrowest(window, app):
    w = window
    w.load_sync(ADAPTOR)
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
def test_open_archive_and_folders_without_archives(window, tmp_path):
    w = window
    assert w.act_open_archive in w.main_menu.actions()
    menu = w.main_menu.actions()
    assert menu.index(w.act_open_archive) == menu.index(w.act_open_folder) + 1
    d = tmp_path / "f"
    d.mkdir()
    shutil.copy(CUBE, d / "a.stl")
    with zipfile.ZipFile(d / "b.zip", "w") as z:
        z.write(CUBE, "x.stl")
    assert [os.path.basename(f) for f in w.folder_files(str(d))] == ["a.stl"]

"""Inches, grid spacing, the cut-planes option, the preview link, the Check section and the folder
browser."""

import os
import shutil

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d import units  # noqa: E402
from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CUBE = os.path.join(DATA, "cube_binary.stl")          # 20 mm cube, 0..20
TWO_PARTS = os.path.join(DATA, "two_parts.3mf")
INSIDE = os.path.join(DATA, "inside_view.3mf")
GCODE = os.path.join(DATA, "cylinder.gcode")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def back_to_mm():
    yield
    units.set_unit("mm")                                  # every test starts and ends in millimetres


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


@pytest.fixture
def inch_window(app, tmp_path):
    from PySide6.QtCore import QEvent
    w = _make(app, tmp_path, units="in")
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


# ------------------------------------------------------------ units
def test_unit_conversions():
    units.set_unit("mm")
    assert units.length(12.5) == "12.50 mm" and units.number(20, 1) == "20.0"
    units.set_unit("in")
    assert units.imperial() and units.name() == "in"
    assert units.length(25.4) == "1.000 in" and units.number(50.8, 1) == "2.000"
    assert units.from_display(2) == pytest.approx(50.8) and units.to_display(127) == pytest.approx(5)
    assert units.short(0.5) == "0.5" and units.short(2.0) == "2" and units.short(0.125) == "0.125"
    assert "in³" in units.volume(25.4 ** 3)
    units.set_unit("cm")                                   # nonsense: millimetres
    assert units.current() == "mm"


def test_sizes_in_inches(inch_window):
    w = inch_window
    w.load_sync(CUBE)
    assert "0.787 × 0.787 × 0.787 in" in w.details_body.findChildren(type(w.kind_label))[1].text() or any(
        "0.787 × 0.787 × 0.787 in" in l.text() for l in w.details_body.findChildren(type(w.kind_label)))
    vol = [l.text() for l in w.details_body.findChildren(type(w.kind_label)) if "in³" in l.text()]
    assert vol and vol[0].startswith("0.49")              # 8 cm³ = 0.488 in³
    w.load_sync(TWO_PARTS)
    sizes = [l.text() for l in w.objects_box.findChildren(type(w.kind_label)) if l.objectName() == "objectSize"]
    assert sizes and all(t.endswith(" in") for t in sizes)


def test_clip_and_measure_in_inches(inch_window):
    w = inch_window
    w.load_sync(CUBE)
    w.act_clip.trigger()
    assert w.clip_info.text() == "Height 0.394 of 0.787 in"           # 10 of 20 mm
    from printview3d.ui import measure as ms
    s = ms.shape_of("distance", [(0, 0, 0), (25.4, 0, 0)], deltas=True)
    assert s.label[1].startswith("1.000 in\n") and "ΔX +1.000" in s.label[1]
    c = ms.shape_of("circle", [(25.4, 0, 0), (0, 25.4, 0), (-25.4, 0, 0)])
    assert c.label[1] == "Ø 2.000 in  ·  R 1.000 in"


def test_grid_in_inches(inch_window):
    w = inch_window
    w.load_sync(CUBE)
    minor, major = w.scene.grid_spacing(220)
    assert (minor, major) == pytest.approx((6.35, 25.4))              # 1/4 in and 1 in
    from printview3d.ui import grid_labels as gl
    assert gl.text_for(50.8) == "2 in" and gl.text_for(12.7) == "0.5 in"


def test_switching_units_in_settings_converts_the_fields(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    dlg = SettingsDialog(w.settings, w, {}, page="language")
    assert dlg.units_combo.currentData() == "mm"
    dlg.plate_w_spin.set_mm(254)
    dlg.units_combo.setCurrentIndex(dlg.units_combo.findData("in"))
    assert dlg.plate_w_spin.suffix().strip() == "in" and dlg.plate_w_spin.value() == pytest.approx(10)
    assert [dlg.grid_minor_combo.itemData(i) for i in range(dlg.grid_minor_combo.count())][1:] == [0.1, 0.125, 0.25, 0.5, 1]
    dlg.grid_minor_combo.setCurrentIndex(dlg.grid_minor_combo.findData(0.5))
    dlg._save()
    w._apply_grid_label_settings()
    assert w.settings.get("units") == "in" and units.imperial()
    assert w.settings.get("plate_size")[0] == pytest.approx(254)      # stored in mm
    assert w.settings.get("grid_minor_in") == 0.5 and w.settings.get("grid_minor") == 0
    assert w.scene.grid_minor == pytest.approx(12.7)


# ------------------------------------------------------------ grid spacing
def _lines(w, name):
    a = w.scene.p.actors.get(name)
    return 0 if a is None else a.GetMapper().GetInput().GetNumberOfCells()


def _expected(lo, hi, minor, major):
    """(minor, major) line counts along one axis, as the grid draws them."""
    import math
    def pos(step):
        return [i * step for i in range(math.ceil(lo / step - 1e-9), math.floor(hi / step + 1e-9) + 1)]
    majors = pos(major)
    minors = [m for m in pos(minor) if all(abs(m - M) > 1e-6 for M in majors)]
    return len(minors), len(majors)


def test_grid_spacing_from_settings(app, tmp_path):
    w = _make(app, tmp_path, plate_mode="custom", plate_size=[200, 100])
    try:
        w.load_sync(CUBE)
        b = w.scene.bed_bounds
        for minor, major in ((10, 50), (5, 20), (2, 25)):
            if (minor, major) != (10, 50):
                w.settings.set("grid_minor", minor)
                w.settings.set("grid_major", major)
                w._apply_grid_label_settings()
            assert w.scene.grid_spacing(200) == (minor, major)
            ex, ey = _expected(b[0], b[1], minor, major), _expected(b[2], b[3], minor, major)
            assert _lines(w, "bed_minor") == ex[0] + ey[0] and _lines(w, "bed_major") == ex[1] + ey[1]
    finally:
        w.close()


# ------------------------------------------------------------ the two cutting planes
def test_cutting_planes_cut_each_other_unless_told_not_to(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.act_clip_face.trigger()
    sheets = w.scene._sheets
    assert all(a.GetMapper().GetNumberOfClippingPlanes() == 1 for _q, acts in sheets.values() for a in acts)
    w.settings.set("cut_planes_whole", True)
    w._apply_grid_label_settings()
    assert all(a.GetMapper().GetNumberOfClippingPlanes() == 0 for _q, acts in sheets.values() for a in acts)
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    assert dlg.cut_planes_cb.isChecked()


# ------------------------------------------------------------ the preview link
def test_preview_link_sits_beside_type_and_size(window, app):
    w = window
    w.load_sync(os.path.join(DATA, "busy_project.3mf"))                # has a preview picture
    for _ in range(4):
        app.processEvents()
    if not w.thumb_toggle.isVisible():
        pytest.skip("this file has no preview picture")
    k, t = w.kind_label, w.thumb_toggle
    assert k.mapTo(w.side, k.rect().topLeft()).y() == t.mapTo(w.side, t.rect().topLeft()).y()      # one line
    assert t.mapTo(w.side, t.rect().topLeft()).x() > k.mapTo(w.side, k.rect().topRight()).x()
    assert w.thumb_label.mapTo(w.side, w.thumb_label.rect().topLeft()).y() > k.mapTo(w.side, k.rect().bottomLeft()).y()


# ------------------------------------------------------------ the Check section
def test_check_button_sits_between_plate_and_view(window):
    w = window
    tb = w.view_btn.parentWidget()
    order = [o for o in (tb.widgetForAction(a) for a in tb.actions()) if o is not None]
    assert order.index(w.plate_btn) < order.index(w.check_btn) < order.index(w.view_btn)
    assert not w.act_check.icon().isNull() and w.act_check.text() == "Check (K)"


def test_check_section_counts_and_highlights(window):
    w = window
    w.load_sync(CUBE)
    assert w.check_box.isHidden() and not w.check.active
    w.act_check.trigger()
    assert w.check_box.isVisible() and w.check.active
    texts = {k: r[1].text() for k, r in w.check_rows.items()}
    assert texts["overhang"] == "none" and texts["open"] == "none" and texts["loose"] == "none"
    w.check_angle.setValue(10)
    assert w.settings.get("check_angle") == 10
    w.act_check.trigger()
    assert w.check_box.isHidden() and not w.check.active and not w.check._actors


def test_check_finds_an_open_mesh_and_shows_it(window, tmp_path):
    from printview3d.loaders.mesh import MeshPart, ModelData
    from test_print_check import box
    w = window
    w.load_sync(CUBE)
    v, f = box()
    w._show_model(ModelData([MeshPart("open", v, f[1:])]))            # a box with one triangle missing
    w.model = ModelData([MeshPart("open", v, f[1:])])
    w.act_check.trigger()
    assert w.check.counts()["open"] == 3
    assert w.check_rows["open"][1].text() == "3 edges"
    assert "check_open_0" in w.check._actors
    w.check_rows["open"][0].setChecked(False)                        # untick: the highlight goes
    assert "check_open_0" not in w.check._actors and w.settings.get("check_show")["open"] is False


def test_thin_walls_on_demand(window):
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    assert w.check.thin is None and not w.check_rows["thin"][0].isChecked()   # off by default: it takes time
    w.check.wait_for_thin()
    assert w.check.counts()["thin"] == 0
    w.check_nozzle.set_mm(0.6)
    w._check_nozzle_changed()
    assert w.settings.get("check_nozzle") == pytest.approx(0.6) and w.check.thin is None


def test_check_colours_last_until_the_program_closes(app, tmp_path, monkeypatch):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QColorDialog
    from printview3d.ui.print_check import DEFAULT_COLORS
    w = _make(app, tmp_path)
    try:
        w.load_sync(CUBE)
        w.act_check.trigger()
        monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *a, **k: QColor("#123456")))
        w.check_rows["overhang"][2].click()
        assert w.check.colors["overhang"] == "#123456" and w.check_rows["overhang"][2].color == "#123456"
        assert not w.settings.get("check_colors")                          # not saved (the default)
    finally:
        w.close()
    w2 = _make(app, tmp_path)                                              # the next start: the defaults
    try:
        assert w2.check.colors["overhang"] == DEFAULT_COLORS["overhang"]
        assert w2.check_rows["overhang"][2].color == DEFAULT_COLORS["overhang"]
    finally:
        w2.close()


def test_mesh_rows_explain_themselves_on_hover(window):
    w = window
    for kind in ("open", "nonmanifold", "flipped", "loose"):
        cb, count_lbl, _box = w.check_rows[kind]
        assert len(cb.toolTip()) > 30 and count_lbl.toolTip() == cb.toolTip()


def test_the_nozzle_field_stays_put_when_counts_change(window, app):
    w = window
    w.load_sync(TWO_PARTS)
    w.act_check.trigger()
    for _ in range(4):
        app.processEvents()
    x = lambda: w.check_nozzle.mapTo(w.check_box, w.check_nozzle.rect().topLeft()).x()
    before = x()
    w.check_nozzle.set_mm(0.45)
    w._check_nozzle_changed()
    w.check_rows["thin"][0].setChecked(True)
    w.check.wait_for_thin()                                                # "none" appears beside it
    for _ in range(4):
        app.processEvents()
    assert w.check_rows["thin"][1].text() == "none" and x() == before


def test_check_is_off_for_gcode(window):
    w = window
    w.load_sync(CUBE)
    w.act_check.trigger()
    w.load_sync(GCODE)
    assert not w.act_check.isEnabled() and w.check_box.isHidden() and not w.check.active


# ------------------------------------------------------------ the folder browser
def test_open_folder_lists_its_files_and_the_arrows_step_through(window, tmp_path, app):
    w = window
    d = tmp_path / "models"
    d.mkdir()
    for name in ("b.stl", "a.stl", "c.3mf"):
        shutil.copy(CUBE if name.endswith(".stl") else TWO_PARTS, d / name)
    (d / "notes.txt").write_text("not a model")
    assert w.act_open_folder in w.main_menu.actions()
    w.open_folder(str(d), sync=True)
    assert [os.path.basename(f) for f in w.folder["files"]] == ["a.stl", "b.stl", "c.3mf"]
    assert os.path.basename(w.current_path) == "a.stl" and w.folder_box.isVisible()
    assert w.folder_list.count() == 3 and w.folder_list.currentRow() == 0
    w._folder_loading = False
    w.load_sync = w.load_sync                              # (the arrow keys use load; make it sync here)
    w.load = w.load_sync
    w._arrow_key(-1)                                       # Down: the next file
    assert os.path.basename(w.current_path) == "b.stl" and w.folder_list.currentRow() == 1
    w._arrow_key(-1)
    assert os.path.basename(w.current_path) == "c.3mf"
    w._arrow_key(1)                                        # Up
    assert os.path.basename(w.current_path) == "b.stl"
    w.load_sync(TWO_PARTS)                                 # a file from elsewhere: the folder list goes
    assert w.folder is None and w.folder_box.isHidden()


def test_an_empty_folder_says_so(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    said = []
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: said.append(a)))
    window.open_folder(str(tmp_path))
    assert said and window.folder is None


# ------------------------------------------------------------ the line where the two whole planes meet
def test_a_faint_line_where_the_two_whole_planes_meet(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.act_clip_face.trigger()
    assert w.scene._cut_line is None or not w.scene._cut_line[1].GetVisibility()     # cut each other: no line
    w.settings.set("cut_planes_whole", True)
    w._apply_grid_label_settings()
    line, actor = w.scene._cut_line
    assert actor.GetVisibility() and actor.GetProperty().GetOpacity() < 0.8
    pts = np.asarray(line.points)
    assert np.allclose(pts[:, 2], w.scene.clip_z)                                    # in the height cut ...
    n = np.array(w.scene._face_plane.GetNormal())
    o = np.array(w.scene._face_plane.GetOrigin())
    assert np.allclose((pts - o) @ n, 0, atol=1e-6)                                 # ... and in the upright one
    w.act_clip.trigger()                                                             # one cut: no line
    assert not actor.GetVisibility()


# ------------------------------------------------------------ Settings: Apply
def test_apply_shows_the_settings_and_keeps_the_dialog_open(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    w.load_sync(CUBE)
    seen = []
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    dlg.applied.connect(w._settings_applied)
    dlg.applied.connect(lambda: seen.append(1))
    dlg.show()
    dlg.grid_labels_cb.setChecked(True)
    dlg.apply_btn.click()
    assert seen == [1] and dlg.isVisible() and w.grid_labels.enabled                # shown, still open
    dlg.line_slider.setValue(9)
    dlg.apply_btn.click()
    dlg.reject()                                                                     # Cancel after Apply
    assert w.settings.get("measure_line_width") == 9 and w.measure.line_width == 9   # keeps what was applied


def test_measurement_lines_slider_comes_before_the_cut_sliders(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(window.settings, window, {}, page="viewer")
    dlg.resize(900, 800)
    dlg.show()
    y = lambda sl: sl.mapTo(dlg, sl.rect().topLeft()).y()
    assert y(dlg.line_slider) < y(dlg.ghost_slider) < y(dlg.plane_slider)
    dlg.close()


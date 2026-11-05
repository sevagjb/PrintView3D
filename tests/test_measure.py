"""The Measure tool: distances, angles and circles on the model."""

import math
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402
from printview3d.ui import measure as ms  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE = os.path.join(HERE, "data", "cube_binary.stl")        # 20 mm cube, 0..20 on every axis
GCODE = os.path.join(HERE, "data", "cylinder.gcode")


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


def _screen(w, p):
    """Display position of a world point."""
    ren = w.plotter.renderer
    ren.SetWorldPoint(p[0], p[1], p[2], 1.0)
    ren.WorldToDisplay()
    d = ren.GetDisplayPoint()
    return int(round(d[0])), int(round(d[1]))


def _measuring(w, mode="distance"):
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)           # the offscreen window has no size until shown for real
    w.scene.set_view("iso", render=True)
    w.choose_measure_mode(mode)
    w.plotter.render()
    return w.measure


def _click(w, p):
    w.measure.click(*_screen(w, p))


# Corners of the cube that face the iso camera (front-right, from above): all but (0, 20, 0).
A, B, C, D = (0.0, 0.0, 0.0), (20.0, 0.0, 0.0), (20.0, 20.0, 0.0), (20.0, 20.0, 20.0)
TOP = (0.0, 0.0, 20.0)


# ------------------------------------------------------------ geometry
def test_distances():
    d, dx, dy, dz = ms.distances((0, 0, 0), (3, 4, 12))
    assert d == pytest.approx(13.0)
    assert (dx, dy, dz) == (3.0, 4.0, 12.0)
    assert ms.distances((1, 1, 1), (0, 1, 3))[1:] == (-1.0, 0.0, 2.0)       # signed: end minus start


def test_angle_at():
    assert ms.angle_at((1, 0, 0), (0, 0, 0), (0, 1, 0)) == pytest.approx(90.0)
    assert ms.angle_at((1, 0, 0), (0, 0, 0), (-1, 0, 0)) == pytest.approx(180.0)
    assert ms.angle_at((1, 0, 0), (0, 0, 0), (1, 1, 0)) == pytest.approx(45.0)
    assert ms.angle_at((0, 0, 0), (0, 0, 0), (1, 0, 0)) is None            # no side


def test_circle_through_three_points():
    c, r, n = ms.circle_through((0, 0, 0), (2, 0, 0), (0, 2, 0))
    assert np.allclose(c, (1, 1, 0)) and r == pytest.approx(2 ** 0.5)
    assert abs(n[2]) == pytest.approx(1.0)
    # a tilted circle in space: three points of a 10 mm radius circle around (5, 5, 5)
    pts = [np.array((5, 5, 5)) + 10 * np.array((math.cos(t), math.sin(t) * 0.6, math.sin(t) * 0.8))
           for t in (0.3, 2.0, 4.4)]
    c, r, _ = ms.circle_through(*pts)
    assert np.allclose(c, (5, 5, 5), atol=1e-9) and r == pytest.approx(10.0)
    assert ms.circle_through((0, 0, 0), (1, 1, 1), (2, 2, 2)) is None      # on a line


def test_arc_and_circle_points_lie_where_they_should():
    arc = ms.arc_points((0, 0, 0), (1, 0, 0), (0, 1, 0), 2.0)
    assert np.allclose(np.linalg.norm(arc, axis=1), 2.0)
    assert np.allclose(arc[0], (2, 0, 0)) and np.allclose(arc[-1], (0, 2, 0))
    ring = ms.circle_points((1, 2, 3), 4.0, (0, 0, 1))
    assert np.allclose(np.linalg.norm(ring - (1, 2, 3), axis=1), 4.0) and np.allclose(ring[0], ring[-1])


def test_shapes_and_labels():
    s = ms.shape_of("distance", [(0, 0, 0), (3, 4, 0)])
    assert s.values["distance"] == pytest.approx(5.0) and "5" in s.label[1] and len(s.dist_lines) == 1
    assert ms.shape_of("distance", [(0, 0, 0)]).values is None
    s = ms.shape_of("angle", [(1, 0, 0), (0, 0, 0), (0, 1, 0)])
    assert s.values["angle"] == pytest.approx(90.0) and "90" in s.label[1] and "°" in s.label[1]
    assert not s.dist_lines and len(s.lines) == 3                         # two sides and the arc
    s = ms.shape_of("circle", [(0, 0, 0), (2, 0, 0), (0, 2, 0)])
    assert s.values["diameter"] == pytest.approx(2 * 2 ** 0.5)
    assert "Ø" in s.label[1] and "R" in s.label[1] and not s.dist_lines
    assert ms.shape_of("angle", [(1, 0, 0), (0, 0, 0)]).label is None     # one side so far


def test_is_valid():
    assert not ms.is_valid("circle", [(0, 0, 0), (1, 1, 1), (2, 2, 2)])
    assert ms.is_valid("circle", [(0, 0, 0), (1, 1, 1)])                  # not finished: fine
    assert not ms.is_valid("angle", [(0, 0, 0), (0, 0, 0), (1, 0, 0)])
    assert ms.is_valid("distance", [(0, 0, 0), (0, 0, 0)])


# ------------------------------------------------------------ the button and the panel
def test_measure_is_off_without_a_model_and_for_gcode(window):
    w = window
    assert not w.act_measure.isEnabled() and not w.measure_btn.isEnabled() and w.measure_box.isHidden()
    w.load_sync(CUBE)
    assert w.act_measure.isEnabled() and w.measure_btn.isEnabled()
    w.load_sync(GCODE)
    assert not w.act_measure.isEnabled() and not w.measure_btn.isEnabled()


def test_toolbar_button_sits_next_to_view_and_only_opens_the_section(window):
    w = window
    tb = w.view_btn.parentWidget()
    assert w.measure_btn.parentWidget() is tb
    kids = [c for c in tb.findChildren(type(w.view_btn)) if c in (w.view_btn, w.measure_btn)]
    assert kids == [w.view_btn, w.measure_btn]                            # in toolbar order
    assert w.measure_btn.defaultAction() is w.act_measure
    assert w.measure_btn.menu() is None                                   # no menu: a plain switch
    assert not w.act_measure.icon().isNull()
    assert list(w.measure_actions) == ["distance", "angle", "circle"]
    assert w.act_measure.shortcut().toString() == "M"
    assert w.measure_actions["distance"].isChecked()


def test_mode_buttons_sit_side_by_side_in_the_section_with_icons(window):
    w = window
    buttons = [b for b in w.measure_box.findChildren(type(w.measure_btn)) if b.objectName() == "sectionButton"]
    assert [b.defaultAction() for b in buttons] == [w.measure_actions[k] for k in ("distance", "angle", "circle")]
    ys = {b.mapTo(w.measure_box, b.rect().topLeft()).y() for b in buttons}
    assert len(ys) == 1                                                   # one row
    assert all(not a.icon().isNull() for a in w.measure_actions.values())
    # snapping and dotted line side by side too
    cb1 = w.measure_snap_cb.mapTo(w.measure_box, w.measure_snap_cb.rect().topLeft()).y()
    cb2 = w.measure_dotted_cb.mapTo(w.measure_box, w.measure_dotted_cb.rect().topLeft()).y()
    assert cb1 == cb2 and w.measure_snap_cb.text() == "Snapping"
    # no value text in the section: the values are written next to the measurements
    assert not hasattr(w, "measure_info") and not hasattr(w, "measure_delta")


def test_toolbar_icons_for_plate_view_and_measure(window):
    w = window
    for a in (w.act_bed, w.act_view, w.act_measure):
        assert not a.icon().isNull()


def test_turning_it_on_shows_the_panel_and_off_hides_it(window):
    w = window
    m = _measuring(w)
    assert m.active and w.measure_box.isVisible() and w.act_measure.isChecked()
    assert w.controls.measure is m
    w.measure_close_btn.click()
    assert not m.active and not w.act_measure.isChecked() and w.measure_box.isHidden()


def test_choosing_a_mode_turns_measure_on_and_is_remembered(window, tmp_path):
    w = window
    w.load_sync(CUBE)
    assert not w.measure.active
    w.measure_actions["angle"].trigger()
    assert w.measure.active and w.measure.mode == "angle" and w.act_measure.isChecked()
    assert w.settings.get("measure_mode") == "angle"
    assert w.measure_actions["angle"].isChecked() and not w.measure_actions["distance"].isChecked()
    w.measure_actions["circle"].trigger()
    assert w.measure.mode == "circle" and w.measure_actions["circle"].isChecked()


def test_mode_is_restored_from_settings(app, tmp_path):
    from printview3d.ui import main_window as mw
    s = Settings(str(tmp_path / "settings.json"))
    s.set("measure_mode", "circle")
    s.set("measure_dotted", True)
    w = mw.MainWindow(s)
    try:
        assert w.measure.mode == "circle" and w.measure_actions["circle"].isChecked()
        assert w.measure.dotted and w.measure_dotted_cb.isChecked()
    finally:
        w.close()


def test_closing_the_file_turns_it_off(window):
    w = window
    m = _measuring(w)
    w.go_home()
    assert not m.active and not w.act_measure.isChecked()


# ------------------------------------------------------------ distance
def test_two_clicks_measure_a_corner_to_corner_line(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    assert len(m.current.points) == 1
    _click(w, D)
    d, dx, dy, dz = (m.current_values()[k] for k in ("distance", "dx", "dy", "dz"))
    assert d == pytest.approx(20 * 3 ** 0.5, abs=1e-3)
    assert (dx, dy, dz) == pytest.approx((20.0, 20.0, 20.0), abs=1e-3)
    assert m.label_texts == ["34.64 mm"]
    w.measure_deltas_cb.setChecked(True)                   # the distance along each axis, per distance
    assert w.settings.get("measure_deltas") is True
    assert m.label_texts[0].startswith("34.64 mm\n") and "ΔZ +20.00" in m.label_texts[0]
    w.measure_deltas_cb.setChecked(False)
    assert m.label_texts == ["34.64 mm"]


def test_live_line_follows_the_mouse_until_the_second_click(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    m.hover(*_screen(w, B))
    assert m.current_values()["distance"] == pytest.approx(20.0, abs=1e-3)
    m.hover(*_screen(w, C))
    assert m.current_values()["distance"] == pytest.approx(20 * 2 ** 0.5, abs=1e-3)
    _click(w, B)
    m.hover(*_screen(w, D))                                # finished: the mouse no longer matters
    assert m.current_values()["distance"] == pytest.approx(20.0, abs=1e-3)


def test_value_is_written_next_to_the_line(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, D)
    assert m.label_texts == ["34.64 mm"] and len(m.label_rects) == 1
    assert sum(1 for a in m._labels if a.GetVisibility()) == 1
    m.clear()
    assert m.label_texts == [] and not any(a.GetVisibility() for a in m._labels)


# ------------------------------------------------------------ several measurements
def test_measurements_stay_and_the_next_click_starts_another(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, B)
    _click(w, B)
    _click(w, C)
    assert len(m.items) == 2 and all(i.complete for i in m.items)
    assert np.allclose(m.items[0].points[1], B, atol=1e-3)
    assert len(m.label_texts) == 2
    assert w.measure_clear_btn.isEnabled()
    w.measure_clear_btn.click()
    assert m.items == [] and not w.measure_clear_btn.isEnabled()


def test_click_on_nothing_does_nothing(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    m.click(1, 1)
    assert len(m.items) == 1 and len(m.items[0].points) == 1


def test_changing_the_mode_drops_the_unfinished_measurement_only(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, B)
    _click(w, C)                                           # a second one, unfinished
    assert len(m.items) == 2
    w.measure_actions["angle"].trigger()
    assert len(m.items) == 1 and m.items[0].kind == "distance"


# ------------------------------------------------------------ angle
def test_angle_on_a_cube_corner(window):
    w = window
    m = _measuring(w, "angle")
    _click(w, B)                                           # one side
    _click(w, A)                                           # the corner
    _click(w, TOP)                                         # the other side
    v = m.current_values()
    assert v["kind"] == "angle" and v["angle"] == pytest.approx(90.0, abs=1e-3)
    assert m.label_texts == ["90.0°"]


def test_angle_live_preview(window):
    w = window
    m = _measuring(w, "angle")
    _click(w, B)
    _click(w, A)
    m.hover(*_screen(w, C))
    assert m.current_values()["angle"] == pytest.approx(45.0, abs=1e-3)


# ------------------------------------------------------------ circle
def test_circle_through_three_cube_corners(window):
    w = window
    m = _measuring(w, "circle")
    _click(w, A)
    _click(w, B)
    _click(w, C)                                           # three corners of a 20 mm square
    v = m.current_values()
    assert v["diameter"] == pytest.approx(20 * 2 ** 0.5, abs=1e-3)
    assert v["radius"] == pytest.approx(10 * 2 ** 0.5, abs=1e-3)
    assert m.label_texts == ["Ø 28.28 mm  ·  R 14.14 mm"]


def test_three_points_on_a_line_make_no_circle(window):
    w = window
    m = _measuring(w, "circle")
    _click(w, A)
    _click(w, B)
    _click(w, (10.0, 0.0, 0.0))                            # between them, on the same edge
    assert len(m.items) == 1 and len(m.items[0].points) == 2


# ------------------------------------------------------------ snapping
def test_snap_jumps_to_the_corner_and_can_be_turned_off(window):
    w = window
    m = _measuring(w)
    x, y = _screen(w, (20.0, 0.0, 20.0))
    m.click(x + 5, y + 3)                                  # a few pixels off the corner
    assert np.allclose(m.items[0].points[0], (20, 0, 20), atol=1e-3)
    m.clear()
    w.measure_snap_cb.setChecked(False)
    assert not m.snap
    m.click(x + 5, y + 3)
    assert not np.allclose(m.items[0].points[0], (20, 0, 20), atol=1e-3)


def test_snap_to_the_middle_of_an_edge(window):
    w = window
    m = _measuring(w)
    x, y = _screen(w, (10.0, 0.0, 0.0))                    # the middle of the bottom front edge
    pos, how = m._pick(x + 3, y + 2)
    assert how == "mid" and np.allclose(pos, (10, 0, 0), atol=1e-3)


def test_snap_to_a_point_on_an_edge(window):
    w = window
    m = _measuring(w)
    x, y = _screen(w, (5.0, 0.0, 0.0))                     # a quarter along the same edge
    pos, how = m._pick(x, y + 3)
    assert how == "edge" and np.allclose(pos[1:], (0, 0), atol=1e-3) and 3.5 < pos[0] < 6.5


def test_a_flat_face_has_no_edge_to_snap_to(window):
    w = window
    m = _measuring(w)
    x, y = _screen(w, (10.0, 10.0, 20.0))                  # the middle of the top face: the
    pos, how = m._pick(x, y)                               # triangulation's diagonal runs here
    assert how == "free" and pos[2] == pytest.approx(20.0, abs=1e-3)


# ------------------------------------------------------------ moving a point
def test_dragging_a_placed_point_moves_it(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, B)
    sx, sy = _screen(w, B)
    assert m.grab(sx + 2, sy + 1)
    m.drag_to(*_screen(w, C))
    m.drop()
    assert np.allclose(m.items[0].points[1], C, atol=1e-3)
    assert m.current_values()["distance"] == pytest.approx(20 * 2 ** 0.5, abs=1e-3)


def test_a_press_away_from_the_points_grabs_nothing(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, B)
    sx, sy = _screen(w, D)
    assert not m.grab(sx, sy)


def test_a_drag_cannot_turn_a_circle_into_a_line(window):
    w = window
    m = _measuring(w, "circle")
    _click(w, A)
    _click(w, B)
    _click(w, C)
    sx, sy = _screen(w, C)
    assert m.grab(sx, sy)
    m.drag_to(*_screen(w, (10.0, 0.0, 0.0)))               # onto the line A-B: refused
    m.drop()
    assert np.allclose(m.items[0].points[2], C, atol=1e-3)


# ------------------------------------------------------------ dotted
def test_dotted_checkbox_dots_distance_angle_and_circle(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, D)
    assert m._lines_poly.GetNumberOfLines() == 1                           # solid: one line
    w.measure_dotted_cb.setChecked(True)
    assert w.settings.get("measure_dotted") is True
    assert m._lines_poly.GetNumberOfLines() > 10                           # dotted: many dashes
    w.measure.clear()
    for mode, pts in (("angle", (B, A, TOP)), ("circle", (A, B, C))):
        w.measure_actions[mode].trigger()
        for p in pts:
            _click(w, p)
        assert m._lines_poly.GetNumberOfLines() > 20, mode
        w.measure.clear()
    w.measure_dotted_cb.setChecked(False)
    w.measure_actions["angle"].trigger()
    for p in (B, A, TOP):
        _click(w, p)
    assert m._lines_poly.GetNumberOfLines() == 3                           # sides + arc, solid again


def test_overlapping_values_are_stacked(window):
    w = window
    m = _measuring(w, "circle")
    for _ in range(2):                                     # the same circle twice: same centre
        for p in (A, B, C):
            _click(w, p)
    assert len(m.label_rects) == 2
    (x0, y0, w0, h0), (x1, y1, w1, h1) = m.label_rects
    assert y1 >= y0 + h0 or y0 >= y1 + h1                  # not on top of each other


def test_radius_is_exactly_half_of_the_diameter_shown():
    for d, expected in ((20.0, "10.00"), (19.99, "9.995"), (28.2843, "14.14"), (0.03, "0.015")):
        assert ms.half_text(d) == expected
    # the three numbers a circle of radius 9.996 shows: 19.99 across and 9.995 half of it
    c = ms.shape_of("circle", [(9.996, 0, 0), (0, 9.996, 0), (-9.996, 0, 0)])
    assert c.label[1] == "Ø 19.99 mm  ·  R 9.995 mm"


def test_value_boxes_have_rounded_corners(window):
    w = window
    m = _measuring(w)
    tex, width, height = m._label_picture("34.64 mm")
    img = tex.GetInput()
    from vtkmodules.util.numpy_support import vtk_to_numpy
    px = vtk_to_numpy(img.GetPointData().GetScalars()).reshape(height, width, 4)
    assert px[0, 0, 3] == 0 and px[-1, -1, 3] == 0 and px[0, -1, 3] == 0 and px[-1, 0, 3] == 0   # corners cut off
    assert px[height // 2, 2, 3] > 200                                                           # the box itself


# ------------------------------------------------------------ click vs. drag in the controls
def _patch_iren(w, monkeypatch, pos):
    monkeypatch.setattr(w.controls.iren, "GetEventPosition", lambda: pos[0], raising=False)
    monkeypatch.setattr(w.controls.iren, "GetShiftKey", lambda: 0, raising=False)


def test_click_places_a_point_and_does_not_set_the_pivot(window, monkeypatch):
    w = window
    m = _measuring(w)
    pos = [_screen(w, A)]
    _patch_iren(w, monkeypatch, pos)
    w.controls._left_down()
    assert w.controls.mode == "measure"
    pos[0] = (pos[0][0] + 1, pos[0][1])                    # a wobble is still a click
    w.controls._move()
    w.controls._button_up()
    assert len(m.items) == 1 and w.controls.mode is None


def test_drag_still_turns_the_view_and_places_nothing(window, monkeypatch):
    w = window
    m = _measuring(w)
    pos = [_screen(w, A)]
    _patch_iren(w, monkeypatch, pos)
    # The test is about click vs. drag, not about picking the rotation centre: that picker
    # (vtkPropPicker) renders to pick, which crashes on the offscreen window of the Windows and
    # macOS CI machines. The real app's drag is not affected.
    monkeypatch.setattr(w.controls, "_pick_pivot", lambda x, y: np.zeros(3))
    before = np.array(w.plotter.camera.position)
    w.controls._left_down()
    pos[0] = (pos[0][0] + 60, pos[0][1])
    w.controls._move()
    assert w.controls.mode == "rotate"
    w.controls._button_up()
    assert m.items == []
    assert not np.allclose(before, w.plotter.camera.position)


def test_drag_from_a_placed_point_moves_the_point_not_the_view(window, monkeypatch):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, B)
    pos = [_screen(w, B)]
    _patch_iren(w, monkeypatch, pos)
    before = np.array(w.plotter.camera.position)
    w.controls._left_down()
    pos[0] = _screen(w, C)
    w.controls._move()
    assert w.controls.mode == "measure_drag"
    w.controls._button_up()
    assert w.controls.mode is None
    assert np.allclose(m.items[0].points[1], C, atol=1e-3)
    assert np.allclose(before, w.plotter.camera.position)


# ------------------------------------------------------------ settings, reset view, themes
def test_settings_have_defaults():
    from printview3d.settings import DEFAULTS
    assert DEFAULTS["measure_mode"] == "distance" and DEFAULTS["measure_line_width"] == 4
    assert DEFAULTS["measure_dotted"] is False


def test_reset_view_keeps_the_measurements(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, B)
    w.reset_view()
    assert m.active and w.act_measure.isChecked() and len(m.items) == 1   # the measurements stay


def test_colours_follow_the_theme(window):
    w = window
    m = _measuring(w)
    w.apply_theme("dark")
    dark = m._line_rgb
    w.apply_theme("light")
    light = m._line_rgb
    assert dark != light and sum(dark) > sum(light)          # light lines on dark, dark on light
    assert m._lines.GetProperty().GetColor() == pytest.approx(tuple(v / 255 for v in light))
    from printview3d.ui import theme
    assert m._hover_rgb["corner"] == ms._rgb(theme.colors()["primary"])


def test_value_texts_go_through_translation(window, monkeypatch):
    from printview3d.ui import measure
    monkeypatch.setattr(measure, "tr", lambda t: {"{d} {unit}": "<{d}|{unit}>"}.get(t, t))
    s = measure.shape_of("distance", [(0, 0, 0), (3, 4, 0)])
    assert s.label[1] == "<5.00|mm>"


# ------------------------------------------------------------ snapping on, thin lines, real dots
def test_snapping_is_on_at_every_start(app, tmp_path):
    from printview3d.ui import main_window as mw
    s = Settings(str(tmp_path / "settings.json"))
    s.set("measure_snap", False)                           # an old choice from an earlier version
    w = mw.MainWindow(s)
    try:
        assert w.measure.snap and w.measure_snap_cb.isChecked()
    finally:
        w.close()


def test_options_sit_side_by_side_and_stack_in_a_narrow_panel(window, app):
    w = window
    boxes = (w.measure_snap_cb, w.measure_dotted_cb, w.measure_deltas_cb)
    assert w.measure_opts._widgets == list(boxes) and all(w.measure_opts.isAncestorOf(b) for b in boxes)
    # a row of its own, free to take any width
    from PySide6.QtWidgets import QCheckBox
    from printview3d.ui.main_window import _FitRow
    cbs = [QCheckBox("Snapping"), QCheckBox("Dotted line"), QCheckBox("Show ΔX ΔY ΔZ")]
    row = _FitRow(cbs)
    row.show()
    row.resize(900, 30)
    app.processEvents()
    assert not row.stacked
    assert len({b.mapTo(row, b.rect().topLeft()).y() for b in cbs}) == 1             # one line
    row.resize(120, 30)
    app.processEvents()
    assert row.stacked
    assert len({b.mapTo(row, b.rect().topLeft()).y() for b in cbs}) == 3             # one under the other
    row.resize(900, 30)
    app.processEvents()
    assert not row.stacked                                                           # and back
    row.close()


def test_line_width_follows_the_setting(window):
    w = window
    m = _measuring(w)
    assert m.line_width == 4 and m._lines.GetProperty().GetLineWidth() == 4
    w.set_measure_line_width(9)
    assert m.line_width == 9 and m._lines.GetProperty().GetLineWidth() == 9


def test_dots_are_round_dots_sized_by_the_line_width(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, D)
    w.measure_dotted_cb.setChecked(True)
    x0, y0 = _screen(w, A)
    x1, y1 = _screen(w, D)
    length_px = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    thin = m._lines_poly.GetNumberOfLines()
    assert thin == pytest.approx(length_px / (ms.DOT_PERIOD * 4), rel=0.2)   # one dot per 2.6 line widths
    w.set_measure_line_width(8)                            # thicker lines: bigger dots, further apart
    assert m._lines_poly.GetNumberOfLines() == pytest.approx(thin / 2, rel=0.25)
    # a dot is short: about a third of the line width, not a dash
    pts = m._lines_poly.GetPoints()
    p0, p1 = np.array(pts.GetPoint(0)), np.array(pts.GetPoint(1))
    assert np.linalg.norm(p1 - p0) < 0.5 * ms.DOT_PERIOD * m._world_per_px(p0) * 8 / 2.6


def test_dots_keep_their_size_on_the_screen_when_the_view_changes(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, D)
    w.measure_dotted_cb.setChecked(True)
    before = m._lines_poly.GetNumberOfLines()
    cam = w.plotter.renderer.GetActiveCamera()
    cam.Dolly(2.0)                                         # zoom in: the line is longer on the screen
    m._layout_labels()                                     # what runs before every frame
    assert m._lines_poly.GetNumberOfLines() > before * 1.5


def test_label_is_a_little_smaller_and_lighter(window):
    w = window
    m = _measuring(w)
    assert ms.LABEL_FONT_PX == 13 and ms.LABEL_PAD == (7, 3)
    tex, width, height = m._label_picture("34.64 mm")
    assert height <= 24                                    # one line of text with small padding


def test_settings_slider_for_the_line_thickness(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    w.load_sync(CUBE)
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    assert dlg.line_slider.value() == 4 and (dlg.line_slider.minimum(), dlg.line_slider.maximum()) == (1, 10)
    dlg.line_slider.setValue(9)
    assert w.measure.line_width == 9                       # seen while dragging
    dlg.reject()
    assert w.measure.line_width == 4 and w.settings.get("measure_line_width") == 4
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    dlg.line_slider.setValue(7)
    dlg._save()                                            # OK
    assert w.settings.get("measure_line_width") == 7 and w.measure.line_width == 7


def test_objects_box_says_in_text_that_the_colour_can_be_changed(window):
    w = window
    w.load_sync(os.path.join(HERE, "data", "two_parts.3mf"))
    assert "colour" in w.objects_hint.text().lower() and w.objects_hint.isVisible()   # plain text, not a tooltip


# ------------------------------------------------------------ thin dotted lines, black core dots, hints
def test_a_dotted_line_is_never_thinner_than_the_minimum(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, D)
    w.set_measure_line_width(1)
    assert m._lines.GetProperty().GetLineWidth() == 1                      # a solid thin line is fine
    w.measure_dotted_cb.setChecked(True)
    assert m.drawn_width() == ms.DOT_MIN_WIDTH == 3
    assert m._lines.GetProperty().GetLineWidth() == 3                      # dots at least 3 px
    w.set_measure_line_width(8)
    assert m._lines.GetProperty().GetLineWidth() == 8
    w.measure_dotted_cb.setChecked(False)
    w.set_measure_line_width(1)
    assert m._lines.GetProperty().GetLineWidth() == 1                      # solid again: thin again
    assert w.measure.line_width == 1                                       # the setting itself is untouched


def test_every_marker_has_a_small_black_dot(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, B)
    pts = m._core_poly.GetNumberOfPoints()
    assert pts >= 2 and pts == m._mark_poly.GetNumberOfPoints()            # one per marker
    assert m._core.GetProperty().GetColor() == (0.0, 0.0, 0.0)
    assert ms.CORE_PX < ms.MARKER_PX and m._core.GetProperty().GetPointSize() == ms.CORE_PX


def test_hints_for_the_measuring_tools_are_shown_in_the_3d_view(window):
    w = window
    assert w.hints.texts == []
    m = _measuring(w)                                                      # distance
    assert len(w.hints.texts) == 1 and "two points" in w.hints.texts[0] and "Drag a point" in w.hints.texts[0]
    w.measure_actions["angle"].trigger()
    assert "three points: one side, the corner" in w.hints.texts[0]
    w.measure_actions["circle"].trigger()
    assert "circle or hole" in w.hints.texts[0]
    assert not hasattr(w, "measure_hint")                                  # not in the side panel any more
    assert w.hints.sprites.shown() == 1
    x0, y0, width, height = w.hints.rects[0]
    view_w = w.plotter.renderer.GetSize()[0]
    assert x0 + width / 2 == pytest.approx(view_w / 2, abs=1.5) and y0 < 40         # bottom centre
    w.act_measure.setChecked(False)
    assert w.hints.texts == [] and w.hints.sprites.shown() == 0


def test_hints_stack_and_wrap_to_the_view(window):
    w = window
    m = _measuring(w)
    w.act_clip_face.trigger()                                              # the clip hint joins in
    assert len(w.hints.texts) == 2 and len(w.hints.rects) == 2
    (xa, ya, wa, ha), (xb, yb, wb, hb) = w.hints.rects
    assert yb >= ya + ha                                                   # stacked, not overlapping
    assert wa <= w.plotter.renderer.GetSize()[0] and wb <= w.plotter.renderer.GetSize()[0]
    from printview3d.ui.overlay_text import wrap
    assert "\n" in wrap("one two three four five six seven eight nine ten", 60)
    assert wrap("short", 500) == "short" and wrap("a\nb", 500) == "a\nb"


# ------------------------------------------------------------ another file: no old measurements on screen
def test_measurements_leave_the_screen_when_another_file_opens(window):
    w = window
    m = _measuring(w)
    _click(w, A)
    _click(w, D)
    assert m.label_texts and m._lines_poly.GetNumberOfLines() == 1
    w.load_sync(CUBE)                                    # dropped again, or another file
    assert m.items == []
    assert m.label_texts == [] and m._lines_poly.GetNumberOfLines() == 0       # gone from the view too
    assert m._mark_poly.GetNumberOfPoints() <= 1                               # at most the mouse's marker


def test_measurements_and_cuts_go_when_a_zip_shows_all_side_by_side(window, tmp_path):
    import zipfile
    w = window
    z = tmp_path / "two.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.write(CUBE, "a.stl")
        f.write(os.path.join(HERE, "data", "cube_ascii.stl"), "b.stl")
    w.load_sync(str(z))
    w.plotter.ren_win.SetSize(800, 600)
    w.scene.set_view("iso", render=True)
    w.act_measure.setChecked(True)
    m = w.measure
    _click(w, A)
    _click(w, D)
    w.act_clip.setChecked(True)
    assert m.label_texts and w.scene.clip_z is not None
    w.zip_show_all(sync=True)
    assert m.items == [] and m.label_texts == []
    assert not w.act_clip.isChecked() and w.scene.clip_z is None

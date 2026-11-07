"""View -> Clip and Measure together: snapping to the outline of a cut, and moving the cuts by
dragging their knobs in the 3D view (an option in Settings -> Viewer)."""

import math
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402
from printview3d.ui import measure as ms  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE = os.path.join(HERE, "data", "cube_binary.stl")        # 20 mm cube, 0..20 on every axis


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
    w.resize(1200, 760)
    w.show()
    return w


def _close(app, w):
    from PySide6.QtCore import QEvent
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


@pytest.fixture
def window(app, tmp_path):
    w = _make(app, tmp_path)
    yield w
    _close(app, w)


@pytest.fixture
def window_knobs(app, tmp_path):
    w = _make(app, tmp_path, clip_handles=True)
    yield w
    _close(app, w)


def _screen(w, p):
    ren = w.plotter.renderer
    ren.SetWorldPoint(p[0], p[1], p[2], 1.0)
    ren.WorldToDisplay()
    d = ren.GetDisplayPoint()
    return int(round(d[0])), int(round(d[1]))


def _cube(w, view="iso"):
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(800, 600)           # the offscreen window has no size until shown for real
    w.scene.set_view(view, render=True)
    w.plotter.render()


# ------------------------------------------------------------ the outline of a cut: geometry
def test_section_segments_of_a_cube_cut_halfway(window):
    w = window
    _cube(w)
    mesh = w.scene.model_actors[0].GetMapper().GetInput()
    seg = ms.section_segments(mesh, (0, 0, 10), (0, 0, -1))
    assert len(seg) >= 4 and np.allclose(seg[:, :, 2], 10.0)
    t = ms.section_targets(seg, 20.0)
    corners = {tuple(np.round(p, 6)) for p in t["corners"]}
    assert corners == {(0, 0, 10), (20, 0, 10), (20, 20, 10), (0, 20, 10)}
    mids = {tuple(np.round(p, 6)) for p in t["mids"]}
    assert mids == {(10, 0, 10), (20, 10, 10), (10, 20, 10), (0, 10, 10)}


def test_a_round_outline_has_no_corners_and_a_straight_run_has_one_middle():
    n = 64                                                  # a circle: 5.6° per point, smooth
    pts = [(10 * math.cos(2 * math.pi * k / n), 10 * math.sin(2 * math.pi * k / n), 0.0) for k in range(n)]
    circle = np.array([(pts[k], pts[(k + 1) % n]) for k in range(n)])
    t = ms.section_targets(circle, 20.0)
    assert len(t["corners"]) == 0 and len(t["mids"]) == 0 and len(t["segments"]) == n
    # A straight line cut into pieces (the diagonals of a flat face cross it): ends are corners.
    line = np.array([((0, 0, 0), (3, 0, 0)), ((3, 0, 0), (7, 0, 0)), ((7, 0, 0), (10, 0, 0))], dtype=float)
    t = ms.section_targets(line, 10.0)
    assert {tuple(p) for p in t["corners"]} == {(0, 0, 0), (10, 0, 0)}
    assert np.allclose(t["mids"], [(5, 0, 0)])


def test_clip_segments_keeps_what_the_cut_keeps():
    seg = np.array([((0, 0, 0), (10, 0, 0)),            # crosses x = 4: keeps 4..10
                    ((0, 1, 0), (2, 1, 0)),              # all on the far side: goes
                    ((5, 2, 0), (9, 2, 0))], dtype=float)  # all kept
    out = ms.clip_segments(seg, (4, 0, 0), (1, 0, 0))
    assert len(out) == 2
    assert np.allclose(out[0], [(4, 0, 0), (10, 0, 0)]) and np.allclose(out[1], seg[2])


# ------------------------------------------------------------ snapping to it
def test_snaps_to_the_outline_of_the_cut_like_an_edge(window):
    w = window
    _cube(w)
    w.choose_measure_mode("distance")
    m = w.measure
    # Without a cut there is nothing at half height on the cube's front edge but its face.
    x, y = _screen(w, (12, 0, 10.3))
    assert m._pick(x, y)[1] == "free"
    w.act_clip.setChecked(True)                          # cut at half height
    w.plotter.render()
    assert w.scene.clip_z == pytest.approx(10.0)
    pos, how = m._pick(*_screen(w, (20, 20, 10)))
    assert how == "corner" and np.allclose(pos, (20, 20, 10))
    pos, how = m._pick(*_screen(w, (10, 0, 10)))
    assert how == "mid" and np.allclose(pos, (10, 0, 10))
    pos, how = m._pick(x, y)
    assert how == "edge" and pos[2] == pytest.approx(10.0) and pos[1] == pytest.approx(0.0)
    # The far corner of the cut: seen through the open top, so it can be snapped to.
    pos, how = m._pick(*_screen(w, (0, 20, 10)))
    assert how == "corner" and np.allclose(pos, (0, 20, 10))


def test_a_click_measures_between_two_corners_of_the_cut(window):
    w = window
    _cube(w)
    w.choose_measure_mode("distance")
    w.act_clip.setChecked(True)
    w.plotter.render()
    w.measure.click(*_screen(w, (20, 0, 10)))
    w.measure.click(*_screen(w, (20, 20, 10)))
    v = w.measure.current_values()
    assert v["distance"] == pytest.approx(20.0, abs=1e-6) and v["dz"] == pytest.approx(0.0, abs=1e-6)


def test_the_outline_hidden_behind_the_model_is_not_snapped_to(window):
    w = window
    _cube(w, view="bottom")
    w.choose_measure_mode("distance")
    w.act_clip.setChecked(True)
    w.plotter.render()
    # From below, the cut at half height is behind the cube's bottom: its corner is not offered.
    pos, how = w.measure._pick(*_screen(w, (20, 20, 10)))
    assert pos[2] == pytest.approx(0.0, abs=1e-6) and not np.allclose(pos, (20, 20, 10))


def test_snaps_to_the_outline_of_clip_facing_you(window):
    w = window
    _cube(w, view="front")
    w.choose_measure_mode("distance")
    w.act_clip_face.setChecked(True)                     # upright, through the centre: y = 10
    w.plotter.render()
    o, n = w.scene.face_plane()
    assert np.allclose(n, (0, 1, 0)) and o[1] == pytest.approx(10.0)
    pos, how = w.measure._pick(*_screen(w, (20, 10, 20)))
    assert how == "corner" and np.allclose(pos, (20, 10, 20))


def test_no_cut_no_outline_and_snapping_off_ignores_it(window):
    w = window
    _cube(w)
    w.choose_measure_mode("distance")
    assert w.measure._section() is None
    w.act_clip.setChecked(True)
    w.plotter.render()
    w.measure_snap_cb.setChecked(False)
    pos, how = w.measure._pick(*_screen(w, (10, 0, 10)))
    assert how == "free"


def test_the_outline_follows_the_cut(window):
    w = window
    _cube(w)
    w.choose_measure_mode("distance")
    w.act_clip.setChecked(True)
    w.plotter.render()
    first = w.measure._section()["corners"][:, 2]
    w.clip_slider.setValue(250)                          # a quarter of the way up: 5 mm
    w.plotter.render()
    assert np.allclose(first, 10.0) and np.allclose(w.measure._section()["corners"][:, 2], 5.0)


# ------------------------------------------------------------ knobs to drag the cuts
def test_knobs_are_off_by_default_and_the_setting_sits_under_the_planes_option(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    _cube(w)
    w.act_clip.setChecked(True)
    assert w.settings.get("clip_handles") is False
    assert w.clip_handles.hit(*_screen(w, (22, 22, 10))) is None and w.clip_handles.shown == []
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    lay = dlg.cut_planes_cb.parentWidget().layout()
    assert lay.indexOf(dlg.clip_handles_cb) == lay.indexOf(dlg.cut_planes_cb) + 1
    assert not dlg.clip_handles_cb.isChecked()
    dlg.clip_handles_cb.setChecked(True)
    dlg._save(close=True)
    w._settings_applied()
    assert w.settings.get("clip_handles") is True and w.clip_handles.enabled
    w.clip_handles.refresh()
    assert w.clip_handles.shown == ["top"]


def test_a_knob_per_cut_that_is_on(window_knobs):
    w = window_knobs
    _cube(w)
    h = w.clip_handles
    h.refresh()
    assert h.shown == []
    w.act_clip.setChecked(True)
    h.refresh()
    assert h.shown == ["top"]
    knob, axis = h._knobs["top"]
    assert knob[2] == pytest.approx(10.0) and np.allclose(axis, (0, 0, 1))
    w.act_clip_face.setChecked(True)
    h.refresh()
    assert sorted(h.shown) == ["face", "top"]
    knob, _ = h._knobs["face"]
    assert knob[2] == pytest.approx(10.0)                # on the upright cut, where the flat one cuts it
    # The flat cut's knob is never in the part Clip facing you takes away.
    o, n = w.scene.face_plane()
    assert float((h._knobs["top"][0] - o) @ n) >= 0
    w.act_clip.setChecked(False)
    w.act_clip_face.setChecked(False)
    h.refresh()
    assert h.shown == []


def test_dragging_the_knob_moves_the_cut_and_its_slider(window_knobs):
    w = window_knobs
    _cube(w)
    w.act_clip.setChecked(True)
    h = w.clip_handles
    h.refresh()
    x, y = (int(round(v)) for v in h._to_screen(h._knobs["top"][0]))
    assert h.hit(x, y) == "top"
    assert h.begin("top", x, y)
    h.drag_to(x, y + 40)                                 # up on the screen: higher
    assert w.clip_slider.value() > 500 and w.scene.clip_z > 10.0
    up = w.scene.clip_z
    h.drag_to(x, y - 40)                                 # down: lower
    assert w.scene.clip_z < 10.0 < up
    h.drag_to(x, y - 4000)                               # never below the bottom
    assert w.clip_slider.value() == 0
    h.end()
    assert "Height 0.0 of 20.0" in w.clip_info.text()


def test_dragging_the_facing_knob_moves_that_cut(window_knobs):
    w = window_knobs
    _cube(w)
    w.act_clip_face.setChecked(True)
    h = w.clip_handles
    h.refresh()
    x, y = (int(round(v)) for v in h._to_screen(h._knobs["face"][0]))
    assert h.begin("face", x, y)
    h.drag_to(x, y + 40)                                 # up on the screen: further away
    h.end()
    assert w.face_slider.value() > 500 and w.scene.clip_face > 0


def test_a_press_on_a_knob_moves_the_cut_not_the_view(window_knobs, monkeypatch):
    w = window_knobs
    _cube(w)
    w.act_clip.setChecked(True)
    h = w.clip_handles
    h.refresh()
    pos = [tuple(int(round(v)) for v in h._to_screen(h._knobs["top"][0]))]
    monkeypatch.setattr(w.controls.iren, "GetEventPosition", lambda: pos[0], raising=False)
    monkeypatch.setattr(w.controls.iren, "GetShiftKey", lambda: 0, raising=False)
    before = np.array(w.plotter.camera.position)
    w.controls._left_down()
    assert w.controls.mode == "clip_handle"
    pos[0] = (pos[0][0], pos[0][1] + 30)
    w.controls._move()
    w.controls._button_up()
    assert w.controls.mode is None and h.dragging is None
    assert w.scene.clip_z > 10.0
    assert np.allclose(before, w.plotter.camera.position)


def test_knobs_light_up_under_the_mouse_and_measure_waits(window_knobs):
    w = window_knobs
    _cube(w)
    w.choose_measure_mode("distance")
    w.act_clip.setChecked(True)
    h = w.clip_handles
    h.refresh()
    x, y = (int(round(v)) for v in h._to_screen(h._knobs["top"][0]))
    w.controls._hover(x, y)
    assert h.hover == "top" and w.measure.hover_point is None
    w.controls._hover(x - 200, y)
    assert h.hover is None


# ------------------------------------------------------------ screenshot key
def test_screenshot_has_a_key(window):
    from PySide6.QtGui import QKeySequence
    w = window
    assert w.act_screenshot.shortcut() == QKeySequence("Ctrl+Shift+S")
    assert w.act_screenshot in w.actions()                   # works wherever the focus is
    key = QKeySequence("Ctrl+Shift+S").toString(QKeySequence.NativeText)
    assert w.act_screenshot.toolTip() == "Screenshot" and key not in w.act_screenshot.toolTip()


def test_a_lit_knob_looks_different_in_every_theme(window_knobs):
    from printview3d.ui import theme
    w = window_knobs
    _cube(w)
    w.act_clip.setChecked(True)
    h = w.clip_handles
    for style in theme.STYLES:
        for mode in ("light", "dark"):
            h.set_colors(theme.colors(theme.theme_for(style, mode)))
            h.set_hover(None)
            normal = h.colors_of("top")
            h.set_hover("top")
            lit = h.colors_of("top")
            assert lit != normal and lit[0] != normal[0], (style, mode)
            assert normal[0] != normal[1]                       # the ring shows against the disc


# ------------------------------------------------------------ lock the facing cut
def test_lock_key_and_button_are_one(window):
    from PySide6.QtGui import QKeySequence
    w = window
    _cube(w)
    assert w.act_lock_face.shortcut() == QKeySequence("L") and w.act_lock_face in w.actions()
    w.act_clip_face.setChecked(True)
    assert w.view_lock_btn.isVisible()
    w.act_lock_face.trigger()                                # the key
    assert w.view_lock_btn.isChecked() and w.scene.freeze_face
    w.view_lock_btn.click()                                  # the button
    assert not w.act_lock_face.isChecked() and not w.scene.freeze_face
    w.act_clip_face.setChecked(False)
    assert w.view_lock_btn.isHidden()


def test_measure_warns_while_the_facing_cut_turns(window):
    w = window
    _cube(w)
    note = w.measure_cut_note
    w.choose_measure_mode("distance")
    assert note.isHidden()                                   # no cut
    w.act_clip.setChecked(True)
    assert note.isHidden()                                   # the flat cut never turns
    w.act_clip_face.setChecked(True)
    assert note.isVisible() and "●" in w.measure_cut_dot.text()
    assert w.measure_cut_text.toolTip() == note.toolTip()
    tip = note.toolTip()
    assert "Lock facing cut stops" in tip and "hanging in the air" in tip and "slider" not in tip
    assert "(L)" not in tip                                   # no keys in tooltips
    assert "before measuring" not in tip                       # some want to turn the cut on purpose
    # one line where it fits; a line can only break between the two sentences
    assert w.measure_cut_text.text() == "Facing cut not locked. Hover for details"
    assert w.measure_cut_text.wordWrap()                       # a long translation wraps, not cut short
    w.act_lock_face.setChecked(True)
    assert note.isHidden()
    w.act_lock_face.setChecked(False)
    assert note.isVisible()
    w.act_measure.setChecked(False)
    assert note.isHidden()                                   # Measure off


def test_the_note_never_moves_clear_and_close(window):
    from PySide6.QtCore import QPoint
    w = window
    _cube(w)
    w.choose_measure_mode("distance")
    w.act_clip_face.setChecked(True)
    w.act_lock_face.setChecked(True)
    where = lambda: [b.mapTo(w.measure_box, QPoint(0, 0)).x() for b in (w.measure_clear_btn, w.measure_close_btn)]
    hidden = where()
    w.act_lock_face.setChecked(False)
    assert w.measure_cut_note.isVisible() and where() == hidden
    note = w.measure_cut_note.mapTo(w.measure_box, QPoint(0, 0))
    assert note.x() < hidden[0]                                   # left of Clear, on its row
    assert abs(note.y() + w.measure_cut_note.height() / 2
               - (w.measure_clear_btn.mapTo(w.measure_box, QPoint(0, 0)).y() + w.measure_clear_btn.height() / 2)) <= 1


def test_section_buttons_carry_their_keys(window):
    from PySide6.QtGui import QKeySequence
    w = window
    native = lambda k: QKeySequence(k).toString(QKeySequence.NativeText)
    assert w.measure_close_btn.text() == f"Close ({native('M')})"   # what M does while Measure is on
    assert w.view_close_btn.text() == f"Close ({native('V')})"      # what V does while View is open
    assert w.measure_clear_btn.text() == f"Clear ({native('K')})"


def test_k_clears_the_measurements_and_measure_stays_on(window):
    w = window
    _cube(w)
    w.choose_measure_mode("distance")
    w.measure.click(*_screen(w, (0, 0, 0)))
    w.measure.click(*_screen(w, (20, 0, 0)))
    assert w.measure.has_items
    w.key_targets["measure_clear"].activated.emit()
    assert not w.measure.has_items and w.measure.active and w.act_measure.isChecked()


def test_sliders_sit_under_their_buttons(window):
    from PySide6.QtCore import QPoint
    w = window
    _cube(w)
    w.act_clip.setChecked(True)
    w.act_clip_face.setChecked(True)
    x = lambda wdg: wdg.mapTo(w.view_box, QPoint(0, 0)).x()
    buttons = {b.defaultAction(): b for b in w.view_box.findChildren(type(w.view_btn)) if b.defaultAction()}
    top_btn, face_btn = buttons[w.act_clip], buttons[w.act_clip_face]
    assert x(w.clip_top_row) == x(top_btn) and x(w.clip_face_row) == x(face_btn)
    y = w.clip_face_row.mapTo(w.view_box, QPoint(0, 0)).y()
    w.act_clip.setChecked(False)                                   # its column stays, empty
    assert x(w.clip_face_row) == x(face_btn) and w.clip_face_row.mapTo(w.view_box, QPoint(0, 0)).y() == y


def test_hints_name_their_section(window_knobs):
    w = window_knobs
    _cube(w)
    w.choose_measure_mode("angle")
    w.act_clip_face.setChecked(True)
    texts = w.hints.texts
    assert any(t.startswith("Measure: Click three points") for t in texts)
    clip = [t for t in texts if t.startswith("Clip: ")]
    assert len(clip) == 1 and "pass the model through the cutting plane" in clip[0]
    assert "Drag a round handle" in clip[0]                        # the handles are on
    w.act_lock_face.setChecked(True)
    clip = [t for t in w.hints.texts if t.startswith("Clip: ")][0]
    assert "is locked" in clip and "pass the model" not in clip
    w.act_lock_face.setChecked(False)
    w.clip_handles.set_enabled(False)
    w._update_hints()
    clip = [t for t in w.hints.texts if t.startswith("Clip: ")][0]
    assert "handle" not in clip


def test_drag_option_says_also_and_mouse_comes_before_keyboard(window):
    from PySide6.QtWidgets import QGroupBox
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    assert dlg.clip_handles_cb.text() == "Also move the cutting planes by dragging them in the 3D view"
    page = dlg.pages.widget(dlg._page_keys.index("keys")).widget()
    titles = [g.title() for g in page.findChildren(QGroupBox)]
    assert titles.index("Mouse") < titles.index("Keyboard")
    dlg.close()


def test_options_are_centred_toggle_buttons_with_room_around(window):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QPushButton
    from printview3d.ui import main_window as mw
    w = window
    _cube(w)
    w.act_clip.setChecked(True)
    w.act_clip_face.setChecked(True)
    w.choose_measure_mode("distance")
    vb, mb = w.view_box, w.measure_box
    pos = lambda b, box: b.mapTo(box, QPoint(0, 0))
    gap = lambda above, below, box: pos(below, box).y() - (pos(above, box).y() + above.height())
    for box, opts in ((vb, (w.clip_ghost_cb, w.clip_plane_cb)),
                      (mb, (w.measure_snap_cb, w.measure_dotted_cb, w.measure_deltas_cb))):
        assert all(isinstance(b, QPushButton) and b.isCheckable() and b.objectName() == "toggleButton"
                   for b in opts)
        assert len({pos(b, box).y() for b in opts}) == 1                       # one row
        left, right = pos(opts[0], box).x(), pos(opts[-1], box).x() + opts[-1].width()
        assert abs(left - (box.width() - right)) <= 2                          # centred in the section
        assert opts[0].height() < w.view_lock_btn.height()                     # a little lower
    # the defaults of the checkboxes they were
    assert w.clip_ghost_cb.isChecked() and w.clip_plane_cb.isChecked() and w.measure_snap_cb.isChecked()
    assert not w.measure_dotted_cb.isChecked() and not w.measure_deltas_cb.isChecked()
    assert gap(w.clip_plane_cb, w.view_reset_btn, vb) >= 12
    assert gap(w.measure_snap_cb, w.measure_clear_btn, mb) >= 12
    btn = mb.findChildren(mw._FitButton)[0]
    assert gap(btn, w.measure_snap_cb, mb) >= 8


def test_even_rows_still_stack_in_a_narrow_panel(app):
    from PySide6.QtWidgets import QCheckBox
    from printview3d.ui.main_window import _FitRow
    cbs = [QCheckBox("Snapping"), QCheckBox("Dotted line"), QCheckBox("Show ΔX ΔY ΔZ")]
    row = _FitRow(cbs, spacing=6, even=True)
    row.show()
    row.resize(600, 30)
    app.processEvents()
    xs = [b.x() for b in cbs]
    assert not row.stacked and xs[1] - xs[0] == xs[2] - xs[1]           # equal columns
    row.resize(120, 30)
    app.processEvents()
    assert row.stacked
    row.close()


def test_no_tooltip_names_a_key(window):
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QWidget
    from printview3d.ui import keys
    w = window
    _cube(w)
    w.act_clip_face.setChecked(True)
    w.choose_measure_mode("distance")
    shown = {f"({keys.native(k)})" for k in w.keys.values() if k}
    tips = [a.toolTip() for a in w.findChildren(QAction)] + [x.toolTip() for x in w.findChildren(QWidget)]
    bad = [t for t in tips if t and any(s in t for s in shown)]
    assert bad == []


def test_both_sliders_show_and_the_unused_one_is_greyed_out(window):
    w = window
    _cube(w)
    w.act_clip_face.setChecked(True)                             # only the facing cut
    assert w.clip_top_row.isVisible() and w.clip_face_row.isVisible()
    assert not w.clip_slider.isEnabled() and w.face_slider.isEnabled()
    assert w.clip_info.text() == "Height" and w.face_info.text().startswith("Depth ")
    w.act_clip.setChecked(True)
    assert w.clip_slider.isEnabled() and w.clip_info.text().startswith("Height ")
    w.act_clip_face.setChecked(False)
    assert not w.face_slider.isEnabled() and w.face_info.text() == "Depth"
    w.act_clip.setChecked(False)
    assert w.clip_box.isHidden()                                 # no cut: no sliders


def test_note_has_room_after_its_dot_and_measure_options_room_above(window):
    from PySide6.QtCore import QPoint
    from printview3d.ui import main_window as mw
    w = window
    _cube(w)
    w.choose_measure_mode("distance")
    w.act_clip_face.setChecked(True)
    assert w.measure_cut_note.layout().spacing() >= 8
    mb = w.measure_box
    btn = mb.findChildren(mw._FitButton)[0]
    gap = w.measure_snap_cb.mapTo(mb, QPoint(0, 0)).y() - (btn.mapTo(mb, QPoint(0, 0)).y() + btn.height())
    assert gap >= 8

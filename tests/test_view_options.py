"""View menu: wireframe, X-ray, clip from the top and clip facing you for models (issue #60)."""

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
INSIDE = os.path.join(DATA, "inside_view.3mf")     # hollow box (0..30 mm), hidden part, 40 mm tube
CUBE = os.path.join(DATA, "cube_binary.stl")
GCODE = os.path.join(DATA, "cylinder.gcode")


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


def _props(w):
    return [a.GetProperty() for a in w.scene.model_actors]


def _planes(w):
    return [a.GetMapper().GetNumberOfClippingPlanes() for a in w.scene.model_actors]


def test_view_menu_is_off_without_a_model(window):
    w = window
    assert not w.view_btn.isEnabled()
    assert not any(a.isEnabled() for a in (w.act_wireframe, w.act_xray, w.act_clip))
    assert w.clip_box.isHidden()


def test_view_menu_on_for_models_off_for_gcode(window):
    w = window
    w.load_sync(INSIDE)
    assert w.view_btn.isEnabled() and w.act_clip.isEnabled()
    w.load_sync(GCODE)
    assert not w.view_btn.isEnabled() and not w.act_wireframe.isEnabled()
    w.go_home()
    assert not w.view_btn.isEnabled()


def test_view_button_opens_a_section_with_all_options_as_buttons(window):
    w = window
    assert w.view_btn.menu() is None and w.view_btn.defaultAction() is w.act_view
    assert w.act_view.isCheckable() and not w.act_view.icon().isNull()
    actions = [w.act_wireframe, w.act_xray, w.act_clip, w.act_clip_face]
    buttons = [b for b in w.view_box.findChildren(type(w.view_btn)) if b.objectName() == "sectionButton"]
    assert [b.defaultAction() for b in buttons] == actions                # every option, as a button
    assert all(not a.icon().isNull() for a in actions)
    assert w.view_box.isHidden()                                          # nothing open yet
    w.load_sync(INSIDE)
    assert w.view_box.isHidden()                                          # a model is not enough: closed
    w.act_view.trigger()
    assert w.view_box.isVisible() and w.view_btn.isChecked()
    w.act_view.trigger()
    assert w.view_box.isHidden()


def test_view_section_has_reset_view_and_close_buttons_and_no_turn_off_button(window):
    w = window
    w.load_sync(INSIDE)
    w.act_view.trigger()
    assert not hasattr(w, "clip_off_btn")
    w.act_wireframe.trigger()
    w.act_clip.trigger()
    assert w.act_wireframe.isChecked() and w.act_clip.isChecked()
    w.view_reset_btn.click()                                              # Reset view, as R does
    assert not w.act_wireframe.isChecked() and not w.act_clip.isChecked()
    assert w.view_box.isVisible()                                         # the section stays open
    w.view_close_btn.click()
    assert w.view_box.isHidden() and not w.act_view.isChecked()


def test_the_clip_controls_live_in_the_view_section_and_open_it(window):
    w = window
    w.load_sync(INSIDE)
    assert w.view_box.isHidden()
    w.act_clip_face.trigger()                                             # V with the section closed
    assert w.view_box.isVisible() and w.act_view.isChecked()              # opens it
    assert w.view_box.isAncestorOf(w.clip_box) and w.clip_box.isVisible()
    # the freeze checkbox is under the other two (cut-away part, cutting plane)
    ys = [cb.mapTo(w.view_box, cb.rect().topLeft()).y() for cb in (w.clip_ghost_cb, w.clip_plane_cb, w.view_freeze_cb)]
    assert ys == sorted(ys) and len(set(ys)) == 3
    w.act_clip_face.trigger()
    assert w.clip_box.isHidden()                                          # no cut: no cut controls


def test_menu_and_shortcuts(window):
    w = window
    actions = [w.act_wireframe, w.act_xray, w.act_clip, w.act_clip_face, w.act_reset_view]
    assert [a.shortcut().toString() for a in actions] == ["W", "X", "C", "V", "R"]
    assert w.act_measure in w.actions() and w.act_measure.shortcut().toString() == "M"
    for a in actions:
        assert a in w.actions()                           # work wherever the focus is


def test_wireframe(window):
    w = window
    w.load_sync(INSIDE)
    assert all(p.GetRepresentation() == 2 for p in _props(w))        # surface
    w.act_wireframe.trigger()
    assert w.scene.wireframe
    assert all(p.GetRepresentation() == 1 and not p.GetLighting() for p in _props(w))
    w.act_wireframe.trigger()
    assert all(p.GetRepresentation() == 2 and p.GetLighting() for p in _props(w))


def test_xray_makes_parts_see_through_with_depth_peeling(window):
    from printview3d.ui.scene import XRAY_OPACITY
    w = window
    w.load_sync(INSIDE)
    renderer = w.plotter.renderer
    assert not renderer.GetUseDepthPeeling()
    w.act_xray.trigger()
    assert all(p.GetOpacity() == pytest.approx(XRAY_OPACITY) for p in _props(w))
    assert renderer.GetUseDepthPeeling()
    w.act_xray.trigger()
    assert all(p.GetOpacity() == 1.0 for p in _props(w))
    assert not renderer.GetUseDepthPeeling()                         # costs nothing when off


def test_depth_peeling_off_after_closing_the_file(window):
    w = window
    w.load_sync(INSIDE)
    w.act_xray.trigger()
    w.go_home()
    assert not w.plotter.renderer.GetUseDepthPeeling()


def test_clip_starts_halfway_and_follows_the_slider(window):
    w = window
    w.load_sync(INSIDE)
    assert _planes(w) == [0, 0, 0]
    w.act_clip.trigger()
    assert w.clip_box.isVisible()
    assert w.scene.clip_z == pytest.approx(20.0)                     # half of 0..40 mm
    assert _planes(w) == [1, 1, 1]
    assert all(a.GetBackfaceProperty() is not None for a in w.scene.model_actors)
    assert "20" in w.clip_info.text() and "40" in w.clip_info.text()

    w.clip_slider.setValue(250)
    assert w.scene.clip_z == pytest.approx(10.0)
    plane = w.scene._top_plane
    assert plane.GetOrigin()[2] == pytest.approx(10.0)
    assert plane.GetNormal() == pytest.approx((0, 0, -1))           # keeps what is below

    w.clip_slider.setValue(w.CLIP_STEPS)                             # all the way up: no cut
    assert w.scene.clip_z is None and _planes(w) == [0, 0, 0]


def test_clip_turn_off_button_and_shortcut(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.act_clip.setChecked(False)
    w.act_clip_face.setChecked(False)
    assert not w.act_clip.isChecked() and w.clip_box.isHidden()
    assert w.scene.clip_z is None and _planes(w) == [0, 0, 0]
    assert all(a.GetBackfaceProperty() is None for a in w.scene.model_actors)


def test_wireframe_and_xray_stay_for_the_next_model_but_the_cuts_go(window):
    w = window
    w.load_sync(INSIDE)
    w.act_xray.trigger()
    w.act_clip.trigger()
    w.clip_slider.setValue(250)
    w.load_sync(GCODE)
    assert w.clip_box.isHidden() and not w.act_clip.isChecked()
    a = w.scene.p.actors.get("gcode")
    assert a is None or a.GetMapper().GetNumberOfClippingPlanes() == 0   # toolpaths untouched
    w.load_sync(CUBE)                                                    # 20 mm cube
    assert all(p.GetOpacity() < 1 for p in _props(w))                    # X-ray stays
    assert w.clip_box.isHidden() and w.scene.clip_z is None and _planes(w) == [0]   # the cut is gone


def test_options_combine(window):
    w = window
    w.load_sync(INSIDE)
    for a in (w.act_wireframe, w.act_xray, w.act_clip):
        a.trigger()
    p = _props(w)[0]
    assert p.GetRepresentation() == 1 and p.GetOpacity() < 1 and _planes(w)[0] == 1
    assert w.scene._cut_prop.GetOpacity() == pytest.approx(p.GetOpacity())   # cut faces see-through too


def test_hiding_an_object_keeps_the_view_options(window, app):
    from PySide6.QtWidgets import QCheckBox
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    boxes = w.objects_box.findChildren(QCheckBox)
    boxes[0].setChecked(False)
    boxes[0].setChecked(True)
    assert _planes(w) == [1, 1, 1]


def test_shortcuts_on_the_about_page(app):
    from printview3d.ui.settings_dialog import shortcut_rows
    keys = [k for row, _ in shortcut_rows() for k in row]
    for k in ("W", "X", "C", "V"):
        assert k in keys


def test_arabic_keeps_the_slider_left_to_right(window, app):
    from PySide6.QtCore import Qt
    assert window.clip_slider.layoutDirection() == Qt.LeftToRight


# ---------------------------------------------------------------- Clip facing you

def _face_normal_after(w, view):
    w.scene.set_view(view, render=False)
    w.scene._update_face_plane()             # what happens before every frame
    return w.scene._face_plane.GetNormal()


def test_clip_facing_you_starts_through_the_centre_and_follows_the_slider(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    assert w.clip_box.isVisible() and any('pass the model through the cut' in t for t in w.hints.texts)
    assert w.scene.clip_face == pytest.approx(0.0) and w.scene.clip_z is None
    assert _planes(w) == [1, 1, 1]
    assert all(a.GetBackfaceProperty() is not None for a in w.scene.model_actors)
    reach = w.scene.model_face_reach()
    w.face_slider.setValue(w.CLIP_STEPS)                     # all the way: further away
    assert w.scene.clip_face == pytest.approx(reach)
    depth, total = w.scene.face_cut_depth()                  # ... out of the model's far side
    assert depth == pytest.approx(total) and f"of {total:.1f} mm" in w.face_info.text()
    w.face_slider.setValue(0)                                # nearer
    assert w.scene.clip_face == pytest.approx(-reach)
    assert w.scene.face_cut_depth()[0] == pytest.approx(0.0)  # in front of the model: depth 0
    w.face_slider.setValue(w.CLIP_STEPS // 2)
    assert 0 < w.scene.face_cut_depth()[0] < total and w.face_info.text().startswith("Depth ")


def test_clip_facing_you_turns_with_the_view_and_stays_upright(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    # The plane keeps the half away from the viewer: its normal points away from the camera.
    assert _face_normal_after(w, "front") == pytest.approx((0, 1, 0), abs=1e-6)   # camera at -Y
    assert _face_normal_after(w, "right") == pytest.approx((-1, 0, 0), abs=1e-6)  # camera at +X
    n = _face_normal_after(w, "iso")
    assert n[2] == pytest.approx(0) and (n[0] ** 2 + n[1] ** 2) == pytest.approx(1)
    # Straight from above the screen's up stands in for the view direction.
    n = _face_normal_after(w, "top")
    assert n[2] == pytest.approx(0) and (n[0] ** 2 + n[1] ** 2) == pytest.approx(1)


def test_clip_facing_you_goes_through_the_centre_of_the_view(window):
    """Moving (panning) the view moves the model across the cut."""
    import numpy as np
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.scene.set_view("front", render=False)
    cam = w.plotter.camera
    cam.focal_point = tuple(np.array(cam.focal_point) + (25.0, 7.0, 0.0))
    cam.position = tuple(np.array(cam.position) + (25.0, 7.0, 0.0))
    w.scene._update_face_plane()
    origin = np.array(w.scene._face_plane.GetOrigin())
    assert origin[:2] == pytest.approx(np.array(cam.focal_point)[:2])
    w.face_slider.setValue(int(w.CLIP_STEPS * 0.75))         # further away: along +Y here
    w.scene._update_face_plane()
    d = w.scene.clip_face
    assert d > 0
    assert w.scene._face_plane.GetOrigin()[1] == pytest.approx(cam.focal_point[1] + d)


def test_both_cuts_at_the_same_time(window):
    """#70 (covrig): Clip from the top and Clip facing you together, a slider each."""
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_slider.setValue(250)                               # 10 mm
    w.act_clip_face.trigger()                                 # the other cut joins in
    assert w.act_clip.isChecked() and w.act_clip_face.isChecked()
    assert w.scene.clip_z == pytest.approx(10.0)              # the height cut stays where it was
    assert w.scene.clip_face == pytest.approx(0.0)            # the new one starts in the middle
    assert _planes(w) == [2, 2, 2]                            # keeps what both keep
    assert w.clip_top_row.isVisible() and w.clip_face_row.isVisible()
    assert any('pass the model through the cut' in t for t in w.hints.texts)
    assert "10" in w.clip_info.text() and "Depth" in w.face_info.text()
    w.face_slider.setValue(750)                               # each slider moves its own cut
    assert w.scene.clip_z == pytest.approx(10.0) and w.scene.clip_face > 0
    w.clip_slider.setValue(500)
    assert w.scene.clip_z == pytest.approx(20.0) and w.scene.clip_face > 0
    w.act_clip.trigger()                                      # C: only the height cut goes off
    assert not w.act_clip.isChecked() and w.act_clip_face.isChecked()
    assert w.scene.clip_z is None and w.scene.clip_face is not None and _planes(w) == [1, 1, 1]
    assert w.clip_box.isVisible()
    assert not w.clip_top_row.isVisible() and w.clip_face_row.isVisible()
    w.act_clip.trigger()                                      # and back, from the middle
    assert w.scene.clip_z == pytest.approx(20.0) and _planes(w) == [2, 2, 2]
    w.act_clip_face.trigger()                                 # V: only the upright cut goes off
    assert w.scene.clip_face is None and w.scene.clip_z is not None and _planes(w) == [1, 1, 1]
    assert w.scene.model_actors[0].GetMapper().GetClippingPlanes().GetItem(0) is w.scene._top_plane
    assert not any('pass the model through the cut' in t for t in w.hints.texts)


def test_turn_off_and_reset_view_end_both_cuts(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.act_clip_face.trigger()
    w.act_clip.setChecked(False)
    w.act_clip_face.setChecked(False)
    assert not w.act_clip.isChecked() and not w.act_clip_face.isChecked()
    assert w.clip_box.isHidden() and _planes(w) == [0, 0, 0]
    w.act_clip.trigger()
    w.act_clip_face.trigger()
    w.reset_view()
    assert not w.act_clip.isChecked() and not w.act_clip_face.isChecked()
    assert w.scene.clip_z is None and w.scene.clip_face is None and _planes(w) == [0, 0, 0]


def test_both_cuts_and_the_freeze_go_when_another_file_opens(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.act_clip_face.trigger()
    w.view_freeze_cb.setChecked(True)
    w.load_sync(CUBE)
    assert not w.act_clip.isChecked() and not w.act_clip_face.isChecked() and not w.view_freeze_cb.isChecked()
    assert w.scene.clip_z is None and w.scene.clip_face is None and _planes(w) == [0]
    assert w.clip_box.isHidden()


def test_clip_facing_you_turn_off(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.act_clip.setChecked(False)
    w.act_clip_face.setChecked(False)
    assert not w.act_clip_face.isChecked() and w.clip_box.isHidden()
    assert w.scene.clip_face is None and _planes(w) == [0, 0, 0]
    w.act_clip_face.trigger()
    w.act_clip_face.trigger()                                 # V twice: off again
    assert w.scene.clip_face is None and _planes(w) == [0, 0, 0]


def test_clip_facing_you_goes_when_another_file_opens(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.load_sync(INSIDE)                                  # even the same file again
    assert not w.act_clip_face.isChecked() and w.scene.clip_face is None and _planes(w) == [0, 0, 0]


# ---------------------------------------------------------------- Reset view (#66)

def test_reset_view_turns_everything_off_and_fits(window, monkeypatch):
    w = window
    w.load_sync(INSIDE)
    for a in (w.act_wireframe, w.act_xray, w.act_clip):
        a.trigger()
    fitted = []
    monkeypatch.setattr(w, "set_view", lambda view, animate=False: fitted.append(view))
    assert w.act_reset_view.isEnabled()
    w.act_reset_view.trigger()
    assert not any(a.isChecked() for a in (w.act_wireframe, w.act_xray, w.act_clip, w.act_clip_face))
    assert w.clip_box.isHidden() and _planes(w) == [0, 0, 0]
    p = _props(w)[0]
    assert p.GetRepresentation() == 2 and p.GetOpacity() == 1.0          # surface, solid
    assert fitted == [None]                                              # like Fit


def test_reset_view_also_ends_clip_facing_you(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.reset_view()
    assert not w.act_clip_face.isChecked() and w.scene.clip_face is None


def test_reset_view_key_and_shortcut_list(window, app):
    from printview3d.ui.settings_dialog import shortcut_rows
    assert window.act_reset_view.shortcut().toString() == "R"
    assert "R" in [k for row, _ in shortcut_rows() for k in row]


def test_reset_view_off_for_gcode(window):
    w = window
    w.load_sync(GCODE)
    assert not w.act_reset_view.isEnabled()
    w.reset_view()                                                      # harmless anyway


# ---------------------------------------------------------------- freeze the cutting plane

def test_freezing_the_cut_keeps_it_while_the_view_turns(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.view_freeze_cb.setChecked(True)
    before = np.array(_face_normal_after(w, "front")), np.array(w.scene._face_plane.GetOrigin())
    after = np.array(_face_normal_after(w, "right")), np.array(w.scene._face_plane.GetOrigin())
    assert np.allclose(before[0], after[0]) and np.allclose(before[1], after[1])       # did not turn
    w.view_freeze_cb.setChecked(False)
    free = np.array(_face_normal_after(w, "right"))
    assert not np.allclose(free, before[0])                                            # follows again


def test_a_frozen_cut_still_follows_its_slider(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.view_freeze_cb.setChecked(True)
    n = np.array(w.scene._face_plane.GetNormal())
    o0 = np.array(w.scene._face_plane.GetOrigin()) @ n
    w.face_slider.setValue(w.CLIP_STEPS)
    assert np.array(w.scene._face_plane.GetOrigin()) @ n > o0 + 1.0


def test_freeze_waits_for_the_cut_and_reset_view_clears_it(window):
    w = window
    w.load_sync(INSIDE)
    w.view_freeze_cb.setChecked(True)                        # no cut yet: nothing to freeze
    w.scene.set_view("front", render=False)
    w.act_clip_face.trigger()                                # freezes at the view it starts in
    n0 = np.array(w.scene._face_plane.GetNormal())
    assert np.allclose(_face_normal_after(w, "right"), n0)
    w.reset_view()
    assert not w.view_freeze_cb.isChecked() and w.scene.freeze_face is False


# ---------------------------------------------------------------- toolbar
def test_fit_has_an_icon_and_comes_after_measure(window):
    w = window
    tb = w.view_btn.parentWidget()
    fit = tb.widgetForAction(w.act_fit)
    order = [tb.widgetForAction(a) for a in tb.actions()]
    order = [o for o in order if o is not None]
    assert order.index(fit) == order.index(w.measure_btn) + 1
    assert order.index(w.view_btn) < order.index(w.measure_btn)
    assert not w.act_fit.icon().isNull() and w.act_fit.shortcut().toString() in ("", "F")
    assert w.act_fit in [a for a, _, v in w.view_actions if v is None]


def test_view_buttons_are_as_tall_as_the_other_toolbar_buttons(window, app):
    from printview3d.ui import theme
    theme.apply_theme(app, "dark")
    w = window
    w.set_view_cube_visible(False)                        # Iso, Top, Front, Right too
    app.processEvents()
    tb = w.view_btn.parentWidget()
    heights = {}
    for a in tb.actions():
        b = tb.widgetForAction(a)
        if b is not None and b.isVisible() and b.objectName() in ("viewButton", "exportButton", "slicerButton", "iconButton"):
            heights[b.objectName() + ":" + (getattr(b, "text", lambda: "")() or "?")] = b.sizeHint().height()
    assert len(set(heights.values())) == 1, heights


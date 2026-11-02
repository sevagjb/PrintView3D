"""View menu: wireframe, X-ray, clip from the top and clip facing you for models (issue #60)."""

import os

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


def test_menu_and_shortcuts(window):
    w = window
    assert w.view_btn.menu() is w.view_menu
    actions = [w.act_wireframe, w.act_xray, w.act_clip, w.act_clip_face]
    assert [a for a in w.view_menu.actions() if not a.isSeparator()] == actions
    assert [a.shortcut().toString() for a in actions] == ["W", "X", "C", "V"]
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
    plane = w.scene._clip_plane
    assert plane.GetOrigin()[2] == pytest.approx(10.0)
    assert plane.GetNormal() == pytest.approx((0, 0, -1))           # keeps what is below

    w.clip_slider.setValue(w.CLIP_STEPS)                             # all the way up: no cut
    assert w.scene.clip_z is None and _planes(w) == [0, 0, 0]


def test_clip_turn_off_button_and_shortcut(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_off_btn.click()
    assert not w.act_clip.isChecked() and w.clip_box.isHidden()
    assert w.scene.clip_z is None and _planes(w) == [0, 0, 0]
    assert all(a.GetBackfaceProperty() is None for a in w.scene.model_actors)


def test_options_stay_on_for_the_next_model_but_not_for_gcode(window):
    w = window
    w.load_sync(INSIDE)
    w.act_xray.trigger()
    w.act_clip.trigger()
    w.clip_slider.setValue(250)
    w.load_sync(GCODE)
    assert w.clip_box.isHidden()
    a = w.scene.p.actors.get("gcode")
    assert a is None or a.GetMapper().GetNumberOfClippingPlanes() == 0   # toolpaths untouched
    w.load_sync(CUBE)                                                    # 20 mm cube
    assert w.clip_box.isVisible()
    assert all(p.GetOpacity() < 1 for p in _props(w))
    assert w.scene.clip_z == pytest.approx(5.0)                          # same slider place, its height
    assert _planes(w) == [1]


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
    return w.scene._clip_plane.GetNormal()


def test_clip_facing_you_starts_through_the_centre_and_follows_the_slider(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    assert w.clip_box.isVisible() and w.clip_hint.isVisible()
    assert w.clip_box.title() == "Clip facing you"
    assert w.scene.clip_face == pytest.approx(0.0) and w.scene.clip_z is None
    assert _planes(w) == [1, 1, 1]
    assert all(a.GetBackfaceProperty() is not None for a in w.scene.model_actors)
    reach = w.scene.model_face_reach()
    w.clip_slider.setValue(w.CLIP_STEPS)                     # all the way: further away
    assert w.scene.clip_face == pytest.approx(reach)
    w.clip_slider.setValue(0)                                # nearer
    assert w.scene.clip_face == pytest.approx(-reach)
    assert "−" in w.clip_info.text()


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
    origin = np.array(w.scene._clip_plane.GetOrigin())
    assert origin[:2] == pytest.approx(np.array(cam.focal_point)[:2])
    w.clip_slider.setValue(int(w.CLIP_STEPS * 0.75))         # further away: along +Y here
    w.scene._update_face_plane()
    d = w.scene.clip_face
    assert d > 0
    assert w.scene._clip_plane.GetOrigin()[1] == pytest.approx(cam.focal_point[1] + d)


def test_one_cut_at_a_time(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_slider.setValue(100)
    w.act_clip_face.trigger()                                 # the other cut: top goes off
    assert w.act_clip_face.isChecked() and not w.act_clip.isChecked()
    assert w.scene.clip_z is None and w.scene.clip_face == pytest.approx(0.0)
    assert w.clip_slider.value() == w.CLIP_STEPS // 2         # starts in the middle
    assert w.clip_box.isVisible() and _planes(w) == [1, 1, 1]
    w.act_clip.trigger()                                      # and back
    assert w.act_clip.isChecked() and not w.act_clip_face.isChecked()
    assert w.scene.clip_face is None and w.scene.clip_z == pytest.approx(20.0)
    assert w.scene._clip_plane.GetNormal() == pytest.approx((0, 0, -1))
    assert w.clip_box.title() == "Clip from the top" and not w.clip_hint.isVisible()


def test_clip_facing_you_turn_off(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.clip_off_btn.click()
    assert not w.act_clip_face.isChecked() and w.clip_box.isHidden()
    assert w.scene.clip_face is None and _planes(w) == [0, 0, 0]
    w.act_clip_face.trigger()
    w.act_clip_face.trigger()                                 # V twice: off again
    assert w.scene.clip_face is None and _planes(w) == [0, 0, 0]


def test_clip_facing_you_stays_on_for_the_next_model(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.load_sync(GCODE)
    assert w.clip_box.isHidden()
    w.load_sync(CUBE)
    assert w.clip_box.isVisible() and w.clip_box.title() == "Clip facing you"
    assert w.scene.clip_face is not None and _planes(w) == [1]

"""View menu: wireframe, X-ray and clip from the top for models (issue #60)."""

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
    assert [a for a in w.view_menu.actions() if not a.isSeparator()] == [w.act_wireframe, w.act_xray, w.act_clip]
    assert [a.shortcut().toString() for a in (w.act_wireframe, w.act_xray, w.act_clip)] == ["W", "X", "C"]
    for a in (w.act_wireframe, w.act_xray, w.act_clip):
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
    for k in ("W", "X", "C"):
        assert k in keys


def test_arabic_keeps_the_slider_left_to_right(window, app):
    from PySide6.QtCore import Qt
    assert window.clip_slider.layoutDirection() == Qt.LeftToRight

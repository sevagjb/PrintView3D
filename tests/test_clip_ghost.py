"""View -> Clip: the cut-away part as a see-through ghost, and the cutting plane (issue #66)."""

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


def _window(app, path):
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(path))
    w.resize(1200, 760)
    w.show()
    return w


@pytest.fixture
def window(app, tmp_path):
    from PySide6.QtCore import QEvent
    w = _window(app, str(tmp_path / "settings.json"))
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _ghosts_visible(w):
    w.scene._sync_ghosts()
    return [bool(g.GetVisibility()) for g, _ in w.scene._ghosts]


def _plane_visible(w):
    return [bool(a.GetVisibility()) for a in w.scene._cut_plane_actors]


def test_no_ghost_without_a_cut(window):
    w = window
    w.load_sync(INSIDE)
    assert w.scene._ghosts == []                     # made only when a cut needs them
    assert "ghost_0" not in w.scene.p.actors


def test_clip_from_the_top_shows_the_cut_away_part(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    assert w.clip_ghost_cb.isVisible() and w.clip_ghost_cb.isChecked()   # on by default
    assert len(w.scene._ghosts) == 3
    assert _ghosts_visible(w) == [True, True, True]
    assert _plane_visible(w) == [True, True]
    # The ghost keeps the other half: the same place, the opposite side.
    cut, ghost = w.scene._clip_plane, w.scene._ghost_plane
    assert ghost.GetNormal() == pytest.approx(tuple(-v for v in cut.GetNormal()))
    assert ghost.GetOrigin() == pytest.approx(cut.GetOrigin())
    for g, outline in w.scene._ghosts:
        assert g.GetMapper().GetNumberOfClippingPlanes() == 1
        assert g.GetProperty().GetOpacity() < 0.5                       # see-through
        assert not g.GetPickable()                                      # a click goes to the model
        assert outline is not None and outline.GetMapper().GetNumberOfClippingPlanes() == 1


def test_the_plane_lies_in_the_cut_and_is_as_big_as_the_model(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_slider.setValue(250)                                         # 10 mm
    pts = np.asarray(w.scene._cut_plane.points)
    assert pts[:, 2] == pytest.approx([10.0] * 4)
    b = w.scene.focus_bounds
    assert pts[:, 0].min() < b[0] and pts[:, 0].max() > b[1]            # a bit bigger than the model
    assert pts[:, 0].max() - pts[:, 0].min() < 1.3 * (b[1] - b[0])     # ... but not the whole view


def test_ghosts_do_not_change_fit_or_bounds(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    for g, outline in w.scene._ghosts:
        assert not g.GetUseBounds()
    assert all(not a.GetUseBounds() for a in w.scene._cut_plane_actors)


def test_checkbox_turns_it_off_and_is_remembered(app, tmp_path):
    from PySide6.QtCore import QEvent
    path = str(tmp_path / "settings.json")
    w = _window(app, path)
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_ghost_cb.setChecked(False)
    assert _ghosts_visible(w) == [False, False, False]
    assert _plane_visible(w) == [False, False]
    assert w.scene._clip_plane is not None and w.scene.clip_z is not None   # the cut itself stays
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()

    w2 = _window(app, path)
    assert not w2.clip_ghost_cb.isChecked() and not w2.scene.show_ghost
    w2.load_sync(INSIDE)
    w2.act_clip.trigger()
    assert w2.scene._ghosts == [] or _ghosts_visible(w2) == [False, False, False]
    w2.clip_ghost_cb.setChecked(True)
    assert _ghosts_visible(w2) == [True, True, True]
    w2.close()


def test_turning_the_cut_off_hides_the_ghost(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_slider.setValue(w.CLIP_STEPS)                                # all the way up: no cut
    assert _ghosts_visible(w) == [False, False, False]
    w.clip_slider.setValue(500)
    w.clip_off_btn.click()
    assert _ghosts_visible(w) == [False, False, False]
    assert _plane_visible(w) == [False, False]


def test_a_hidden_object_has_no_ghost(window):
    from PySide6.QtWidgets import QCheckBox
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.objects_box.findChildren(QCheckBox)[2].setChecked(False)          # the tube
    assert _ghosts_visible(w) == [True, True, False]


def test_clip_facing_you_ghost_and_upright_plane(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip_face.trigger()
    w.scene.set_view("front", render=False)
    w.scene._update_face_plane()                                        # before every frame
    cut, ghost = w.scene._clip_plane, w.scene._ghost_plane
    assert ghost.GetNormal() == pytest.approx(tuple(-v for v in cut.GetNormal()))
    pts = np.asarray(w.scene._cut_plane.points)
    n = np.array(cut.GetNormal())
    o = np.array(cut.GetOrigin())
    assert (pts - o) @ n == pytest.approx([0.0] * 4, abs=1e-6)          # in the cut
    assert np.ptp(pts[:, 2]) > 40                                       # upright, model-high
    assert _ghosts_visible(w) == [True, True, True]


def test_new_file_replaces_the_ghosts(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.load_sync(CUBE)                                                   # the cut stays on (#60)
    assert len(w.scene._ghosts) == 1
    assert "ghost_2" not in w.scene.p.actors
    w.load_sync(GCODE)
    assert w.scene._ghosts == []


def test_theme_colours(window, app):
    from printview3d.ui import theme
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    for name, light in (("ember", True), ("ember_dark", False)):
        theme.apply_theme(app, name)
        w.scene.set_colors(theme.colors())
        g, outline = w.scene._ghosts[0]
        assert g.GetProperty().GetColor() == pytest.approx((1.0, 1.0, 1.0))     # white on both
        edge = outline.GetProperty().GetColor()
        assert (sum(edge) / 3 < 0.5) == light           # dark outline on light themes, light on dark
        sheet = w.scene._cut_plane_actors[0].GetProperty()
        teal = theme.colors()["accent_ink"].lstrip("#")
        assert sheet.GetColor() == pytest.approx(tuple(int(teal[i:i + 2], 16) / 255 for i in (0, 2, 4)))


def test_ghosts_are_plain_colours_without_a_colour_bar(window):
    """The outline came out coloured by the edge extraction's point ids, with a colour bar."""
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    for g, outline in w.scene._ghosts:
        assert not g.GetMapper().GetScalarVisibility()
        assert not outline.GetMapper().GetScalarVisibility()
    assert all(not a.GetMapper().GetScalarVisibility() for a in w.scene._cut_plane_actors)
    assert not w.scene.p.scalar_bars

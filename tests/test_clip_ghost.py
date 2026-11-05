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


def _ghosts_visible(w, cut="top"):
    w.scene._sync_ghosts()
    return [bool(g.GetVisibility()) for g, _ in w.scene._ghosts[cut]]


def _sheet_actors(w, cut="top"):
    return w.scene._sheets[cut][1] if cut in w.scene._sheets else []


def _plane_visible(w, cut="top"):
    return [bool(a.GetVisibility()) for a in _sheet_actors(w, cut)]


def _sheet_points(w, cut="top"):
    return np.asarray(w.scene._sheets[cut][0].points)


def test_no_ghost_without_a_cut(window):
    w = window
    w.load_sync(INSIDE)
    assert w.scene._ghosts == {"top": [], "face": []}   # made only when a cut needs them
    assert "ghost_top_0" not in w.scene.p.actors


def test_clip_from_the_top_shows_the_cut_away_part(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    assert w.clip_ghost_cb.isVisible() and w.clip_ghost_cb.isChecked()   # on by default
    assert len(w.scene._ghosts["top"]) == 3 and w.scene._ghosts["face"] == []
    assert _ghosts_visible(w) == [True, True, True]
    assert _plane_visible(w) == [True, True]
    # The ghost keeps the other half: the same place, the opposite side.
    cut, ghost = w.scene._top_plane, w.scene._ghost_top_plane
    assert ghost.GetNormal() == pytest.approx(tuple(-v for v in cut.GetNormal()))
    assert ghost.GetOrigin() == pytest.approx(cut.GetOrigin())
    for g, outline in w.scene._ghosts["top"]:
        assert g.GetMapper().GetNumberOfClippingPlanes() == 1
        assert g.GetProperty().GetOpacity() < 0.5                       # see-through
        assert not g.GetPickable()                                      # a click goes to the model
        assert outline is not None and outline.GetMapper().GetNumberOfClippingPlanes() == 1


def test_the_plane_lies_in_the_cut_and_is_as_big_as_the_model(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_slider.setValue(250)                                         # 10 mm
    pts = _sheet_points(w)
    assert pts[:, 2] == pytest.approx([10.0] * 4)
    b = w.scene.focus_bounds
    assert pts[:, 0].min() < b[0] and pts[:, 0].max() > b[1]            # a bit bigger than the model
    assert pts[:, 0].max() - pts[:, 0].min() < 1.3 * (b[1] - b[0])     # ... but not the whole view


def test_ghosts_do_not_change_fit_or_bounds(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    for g, outline in w.scene._ghosts["top"]:
        assert not g.GetUseBounds()
    assert all(not a.GetUseBounds() for a in _sheet_actors(w))


def test_checkbox_turns_it_off_and_is_remembered(app, tmp_path):
    from PySide6.QtCore import QEvent
    path = str(tmp_path / "settings.json")
    w = _window(app, path)
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.clip_ghost_cb.setChecked(False)
    assert _ghosts_visible(w) == [False, False, False]
    assert _plane_visible(w) == [True, True]                            # the plane has its own box
    assert w.scene.clip_z is not None   # the cut itself stays
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()

    w2 = _window(app, path)
    assert not w2.clip_ghost_cb.isChecked() and not w2.scene.show_ghost
    w2.load_sync(INSIDE)
    w2.act_clip.trigger()
    assert w2.scene._ghosts["top"] == [] or _ghosts_visible(w2) == [False, False, False]
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
    w.act_clip.setChecked(False)
    w.act_clip_face.setChecked(False)
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
    cut, ghost = w.scene._face_plane, w.scene._ghost_face_plane
    assert ghost.GetNormal() == pytest.approx(tuple(-v for v in cut.GetNormal()))
    pts = _sheet_points(w, "face")
    n = np.array(cut.GetNormal())
    o = np.array(cut.GetOrigin())
    assert (pts - o) @ n == pytest.approx([0.0] * 4, abs=1e-6)          # in the cut
    assert np.ptp(pts[:, 2]) > 40                                       # upright, model-high
    assert _ghosts_visible(w, "face") == [True, True, True]
    assert w.scene._ghosts["top"] == []                                 # the other cut's: not made


def test_new_file_replaces_the_ghosts(window):
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    w.load_sync(CUBE)                                                   # another file: the cut goes
    assert not w.act_clip.isChecked() and not any(n.startswith("ghost_") for n in w.scene.p.actors)
    w.act_clip.trigger()                                                # on again: ghosts of the new model
    assert len(w.scene._ghosts["top"]) == 1
    assert "ghost_top_2" not in w.scene.p.actors
    w.load_sync(GCODE)
    assert w.scene._ghosts == {"top": [], "face": []}


def test_theme_colours(window, app):
    from printview3d.ui import theme
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    for name, light in (("ember", True), ("ember_dark", False)):
        theme.apply_theme(app, name)
        w.scene.set_colors(theme.colors())
        g, outline = w.scene._ghosts["top"][0]
        assert g.GetProperty().GetColor() == pytest.approx((1.0, 1.0, 1.0))     # white on both
        edge = outline.GetProperty().GetColor()
        assert (sum(edge) / 3 < 0.5) == light           # dark outline on light themes, light on dark
        sheet = _sheet_actors(w)[0].GetProperty()
        teal = theme.colors()["accent_ink"].lstrip("#")
        assert sheet.GetColor() == pytest.approx(tuple(int(teal[i:i + 2], 16) / 255 for i in (0, 2, 4)))


def test_ghosts_are_plain_colours_without_a_colour_bar(window):
    """The outline came out coloured by the edge extraction's point ids, with a colour bar."""
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    for g, outline in w.scene._ghosts["top"]:
        assert not g.GetMapper().GetScalarVisibility()
        assert not outline.GetMapper().GetScalarVisibility()
    assert all(not a.GetMapper().GetScalarVisibility() for a in _sheet_actors(w))
    assert not w.scene.p.scalar_bars


def test_plane_and_ghost_each_have_their_own_checkbox(app, tmp_path):
    """covrig's suggestion on #66: the plane and the ghost turn on and off separately."""
    from PySide6.QtCore import QEvent
    path = str(tmp_path / "settings.json")
    w = _window(app, path)
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    assert w.clip_plane_cb.isVisible() and w.clip_plane_cb.isChecked()
    w.clip_plane_cb.setChecked(False)
    assert _plane_visible(w) == [False, False]
    assert _ghosts_visible(w) == [True, True, True]
    w.clip_ghost_cb.setChecked(False)
    w.clip_plane_cb.setChecked(True)
    assert _plane_visible(w) == [True, True] and _ghosts_visible(w) == [False, False, False]
    w.clip_plane_cb.setChecked(False)
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()
    w2 = _window(app, path)                                             # both remembered
    assert not w2.clip_plane_cb.isChecked() and not w2.clip_ghost_cb.isChecked()
    w2.load_sync(INSIDE)
    w2.act_clip.trigger()
    assert _sheet_actors(w2) == [] or _plane_visible(w2) == [False, False]
    w2.close()


def test_plane_alone_without_any_ghosts(window):
    w = window
    w.clip_ghost_cb.setChecked(False)
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    assert w.scene._ghosts == {"top": [], "face": []}                   # never made
    assert _plane_visible(w) == [True, True]


def test_strength_makes_everything_fainter_or_stronger_together():
    from printview3d.ui.scene import ghost_factor
    assert ghost_factor(50) == pytest.approx(1.0)
    assert ghost_factor(0) == pytest.approx(0.25)
    assert ghost_factor(100) == pytest.approx(4.0)
    assert ghost_factor("bad") == pytest.approx(1.0)
    assert ghost_factor(25) < ghost_factor(50) < ghost_factor(75)


def test_default_is_a_bit_fainter_than_the_first_try(window, app):
    from printview3d.ui import scene as sc
    assert sc.GHOST_OPACITY["dark"] < 0.30 and sc.GHOST_OPACITY["light"] < 0.35
    assert sc.CUT_PLANE_OPACITY < 0.16


def test_strength_setting(window):
    from printview3d.ui.scene import CUT_PLANE_OPACITY, GHOST_OPACITY
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    mode = w.scene._ghost_mode()
    g = w.scene._ghosts["top"][0][0].GetProperty()
    sheet = _sheet_actors(w)[0].GetProperty()
    assert g.GetOpacity() == pytest.approx(GHOST_OPACITY[mode])
    w.set_ghost_strength(0)
    assert g.GetOpacity() == pytest.approx(GHOST_OPACITY[mode] / 4)
    assert sheet.GetOpacity() == pytest.approx(CUT_PLANE_OPACITY)       # the plane has its own
    w.set_ghost_strength(100)
    assert g.GetOpacity() == pytest.approx(min(1.0, GHOST_OPACITY[mode] * 4))
    w.set_plane_strength(100)
    assert sheet.GetOpacity() == pytest.approx(CUT_PLANE_OPACITY * 4)
    assert g.GetOpacity() == pytest.approx(min(1.0, GHOST_OPACITY[mode] * 4))   # ghost unchanged
    w.set_plane_strength(0)
    assert sheet.GetOpacity() == pytest.approx(CUT_PLANE_OPACITY / 4)


def test_settings_slider_is_live_and_cancel_puts_it_back(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    w = window
    w.load_sync(INSIDE)
    w.act_clip.trigger()
    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    assert dlg.ghost_slider.value() == 50
    dlg.ghost_slider.setValue(10)
    assert w.scene.ghost_strength == 10                                 # seen while dragging
    dlg.reject()
    assert w.scene.ghost_strength == 50 and w.settings.get("ghost_strength") == 50

    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    dlg.plane_slider.setValue(80)
    assert w.scene.plane_strength == 80 and w.scene.ghost_strength == 50
    dlg.reject()
    assert w.scene.plane_strength == 50

    dlg = SettingsDialog(w.settings, w, {}, page="viewer")
    dlg.ghost_slider.setValue(20)
    dlg.plane_slider.setValue(70)
    dlg._save()                                                         # OK
    assert w.settings.get("ghost_strength") == 20 and w.scene.ghost_strength == 20
    assert w.settings.get("plane_strength") == 70 and w.scene.plane_strength == 70


# ------------------------------------------------------------ both cuts together (#70)

def _keeps(planes, p):
    """Does a point pass all these clipping planes (what VTK keeps)?"""
    return all(np.dot(np.array(p) - np.array(pl.GetOrigin()), pl.GetNormal()) >= 0 for pl in planes)


def _clip_planes(actor):
    c = actor.GetMapper().GetClippingPlanes()
    return [c.GetItem(i) for i in range(c.GetNumberOfItems())] if c is not None else []


def _both_cuts(w):
    w.load_sync(INSIDE)
    w.act_clip.trigger()                                                # 20 mm
    w.act_clip_face.trigger()
    w.scene.set_view("front", render=False)                             # camera at -Y
    w.scene._update_face_plane()
    w.scene.apply_view_options()


def test_both_cuts_ghost_is_even_never_drawn_twice(window):
    """covrig on #70: the ghost looks the same with one cut or two. The two ghost pieces split
    what is hidden between them and never cover the same spot."""
    w = window
    _both_cuts(w)
    assert _ghosts_visible(w, "top") == [True] * 3 and _ghosts_visible(w, "face") == [True] * 3
    top_g = w.scene._ghosts["top"][0][0]
    face_g, face_edges = w.scene._ghosts["face"][0]
    assert len(_clip_planes(top_g)) == 1 and len(_clip_planes(face_g)) == 2
    assert len(_clip_planes(face_edges)) == 2                           # the outline too
    model = _clip_planes(w.scene.model_actors[0])
    assert len(model) == 2
    rng = np.random.default_rng(1)
    pts = rng.uniform((-10, -10, -5), (40, 40, 45), size=(2000, 3))
    for p in pts:
        shown = _keeps(model, p)
        in_top, in_face = _keeps(_clip_planes(top_g), p), _keeps(_clip_planes(face_g), p)
        assert not (in_top and in_face)                                 # no spot twice
        assert shown or in_top or in_face                               # every hidden spot once
    # Both ghost pieces look exactly the same.
    assert top_g.GetProperty().GetOpacity() == pytest.approx(face_g.GetProperty().GetOpacity())


def test_both_cuts_sheets_meet_in_a_corner(window):
    """Each cutting plane stops where the other cut is, instead of reaching into the cut-away part."""
    w = window
    _both_cuts(w)
    assert _plane_visible(w, "top") == [True, True] and _plane_visible(w, "face") == [True, True]
    for a in _sheet_actors(w, "top"):
        assert _clip_planes(a) == [w.scene._face_plane]
    for a in _sheet_actors(w, "face"):
        assert _clip_planes(a) == [w.scene._top_plane]
    w.act_clip.trigger()                                                # the height cut off
    assert _plane_visible(w, "top") == [False, False]
    assert all(_clip_planes(a) == [] for a in _sheet_actors(w, "face"))  # full height again
    assert all(len(_clip_planes(g)) == 1 for g, _ in w.scene._ghosts["face"])
    assert _ghosts_visible(w, "top") == [False] * 3


def test_both_cuts_one_ghost_checkbox_and_one_plane_checkbox(window):
    w = window
    _both_cuts(w)
    w.clip_ghost_cb.setChecked(False)
    assert _ghosts_visible(w, "top") == [False] * 3 and _ghosts_visible(w, "face") == [False] * 3
    w.clip_plane_cb.setChecked(False)
    assert _plane_visible(w, "top") == [False, False] and _plane_visible(w, "face") == [False, False]

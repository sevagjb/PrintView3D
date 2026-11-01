"""The view cube: what is under the mouse, its colours in every theme, and clicks on its faces."""

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from printview3d.ui import theme  # noqa: E402
from printview3d.ui.view_cube import FACES, cube_colors, face_image, ray_hit  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("origin,direction,expected", [
    ((0, -5, 0), (0, 1, 0), "front"),
    ((0, 5, 0), (0, -1, 0), "back"),
    ((5, 0, 0), (-1, 0, 0), "right"),
    ((-5, 0, 0), (1, 0, 0), "left"),
    ((0, 0, 5), (0, 0, -1), "top"),
    ((0, 0, -5), (0, 0, 1), "bottom"),
    ((0.86, 0, 5), (0, 0, -1), "ring"),            # from above, beside the cube: the ring
    ((0, 0, 5), (1, 0, 0), None),                  # passes over everything
    ((3, 3, 5), (0, 0, -1), None),                 # far outside the ring
])
def test_ray_hit(origin, direction, expected):
    d = np.array(direction, float)
    assert ray_hit(np.array(origin, float), d / np.linalg.norm(d)) == expected


def test_iso_ray_hits_the_nearest_face():
    # From the front-right and slightly above, aimed just below the centre: the front face.
    o = np.array([0.0, -6.0, 0.0])
    d = np.array([0.0, 1.0, -0.02])
    assert ray_hit(o, d / np.linalg.norm(d)) == "front"


def test_faces_read_upright_from_their_view():
    # Every face's corners go bottom-left, bottom-right, top-right, top-left on its own plane.
    for name, corners in FACES.items():
        c = np.array(corners)
        normal = np.cross(c[1] - c[0], c[3] - c[0])
        assert np.allclose(np.abs(normal).max(), 1.0), name
        centre = c.mean(axis=0)
        assert np.dot(normal, centre) > 0, name           # points out of the cube


@pytest.mark.parametrize("name", list(theme.THEMES))
def test_cube_colours_in_every_theme(name):
    c = cube_colors(theme.THEMES[name])
    assert set(c) == {"face", "text", "edge", "hover", "hover_text"}
    for value in c.values():
        assert value.startswith("#") and len(value) == 7


def test_ember_light_cube_matches_the_teal_buttons():
    c = cube_colors(theme.THEMES["ember"])
    assert c["hover"] == theme.THEMES["ember"]["view_bg"] == "#14736a"
    assert c["hover_text"] == "#ffffff"


def test_face_picture(app):
    img = face_image("FRONT", "#ffffff", "#14736a", "#14736a")
    assert img.shape == (256, 256, 4) and img.dtype == np.uint8
    assert tuple(img[128, 2, :3]) == (0x14, 0x73, 0x6a)  # the edge
    assert tuple(img[30, 30, :3]) == (255, 255, 255)      # the face
    long = face_image("Vorderansicht" * 3, "#ffffff", "#000000", "#000000")
    assert long.shape == (256, 256, 4)                   # long labels shrink, never fail


def test_ember_light_view_buttons_are_teal(app):
    assert theme.filled_view_buttons("ember")
    for name in theme.THEMES:
        if name != "ember":
            assert not theme.filled_view_buttons(name), name


def _offscreen_cube(app):
    pv = pytest.importorskip("pyvista")
    from printview3d.ui.view_cube import ViewCube
    plotter = pv.Plotter(off_screen=True, window_size=(800, 600))
    plotter.add_mesh(pv.Cube(), reset_camera=True)
    cube = ViewCube(plotter, theme.THEMES["ember"], {})
    return plotter, cube


def test_click_in_the_corner_finds_the_face(app):
    plotter, cube = _offscreen_cube(app)
    try:
        plotter.camera_position = [(0, -10, 0), (0, 0, 0), (0, 0, 1)]   # front view
        plotter.render()
        x0, y0, x1, y1 = cube._corner()
        assert cube.hit((x0 + x1) / 2, (y0 + y1) / 2) == "front"
        assert cube.hit(10, 10) is None                                  # outside the corner
        plotter.camera_position = [(0, 0, 10), (0, 0, 0), (0, 1, 0)]    # top view
        plotter.render()
        assert cube.hit((x0 + x1) / 2, (y0 + y1) / 2) == "top"
        cube.set_visible(False)
        assert cube.hit((x0 + x1) / 2, (y0 + y1) / 2) is None           # hidden: never in the way
    finally:
        plotter.close()


def test_hover_and_labels(app):
    plotter, cube = _offscreen_cube(app)
    try:
        assert cube.set_hover("top") is True
        assert cube.set_hover("top") is False                  # no change, no redraw
        cube.set_labels({"top": "أعلى"})                        # any language
        cube.set_colors(theme.THEMES["dark"])
        assert cube.set_hover(None) is True
    finally:
        plotter.close()


def test_scene_has_the_cube_views(app):
    pv = pytest.importorskip("pyvista")
    from printview3d.ui.scene import Scene
    plotter = pv.Plotter(off_screen=True, window_size=(400, 300))
    try:
        scene = Scene(plotter)
        scene.focus_bounds = (0, 10, 0, 10, 0, 10)
        expected = {"back": (0, 1, 0), "left": (-1, 0, 0), "bottom": (0, 0, -1)}
        for view, direction in expected.items():
            scene.set_view(view)
            pos = np.array(plotter.camera.position) - np.array(plotter.camera.focal_point)
            assert np.allclose(pos / np.linalg.norm(pos), direction, atol=1e-6), view
    finally:
        plotter.close()


class _FakeIren:
    def __init__(self):
        self.pos = (0, 0)

    def GetEventPosition(self):
        return self.pos

    def GetShiftKey(self):
        return False

    def SetInteractorStyle(self, style):
        pass

    def Render(self):
        pass


class _FakeCube:
    """Everything right of x=700 is the cube's front face."""
    visible = True

    def hit(self, x, y):
        return "front" if x > 700 else None

    def set_hover(self, part):
        return False


def _controls(app):
    pv = pytest.importorskip("pyvista")
    from types import SimpleNamespace

    from printview3d.ui.camera_controls import TurntableControls
    plotter = pv.Plotter(off_screen=True, window_size=(800, 600))
    plotter.add_mesh(pv.Cube())
    iren = _FakeIren()
    fake = SimpleNamespace(iren=SimpleNamespace(interactor=iren), renderer=plotter.renderer)
    scene = SimpleNamespace(default_pivot=lambda: (0, 0, 0), pickable_actors=lambda: [])
    c = TurntableControls(fake, scene)
    c.cube = _FakeCube()
    views = []
    c.on_cube_view = views.append
    return plotter, c, iren, views


def test_click_on_a_cube_face_picks_the_view(app):
    plotter, c, iren, views = _controls(app)
    try:
        iren.pos = (750, 550)
        c._left_down()
        iren.pos = (751, 551)                  # a tiny wobble is still a click
        c._move()
        c._button_up()
        assert views == ["front"]
    finally:
        plotter.close()


def test_drag_on_the_cube_orbits_instead(app):
    plotter, c, iren, views = _controls(app)
    try:
        before = plotter.camera.position
        iren.pos = (750, 550)
        c._left_down()
        iren.pos = (790, 550)
        c._move()
        c._button_up()
        assert views == []
        assert not np.allclose(before, plotter.camera.position)
    finally:
        plotter.close()


def test_press_beside_the_cube_is_a_normal_orbit(app):
    plotter, c, iren, views = _controls(app)
    try:
        iren.pos = (100, 100)
        c._left_down()
        assert c.mode == "rotate"
        c._button_up()
        assert views == []
    finally:
        plotter.close()


# --- Top / Bottom view, then drag (the model used to disappear) ------------------------------

def _scene_with_model(app):
    pv = pytest.importorskip("pyvista")
    from types import SimpleNamespace

    from printview3d.ui.camera_controls import TurntableControls
    from printview3d.ui.scene import Scene
    plotter = pv.Plotter(off_screen=True, window_size=(400, 300))
    scene = Scene(plotter)
    plotter.add_mesh(pv.Cube(center=(5, 5, 5), x_length=10, y_length=10, z_length=10), color="#ff0000",
                     lighting=False)
    scene.focus_bounds = (0, 10, 0, 10, 0, 10)
    fake = SimpleNamespace(iren=SimpleNamespace(interactor=_FakeIren()), renderer=plotter.renderer)
    c = TurntableControls(fake, scene)
    c.pivot = np.array([5.0, 5.0, 5.0])
    return plotter, scene, c


def _camera_ok(plotter):
    cam = plotter.camera
    up = np.array(cam.up)
    fwd = np.array(cam.focal_point) - np.array(cam.position)
    fwd /= np.linalg.norm(fwd)
    assert np.all(np.isfinite(up)) and abs(np.linalg.norm(up) - 1) < 1e-6, up
    assert abs(np.dot(up, fwd)) < 1e-6                     # up is never along the viewing direction


def _model_visible(plotter) -> bool:
    plotter.render()
    img = plotter.screenshot(return_img=True)
    red = (img[..., 0] > 200) & (img[..., 1] < 60) & (img[..., 2] < 60)
    return red.sum() > 500


@pytest.mark.parametrize("view", ["top", "bottom"])
@pytest.mark.parametrize("dx,dy", [(20, 0), (-35, 0), (20, 6), (0, 10), (0, -10), (3, -40)])
def test_drag_from_top_and_bottom_keeps_the_model(app, view, dx, dy):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view(view)
        assert _model_visible(plotter)
        for _ in range(5):                                  # a drag is many small moves
            c._orbit(dx / 5, dy / 5)
            _camera_ok(plotter)
        assert _model_visible(plotter), (view, dx, dy)
    finally:
        plotter.close()


def test_ring_turn_in_top_view_spins_the_picture(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("top")
        before_pos, before_up = np.array(plotter.camera.position), np.array(plotter.camera.up)
        c._orbit(40, 0)                                    # ring: turn only
        assert np.allclose(before_pos, plotter.camera.position)   # still straight above
        assert not np.allclose(before_up, plotter.camera.up)      # but the picture turned
        _camera_ok(plotter)
    finally:
        plotter.close()


def test_drag_down_from_top_tilts_out_of_it(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("top")
        c._orbit(0, 30)
        fwd = np.array(plotter.camera.focal_point) - np.array(plotter.camera.position)
        assert fwd[2] / np.linalg.norm(fwd) > -0.999         # no longer straight down
        _camera_ok(plotter)
    finally:
        plotter.close()


def test_toolbar_hides_the_cube_views_while_the_cube_is_on(app, tmp_path, monkeypatch):
    """Top, Front and Right are on the cube; their buttons come back when it is switched off,
    and the keys 2/3/4 keep working either way."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from printview3d.settings import Settings
    from printview3d.ui.main_window import MainWindow
    win = MainWindow(Settings(str(tmp_path / "settings.json")))
    try:
        views = {view: act for act, _, view in win.view_actions}
        assert win.view_cube.visible
        assert views[None].isVisible() and views["iso"].isVisible() and win.act_bed.isVisible()
        assert not any(views[v].isVisible() for v in ("top", "front", "right"))
        fired = []
        views["front"].triggered.connect(lambda: fired.append("front"))
        views["front"].trigger()                       # what the "3" key does
        assert fired == ["front"]
        win.set_view_cube_visible(False)
        assert all(views[v].isVisible() for v in ("top", "front", "right"))
        win.set_view_cube_visible(True)
        assert not views["top"].isVisible()
    finally:
        win.close()
        win.deleteLater()

"""The view cube: what is under the mouse, its colours in every theme, and clicks on its faces."""

import os
import sys

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from printview3d.ui import theme  # noqa: E402
from printview3d.ui.camera_controls import azimuth_elevation, next_stop, view_frame  # noqa: E402
from printview3d.ui.view_cube import (ARROWS, FACES, arrow_triangle, contrast, control_at,  # noqa: E402
                                      cube_colors, face_image, ray_hit)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _need_3d_view():
    """Like the window tests in test_archive.py: without a screen, a VTK 3D view can't be made on
    macOS (the GitHub runner crashes). The macOS build has its own smoke test in the real app."""
    if sys.platform == "darwin":
        pytest.skip("the VTK 3D view cannot be created offscreen on macOS")


# Reading back the rendered picture needs real OpenGL. Linux has it in software (Mesa); the
# Windows CI machines have no graphics card and crash there ("access violation"). The camera
# checks that catch the bug run everywhere; the "is the model on screen" check only on Linux.
CAN_READ_PIXELS = sys.platform.startswith("linux")


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
    assert c["edge"] == theme.THEMES["ember"]["view_bg"] == "#14736a"


@pytest.mark.parametrize("name", list(theme.THEMES))
def test_hover_is_the_primary_colour_with_readable_text(name):
    """One rule for every theme: the part under the mouse in the theme's primary colour (amber in
    Ember, teal elsewhere), with white or dark text - whichever reads better (at least 4.5:1)."""
    t = theme.THEMES[name]
    c = cube_colors(t)
    assert c["hover"] == t["primary"]
    assert contrast(c["hover"], c["hover_text"]) >= 4.5, (name, c)


def test_ember_hover_is_amber():
    for name in ("ember", "ember_dark"):
        assert cube_colors(theme.THEMES[name])["hover"] == "#ef791b"


def test_see_through_face(app):
    img = face_image("TOP", "#ffffff", "#14736a", "#14736a", alpha=0.55)
    assert abs(int(img[60, 60, 3]) - 140) <= 2           # the face: 55 % see-through
    assert img[128, 2, 3] == 255                          # the border stays solid
    assert img[..., 3].max() == 255                       # and so does the text


def test_arrows_and_home_are_found():
    for name in ARROWS:
        tip, b1, b2 = arrow_triangle(name)
        cx, cy = (tip[0] + b1[0] + b2[0]) / 3, (tip[1] + b1[1] + b2[1]) / 3
        assert control_at(cx, cy) == name
    assert control_at(0.0875, 0.8375) == "home"
    assert control_at(0.5, 0.5) is None                   # the cube itself
    assert control_at(0.95, 0.05) is None                 # an empty corner
    # The arrows stay outside the cube: the up arrow is above the top of the square's middle.
    assert arrow_triangle("arrow_up")[0][1] > 0.95


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
    _need_3d_view()
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


def test_click_on_the_arrows_and_home(app):
    plotter, cube = _offscreen_cube(app)
    try:
        x0, y0, x1, y1 = cube._corner()
        at = lambda u, v: cube.hit(x0 + u * (x1 - x0), y0 + v * (y1 - y0))   # noqa: E731
        assert at(0.5, 0.955) == "arrow_up"
        assert at(0.5, 0.045) == "arrow_down"
        assert at(0.045, 0.5) == "arrow_left"
        assert at(0.955, 0.5) == "arrow_right"
        assert at(0.0875, 0.8375) == "home"
        assert cube.contains((x0 + x1) / 2, (y0 + y1) / 2)
        assert not cube.contains(10, 10)
    finally:
        plotter.close()


def test_arrows_show_only_while_the_mouse_is_over_the_cube(app):
    plotter, cube = _offscreen_cube(app)
    try:
        assert not cube.show_controls
        assert not cube.arrow_actors["arrow_up"].GetVisibility()
        assert cube.set_hover(None, True) is True               # mouse enters the square
        assert cube.arrow_actors["arrow_up"].GetVisibility() and cube.home_actor.GetVisibility()
        assert cube.set_hover("arrow_up", True) is True
        assert cube.set_hover(None, False) is True               # mouse leaves
        assert not cube.home_actor.GetVisibility()
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
    _need_3d_view()
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
    """Everything right of x=700 is the cube's front face; at y < 20 there its right arrow."""
    visible = True
    tooltips = {}

    def hit(self, x, y):
        if x > 700:
            return "arrow_right" if y < 20 else "front"
        return None

    def contains(self, x, y):
        return x > 700

    def set_hover(self, part, inside=None):
        return False


def _controls(app):
    _need_3d_view()
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
    _need_3d_view()
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
    if not CAN_READ_PIXELS:
        return True                                         # see CAN_READ_PIXELS
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
    _need_3d_view()
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


# --- Arrows: 45° stops, Home, smooth turns ---------------------------------------------------


@pytest.mark.parametrize("angle,direction,expected", [
    (0, 1, 45), (0, -1, -45), (10, 1, 45), (10, -1, 0), (44.99999, 1, 90),
    (-90, -1, -135), (-57, -1, -90), (-57, 1, -45), (90, 1, 135),
])
def test_next_stop(angle, direction, expected):
    assert next_stop(angle, direction) == pytest.approx(expected)


@pytest.mark.parametrize("az,el", [(-90, 0), (-45, 45), (30, -45), (180, 0), (-90, 90), (0, -90),
                                   (135, 90)])
def test_view_frame_round_trip(az, el):
    back, up = view_frame(az, el)
    assert abs(np.dot(back, up)) < 1e-9
    a, e = azimuth_elevation(back, up)
    assert e == pytest.approx(el)
    assert (a - az + 180) % 360 - 180 == pytest.approx(0, abs=1e-6)


def test_top_frame_matches_the_top_view():
    """Up from Front in two steps must be exactly Scene.set_view('top'): looking down, +Y up."""
    back, up = view_frame(-90, 90)
    assert np.allclose(back, (0, 0, 1)) and np.allclose(up, (0, 1, 0), atol=1e-12)
    back, up = view_frame(-90, -90)       # tilting down from Front under the model: +Y at the bottom
    assert np.allclose(back, (0, 0, -1)) and np.allclose(up, (0, -1, 0), atol=1e-12)


def _cam(plotter):
    cam = plotter.camera
    back = np.array(cam.position) - np.array(cam.focal_point)
    return azimuth_elevation(back / np.linalg.norm(back), np.array(cam.up))


def test_arrows_walk_the_45_degree_stops(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("front")
        assert _cam(plotter) == pytest.approx((-90, 0))
        c.step(1, 0, animate=False)                         # right: the model turns right
        assert _cam(plotter) == pytest.approx((-135, 0))
        c.step(-1, 0, animate=False)
        c.step(-1, 0, animate=False)                        # left twice: front-right corner side
        assert _cam(plotter) == pytest.approx((-45, 0))
        c.step(0, 1, animate=False)                         # up: from higher up
        assert _cam(plotter) == pytest.approx((-45, 45))
        c.step(0, 1, animate=False)                         # up again: straight down = Top
        _, el = _cam(plotter)
        assert el == pytest.approx(90)
        _camera_ok(plotter)
        assert _model_visible(plotter)
        c.step(0, 1, animate=False)                         # no further than Top
        assert _cam(plotter)[1] == pytest.approx(90)
        c.step(0, -1, animate=False)
        c.step(0, -1, animate=False)
        c.step(0, -1, animate=False)
        c.step(0, -1, animate=False)                        # down to Bottom
        assert _cam(plotter)[1] == pytest.approx(-90)
        _camera_ok(plotter)
    finally:
        plotter.close()


def test_two_ups_from_front_is_the_top_view(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("front")
        c.step(0, 1, animate=False)
        c.step(0, 1, animate=False)
        up = np.array(plotter.camera.up)
        scene.set_view("top")
        assert np.allclose(up, plotter.camera.up, atol=1e-9)
    finally:
        plotter.close()


def test_arrow_after_a_free_drag_lines_up_again(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("iso")
        c._orbit(37, -11)                                   # somewhere in between
        c.step(1, 0, animate=False)
        az, el = _cam(plotter)
        assert (az / 45) == pytest.approx(round(az / 45), abs=1e-6)
        assert el == pytest.approx(round(el, 6))            # the tilt is kept by a sideways step
        c.step(0, -1, animate=False)
        _, el = _cam(plotter)
        assert (el / 45) == pytest.approx(round(el / 45), abs=1e-6)
    finally:
        plotter.close()


def test_arrow_step_keeps_the_zoom(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("front")
        dist = np.linalg.norm(np.array(plotter.camera.position) - plotter.camera.focal_point)
        scale = plotter.camera.parallel_scale
        c.step(1, 0, animate=False)
        assert np.linalg.norm(np.array(plotter.camera.position) - plotter.camera.focal_point) == \
            pytest.approx(dist)
        assert plotter.camera.parallel_scale == pytest.approx(scale)
    finally:
        plotter.close()


def test_smooth_turn_runs_and_ends_on_the_view(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("front")
        start = c.camera_state()
        scene.set_view("right", render=False)
        end = c.camera_state()
        c._set_state(start)
        c.animate_to(end, ms=60)
        assert c.animating
        middle = c.blend(start, end, 0.5)
        back = middle[0] - middle[1]
        az, el = azimuth_elevation(back / np.linalg.norm(back), middle[2])
        assert az == pytest.approx(-45) and el == pytest.approx(0, abs=1e-6)   # halfway round
        import time
        t0 = time.monotonic()
        while c.animating and time.monotonic() - t0 < 2:
            app.processEvents()
        assert not c.animating
        assert all(np.allclose(a, b) for a, b in zip(c.camera_state()[:3], end[:3]))
    finally:
        plotter.close()


def test_a_press_stops_a_smooth_turn(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("front")
        c.step(1, 0)
        assert c.animating
        c._begin("rotate")
        assert not c.animating
    finally:
        plotter.close()


def test_turning_to_the_opposite_side_never_breaks_the_camera(app):
    plotter, scene, c = _scene_with_model(app)
    try:
        scene.set_view("front")
        a = c.camera_state()
        scene.set_view("back", render=False)
        b = c.camera_state()
        for t in (0.0, 0.25, 0.5, 0.75, 1.0):
            pos, foc, up, _ = c.blend(a, b, t)
            fwd = (foc - pos) / np.linalg.norm(foc - pos)
            assert np.all(np.isfinite(pos)) and abs(np.dot(up, fwd)) < 1e-6
    finally:
        plotter.close()


def test_click_on_an_arrow_steps_instead_of_picking_a_face(app):
    plotter, c, iren, views = _controls(app)
    try:
        plotter.camera_position = [(0, -10, 0), (0, 0, 0), (0, 0, 1)]
        iren.pos = (750, 10)
        c._left_down()
        c._button_up()
        assert views == []
        c.stop_animation()
        assert c.animating is False
    finally:
        plotter.close()


def test_home_on_the_cube_goes_to_iso(app, tmp_path, monkeypatch):
    _need_3d_view()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from printview3d.settings import Settings
    from printview3d.ui.main_window import MainWindow
    win = MainWindow(Settings(str(tmp_path / "settings.json")))
    try:
        calls = []
        win.set_view = lambda v, animate=False: calls.append((v, animate))
        win._cube_view("home")
        win._cube_view("left")
        assert calls == [("iso", True), ("left", True)]
        assert set(win.view_cube.tooltips) == {"arrow_left", "arrow_right", "arrow_up", "arrow_down",
                                               "home"}
    finally:
        win.close()
        win.deleteLater()

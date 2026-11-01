"""Slicer-style camera controls.

  * Left-drag       orbit; Z always stays "up" (no rolling)
                    - press on the model: it rotates around that exact point
                    - press on empty space: it rotates around the model's centre
  * Right-drag      pan            (also middle-drag or Shift + left-drag)
  * Mouse wheel     zoom towards the point under the cursor
  * View cube       (top-right corner) click a face to jump to that view, drag the cube to orbit,
                    drag its ring to turn around the vertical axis only; the arrows that appear on
                    hover turn to the next 45° stop, the Home icon goes back to Iso - see view_cube.py

Why it is built this way (root causes of earlier problems):

* Lag: every mouse-move event used to redraw the scene immediately. Gaming
  mice send up to 1000 events per second, far more than the screen can show,
  so redraws queued up and the view trailed behind the mouse. Now mouse moves
  only update the camera, and at most one redraw is scheduled; Qt runs it
  once the queued mouse events have been handled ("event coalescing").

* Unpredictable rotation: the orbit centre was the camera's focal point, and
  zoom-to-cursor moves that point around, so after zooming the model swung
  around some arbitrary spot. The orbit centre is now chosen on every press
  (the point under the mouse, or the model centre), and the camera rotates
  around it without the view jumping.

Arrow steps use fixed 45° stops (not "45° from wherever you are"): after a free drag the first
click lines the view up again, and every click lands on one of the 26 views of the cube (its 6
faces, 12 edges and 8 corners), so the same clicks always give the same view.

View changes from the cube and the view buttons turn smoothly (ANIM_MS) instead of jumping, so it
stays clear which way the model turned. Any mouse press stops a running turn at once.
"""

from __future__ import annotations

import math
import time

import numpy as np
from PySide6.QtCore import QTimer
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
from vtkmodules.vtkRenderingCore import vtkPropPicker

ROTATE_DEG_PER_PX = 0.3       # orbit speed (degrees per screen pixel)
CLICK_SLOP_PX = 4             # a press on the view cube that moves less than this is a click
ZOOM_STEP = 1.15              # zoom factor per wheel notch
MAX_PITCH = 88.0              # how far the camera may look up/down (degrees)
STEP_DEG = 45.0               # the view cube's arrows turn to the next stop of this many degrees
ANIM_MS = 250                 # length of a smooth view change (0 = jump)
ANIM_FRAME_MS = 15
_EPS_STEPS = 1e-3             # "already on a stop" tolerance, in steps (~0.05°)

ARROW_STEPS = {"arrow_left": (-1, 0), "arrow_right": (1, 0), "arrow_up": (0, 1), "arrow_down": (0, -1)}


def _rotate(v: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotate vector v around a unit axis by angle (radians) - Rodrigues."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * np.dot(axis, v) * (1 - c)


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def _slerp(a: np.ndarray, b: np.ndarray, t: float, axis_if_opposite: np.ndarray) -> np.ndarray:
    """Turn unit vector a towards unit vector b by fraction t, along the shortest arc."""
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    if dot > 0.99999:
        return _unit(a + (b - a) * t)
    if dot < -0.99999:                        # exactly opposite: turn around the given axis
        return _rotate(a, _unit(axis_if_opposite), math.pi * t)
    ang = math.acos(dot)
    s = math.sin(ang)
    return (math.sin((1 - t) * ang) * a + math.sin(t * ang) * b) / s


def _ease(t: float) -> float:
    """Smooth start and stop."""
    return t * t * (3 - 2 * t)


def next_stop(angle: float, direction: int, step: float = STEP_DEG) -> float:
    """The next multiple of `step` from `angle` in `direction` (+1 up, -1 down). An angle already on
    a stop moves a full step."""
    k = angle / step
    if direction > 0:
        return (math.floor(k + _EPS_STEPS) + 1) * step
    return (math.ceil(k - _EPS_STEPS) - 1) * step


def azimuth_elevation(back: np.ndarray, up: np.ndarray) -> tuple[float, float]:
    """Where the camera is, seen from what it looks at: azimuth around Z and elevation (degrees).
    `back` points from the focal point to the camera; `up` is the screen's up. Straight above or
    below, the azimuth comes from the screen's up (it points away from the camera's side)."""
    el = math.degrees(math.asin(max(-1.0, min(1.0, float(back[2])))))
    if abs(back[2]) > 0.9999:
        h = -np.asarray(up[:2], float) * (1.0 if back[2] > 0 else -1.0)
    else:
        h = np.asarray(back[:2], float)
    return math.degrees(math.atan2(h[1], h[0])), el


def view_frame(az: float, el: float) -> tuple[np.ndarray, np.ndarray]:
    """(back, up) for a camera at azimuth/elevation (degrees): Z up, or - straight above or
    below - the screen's up pointing away from the camera's side, as Scene.set_view() does."""
    a, e = math.radians(az), math.radians(el)
    h = np.array([math.cos(a), math.sin(a), 0.0])
    back = h * math.cos(e) + np.array([0.0, 0.0, math.sin(e)])
    up = -h * math.sin(e) + np.array([0.0, 0.0, math.cos(e)])
    return _unit(back), _unit(up)


class TurntableControls:
    def __init__(self, plotter, scene, on_interaction_start=None, on_interaction_end=None):
        self.p = plotter
        self.scene = scene
        self.iren = plotter.iren.interactor
        self.renderer = plotter.renderer
        self.on_start = on_interaction_start
        self.on_end = on_interaction_end
        self.mode = None
        self.last = (0, 0)
        self.pivot = None
        self.picker = vtkPropPicker()
        # The view cube (set by the main window) and what a click on one of its faces does
        # (called with the face name, or "home" for the Home icon).
        self.cube = None
        self.on_cube_view = None
        self._cube_part = None
        self._press = (0, 0)
        self._dragged = False
        self._tip_part = None

        # Redraw at most once per pass of the Qt event loop.
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(0)
        self._render_timer.timeout.connect(self._do_render)

        # Smooth view changes.
        self._anim = None                       # (start state, end state, start time)
        self._anim_timer = QTimer()
        self._anim_timer.setInterval(ANIM_FRAME_MS)
        self._anim_timer.timeout.connect(self._anim_step)

        # An empty style: we handle the mouse ourselves.
        self.style = vtkInteractorStyleUser()
        self._install_style(plotter)
        s = self.style
        s.AddObserver("LeftButtonPressEvent", self._left_down)
        s.AddObserver("LeftButtonReleaseEvent", self._button_up)
        s.AddObserver("RightButtonPressEvent", self._pan_down)
        s.AddObserver("RightButtonReleaseEvent", self._button_up)
        s.AddObserver("MiddleButtonPressEvent", self._pan_down)
        s.AddObserver("MiddleButtonReleaseEvent", self._button_up)
        s.AddObserver("MouseMoveEvent", self._move)
        s.AddObserver("LeaveEvent", lambda *_: self.leave())
        s.AddObserver("MouseWheelForwardEvent", lambda *_: self._zoom(ZOOM_STEP))
        s.AddObserver("MouseWheelBackwardEvent", lambda *_: self._zoom(1 / ZOOM_STEP))
        # Swallow VTK's own key shortcuts (w = wireframe, e/q = quit, ...)
        s.AddObserver("CharEvent", lambda *_: None)
        s.AddObserver("KeyPressEvent", lambda *_: None)

    def _install_style(self, plotter):
        """Make our style the interactor's style - and pyvista's too.

        Root cause of "after a double-click the view cube and its arrows stop working until a
        restart": pyvista keeps its own record of the interactor style (a trackball style it sets
        up at start) and, on every double-click in the 3D view, its built-in chart toggle
        (_toggle_chart_interaction) puts that recorded style back on the interactor. Our style was
        set on VTK directly, so pyvista still had its trackball on record: a double-click (two
        clicks within 0.8 s on nearly the same spot - two quick clicks on an arrow) silently
        replaced our controls with pyvista's trackball. Dragging still turned the view (the
        trackball), but no click ever reached the cube again, and opening a file did not help.

        So: register our style through pyvista, so its record and the real style always agree,
        and remove that chart double-click handler - PrintView3D has no pyvista charts.
        """
        pv_iren = getattr(plotter, "iren", None)
        if pv_iren is not None and hasattr(pv_iren, "untrack_click_position"):
            try:
                pv_iren.untrack_click_position(side="left")
            except Exception:   # noqa: BLE001 - older/newer pyvista: the style below still fixes it
                pass
        if pv_iren is not None and hasattr(type(pv_iren), "style"):
            pv_iren.style = self.style                 # pyvista sets it on the interactor too
        if self.iren.GetInteractorStyle() is not self.style:
            self.iren.SetInteractorStyle(self.style)

    # ------------------------------------------------------------ rendering
    def request_render(self):
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _do_render(self):
        self.renderer.ResetCameraClippingRange()
        self.iren.Render()

    # ------------------------------------------------------------ camera state + smooth turns
    def camera_state(self) -> tuple:
        cam = self.renderer.GetActiveCamera()
        return (np.array(cam.GetPosition()), np.array(cam.GetFocalPoint()), np.array(cam.GetViewUp()),
                float(cam.GetParallelScale()))

    def _set_state(self, st):
        pos, foc, up, scale = st
        cam = self.renderer.GetActiveCamera()
        cam.SetPosition(*pos)
        cam.SetFocalPoint(*foc)
        cam.SetViewUp(*up)
        cam.SetParallelScale(scale)
        cam.OrthogonalizeViewUp()

    @staticmethod
    def blend(a, b, t: float) -> tuple:
        """The camera a fraction t (0..1) of the way from state a to state b: the look direction
        and the screen's up turn along the shortest arc; focal point, distance and zoom glide."""
        p0, f0, u0, s0 = a
        p1, f1, u1, s1 = b
        foc = f0 + (f1 - f0) * t
        d0, d1 = p0 - f0, p1 - f1
        l0, l1 = float(np.linalg.norm(d0)), float(np.linalg.norm(d1))
        back = _slerp(_unit(d0), _unit(d1), t, u0)
        up = _slerp(_unit(u0), _unit(u1), t, back)
        up = up - np.dot(up, back) * back
        if float(np.linalg.norm(up)) < 1e-6:          # never let up lie along the view direction
            up = np.cross(back, np.cross(u1, back))
        return foc + back * (l0 + (l1 - l0) * t), foc, _unit(up), s0 + (s1 - s0) * t

    def animate_to(self, end, ms: int | None = None):
        """Turn smoothly from the current camera to state `end` (instantly when ms is 0)."""
        self.stop_animation()
        ms = ANIM_MS if ms is None else ms
        start = self.camera_state()
        if ms <= 0 or self._same_view(start, end):
            self._set_state(end)
            self.request_render()
            return
        self._anim = (start, end, time.monotonic(), ms / 1000.0)
        if self.on_start:
            self.on_start()
        self._anim_timer.start()
        self._anim_step()

    @staticmethod
    def _same_view(a, b) -> bool:
        return all(np.allclose(x, y, atol=1e-9) for x, y in zip(a[:3], b[:3])) and abs(a[3] - b[3]) < 1e-12

    def _anim_step(self):
        if self._anim is None:
            return
        start, end, t0, length = self._anim
        t = min(1.0, (time.monotonic() - t0) / length)
        self._set_state(end if t >= 1.0 else self.blend(start, end, _ease(t)))
        self.request_render()
        if t >= 1.0:
            self.stop_animation()

    def stop_animation(self):
        """Stop a running smooth turn where it is (any mouse press does this)."""
        if self._anim is None:
            return
        self._anim = None
        self._anim_timer.stop()
        if self.on_end:
            self.on_end()

    @property
    def animating(self) -> bool:
        return self._anim is not None

    def step(self, dx: int, dy: int, animate: bool = True):
        """The view cube's arrows: turn to the next 45° stop. dx = +1 turns the model to the right
        (as dragging to the right does), -1 to the left; dy = +1 tilts to look from higher up
        (towards Top), -1 from lower down (towards Bottom). Zoom and framing stay as they are."""
        if self._anim is not None:                 # quick clicks: continue from where it ends up
            end = self._anim[1]
            self.stop_animation()
            self._set_state(end)
        pos, foc, up, scale = self.camera_state()
        back = _unit(pos - foc)
        up_o = _unit(up - np.dot(up, back) * back)
        az, el = azimuth_elevation(back, up_o)
        if dx:
            az = next_stop(az, -dx)                # turning right = the camera goes round to the left
        if dy:
            el = max(-90.0, min(90.0, next_stop(el, dy)))
        back_n, up_n = view_frame(az, el)
        # The rotation taking the old camera frame onto the new one, around the model's centre.
        old = np.column_stack([back, up_o, np.cross(back, up_o)])
        new = np.column_stack([back_n, up_n, np.cross(back_n, up_n)])
        rot = new @ old.T
        c = self.scene.default_pivot()
        piv = np.array(c, float) if c is not None else foc
        end = (piv + rot @ (pos - piv), piv + rot @ (foc - piv), up_n, scale)
        if animate:
            self.animate_to(end)
        else:
            self._set_state(end)
            self.request_render()

    # ------------------------------------------------------------ buttons
    def _begin(self, mode):
        self.stop_animation()
        self.mode = mode
        self.last = self.iren.GetEventPosition()
        if mode == "rotate":
            self.pivot = self._pick_pivot(*self.last)
        if self.on_start:
            self.on_start()

    def _pick_pivot(self, x, y):
        actors = self.scene.pickable_actors()
        if actors:
            self.picker.InitializePickList()
            for a in actors:
                self.picker.AddPickList(a)
            self.picker.PickFromListOn()
            if self.picker.Pick(x, y, 0, self.renderer) and self.picker.GetViewProp() is not None:
                return np.array(self.picker.GetPickPosition())
        c = self.scene.default_pivot()
        if c is not None:
            return np.array(c)
        return np.array(self.renderer.GetActiveCamera().GetFocalPoint())

    def _left_down(self, *_):
        x, y = self.iren.GetEventPosition()
        part = self.cube.hit(x, y) if self.cube is not None else None
        if part is not None:
            # On the cube: a click picks a view (or an arrow step, or Home); a drag orbits around
            # the model's centre (the ring: only around the vertical axis).
            self._hide_tip()
            self._cube_part = part
            self._press = (x, y)
            self._dragged = False
            self.mode = "cube"
            self.last = (x, y)
            c = self.scene.default_pivot()
            self.pivot = np.array(c) if c is not None else \
                np.array(self.renderer.GetActiveCamera().GetFocalPoint())
            if part not in ARROW_STEPS:            # an arrow click continues a running turn
                self.stop_animation()
            if self.on_start:
                self.on_start()
            return
        self._begin("pan" if self.iren.GetShiftKey() else "rotate")

    def _pan_down(self, *_):
        self._begin("pan")

    def _button_up(self, *_):
        if self.mode is None:
            return
        clicked = self.mode == "cube" and not self._dragged and self._cube_part not in (None, "ring")
        part = self._cube_part
        self.mode = None
        self._cube_part = None
        if clicked:
            if self.on_end:
                self.on_end()
            if part in ARROW_STEPS:
                self.step(*ARROW_STEPS[part])
            elif self.on_cube_view:
                self.on_cube_view(part)          # a face name, or "home"
            return
        if self.on_end:
            self.on_end()
        self._render_timer.stop()
        self._do_render()

    # ------------------------------------------------------------ motion
    def _move(self, *_):
        x, y = self.iren.GetEventPosition()
        if self.mode is None:
            self._hover(x, y)
            return
        dx, dy = x - self.last[0], y - self.last[1]
        self.last = (x, y)
        if dx == 0 and dy == 0:
            return
        if self.mode == "cube":
            if not self._dragged:
                if abs(x - self._press[0]) + abs(y - self._press[1]) < CLICK_SLOP_PX:
                    return
                self._dragged = True
                self.stop_animation()
                dx, dy = x - self._press[0], y - self._press[1]
            self._orbit(dx, 0 if self._cube_part == "ring" else dy)
        elif self.mode == "rotate":
            self._orbit(dx, dy)
        else:
            self._pan(dx, dy)
        self.request_render()

    def _hover(self, x, y):
        """Light up the part of the view cube under the mouse, show its arrows while the mouse is
        over the cube, and set the cursor and tooltip."""
        if self.cube is None:
            return
        part = self.cube.hit(x, y)
        if self.cube.set_hover(part, self.cube.contains(x, y)):
            try:
                from PySide6.QtCore import Qt
                widget = self.p.interactor
                if part is None:
                    widget.unsetCursor()
                else:
                    widget.setCursor(Qt.SizeHorCursor if part == "ring" else Qt.PointingHandCursor)
            except Exception:   # noqa: BLE001 - no Qt widget (tests)
                pass
            self._show_tip(part)
            self.request_render()

    def _show_tip(self, part):
        if part == self._tip_part:
            return
        self._tip_part = part
        tip = getattr(self.cube, "tooltips", {}).get(part) if part else None
        try:
            from PySide6.QtGui import QCursor
            from PySide6.QtWidgets import QToolTip
            if tip:
                QToolTip.showText(QCursor.pos(), tip, self.p.interactor)
            else:
                QToolTip.hideText()
        except Exception:   # noqa: BLE001 - no Qt widget (tests)
            pass

    def _hide_tip(self):
        self._show_tip(None)

    def leave(self):
        """The mouse left the 3D view: nothing stays lit, the arrows hide."""
        self._hide_tip()
        if self.cube is not None and self.cube.set_hover(None, False):
            self.request_render()

    def _orbit(self, dx, dy):
        """Turntable orbit around self.pivot, keeping world Z up.

        Looking straight down (Top view) or up (Bottom view) is a special case: the viewing
        direction is then the Z axis itself, so "Z is up" means nothing there and the tilt axis
        cross(forward, Z) is zero. Earlier versions still forced view-up to Z; VTK then had no
        usable up direction (it became 0, 0, 0) and the model disappeared until a view button was
        pressed. Now the camera's own up direction (the top of the screen) is turned along, and
        is used for the tilt axis and as view-up whenever the camera looks straight down or up.
        """
        cam = self.renderer.GetActiveCamera()
        pos = np.array(cam.GetPosition())
        foc = np.array(cam.GetFocalPoint())
        up = np.array(cam.GetViewUp())
        piv = self.pivot if self.pivot is not None else foc

        # 1) spin around the vertical axis through the pivot (the screen's up turns along)
        z = np.array([0.0, 0.0, 1.0])
        yaw = -math.radians(dx * ROTATE_DEG_PER_PX)
        pos = piv + _rotate(pos - piv, z, yaw)
        foc = piv + _rotate(foc - piv, z, yaw)
        up = _rotate(up, z, yaw)

        # 2) tilt around the camera's horizontal axis through the pivot,
        #    limited so the camera never flips over the top or bottom
        fwd = foc - pos
        dist = float(np.linalg.norm(fwd))
        if dist < 1e-9:
            return
        fwd /= dist
        pitch_now = math.degrees(math.asin(max(-1.0, min(1.0, fwd[2]))))
        pitch_delta = dy * ROTATE_DEG_PER_PX           # drag up = look from lower down
        # Already beyond the limit (Top/Bottom view looks exactly down/up): only tilt back.
        lo, hi = min(-MAX_PITCH, pitch_now), max(MAX_PITCH, pitch_now)
        pitch_new = max(lo, min(hi, pitch_now + pitch_delta))
        tilt = math.radians(pitch_new - pitch_now)
        right = np.cross(fwd, z)
        if float(np.linalg.norm(right)) < 1e-6:        # straight down/up: use the screen's sideways
            right = np.cross(fwd, up)
        n = float(np.linalg.norm(right))
        if n > 1e-9 and tilt != 0.0:
            right /= n
            pos = piv + _rotate(pos - piv, right, tilt)
            foc = piv + _rotate(foc - piv, right, tilt)
            up = _rotate(up, right, tilt)

        cam.SetPosition(*pos)
        cam.SetFocalPoint(*foc)
        fwd = (foc - pos) / max(float(np.linalg.norm(foc - pos)), 1e-9)
        if abs(fwd[2]) > 0.9999:
            cam.SetViewUp(*up)                         # straight down/up: keep the screen's up
        else:
            cam.SetViewUp(0, 0, 1)
        cam.OrthogonalizeViewUp()

    def _pan(self, dx, dy):
        cam = self.renderer.GetActiveCamera()
        f = np.array(cam.GetFocalPoint())
        pos = np.array(cam.GetPosition())
        h = max(1, self.renderer.GetSize()[1])
        dist = float(np.linalg.norm(pos - f))
        if cam.GetParallelProjection():
            world_per_px = 2 * cam.GetParallelScale() / h
        else:
            world_per_px = 2 * dist * math.tan(math.radians(cam.GetViewAngle() / 2)) / h
        forward = (f - pos) / max(dist, 1e-9)
        up = np.array(cam.GetViewUp())
        right = np.cross(forward, up)
        right /= max(np.linalg.norm(right), 1e-9)
        true_up = np.cross(right, forward)
        move = (-dx * right - dy * true_up) * world_per_px
        cam.SetFocalPoint(*(f + move))
        cam.SetPosition(*(pos + move))

    def _zoom(self, factor):
        """Zoom towards the point under the mouse cursor."""
        self.stop_animation()
        cam = self.renderer.GetActiveCamera()
        x, y = self.iren.GetEventPosition()
        f = np.array(cam.GetFocalPoint())
        pos = np.array(cam.GetPosition())

        # Point under the cursor on the plane through the focal point.
        self.renderer.SetWorldPoint(*f, 1.0)
        self.renderer.WorldToDisplay()
        depth = self.renderer.GetDisplayPoint()[2]
        self.renderer.SetDisplayPoint(x, y, depth)
        self.renderer.DisplayToWorld()
        w = self.renderer.GetWorldPoint()
        target = np.array(w[:3]) / (w[3] or 1.0)

        t = 1.0 - 1.0 / factor
        cam.SetPosition(*(pos + (target - pos) * t))
        cam.SetFocalPoint(*(f + (target - f) * t))
        if cam.GetParallelProjection():
            cam.SetParallelScale(cam.GetParallelScale() / factor)
        self.request_render()

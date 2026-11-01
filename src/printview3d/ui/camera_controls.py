"""Slicer-style camera controls.

  * Left-drag       orbit; Z always stays "up" (no rolling)
                    - press on the model: it rotates around that exact point
                    - press on empty space: it rotates around the model's centre
  * Right-drag      pan            (also middle-drag or Shift + left-drag)
  * Mouse wheel     zoom towards the point under the cursor
  * View cube       (top-right corner) click a face to jump to that view, drag the cube to orbit,
                    drag its ring to turn around the vertical axis only - see view_cube.py

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
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QTimer
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
from vtkmodules.vtkRenderingCore import vtkPropPicker

ROTATE_DEG_PER_PX = 0.3       # orbit speed (degrees per screen pixel)
CLICK_SLOP_PX = 4             # a press on the view cube that moves less than this is a click
ZOOM_STEP = 1.15              # zoom factor per wheel notch
MAX_PITCH = 88.0              # how far the camera may look up/down (degrees)


def _rotate(v: np.ndarray, axis: np.ndarray, angle: float) -> np.ndarray:
    """Rotate vector v around a unit axis by angle (radians) - Rodrigues."""
    c, s = math.cos(angle), math.sin(angle)
    return v * c + np.cross(axis, v) * s + axis * np.dot(axis, v) * (1 - c)


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
        # The view cube (set by the main window) and what a click on one of its faces does.
        self.cube = None
        self.on_cube_view = None
        self._cube_part = None
        self._press = (0, 0)
        self._dragged = False

        # Redraw at most once per pass of the Qt event loop.
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(0)
        self._render_timer.timeout.connect(self._do_render)

        # An empty style: we handle the mouse ourselves.
        self.style = vtkInteractorStyleUser()
        self.iren.SetInteractorStyle(self.style)
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

    # ------------------------------------------------------------ rendering
    def request_render(self):
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _do_render(self):
        self.renderer.ResetCameraClippingRange()
        self.iren.Render()

    # ------------------------------------------------------------ buttons
    def _begin(self, mode):
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
            # On the cube: a click picks a view, a drag orbits around the model's centre
            # (the ring: only around the vertical axis).
            self._cube_part = part
            self._press = (x, y)
            self._dragged = False
            self.mode = "cube"
            self.last = (x, y)
            c = self.scene.default_pivot()
            self.pivot = np.array(c) if c is not None else \
                np.array(self.renderer.GetActiveCamera().GetFocalPoint())
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
        if clicked and self.on_cube_view:
            if self.on_end:
                self.on_end()
            self.on_cube_view(part)
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
                dx, dy = x - self._press[0], y - self._press[1]
            self._orbit(dx, 0 if self._cube_part == "ring" else dy)
        elif self.mode == "rotate":
            self._orbit(dx, dy)
        else:
            self._pan(dx, dy)
        self.request_render()

    def _hover(self, x, y):
        """Light up the view cube's face under the mouse (and show a hand cursor there)."""
        if self.cube is None:
            return
        part = self.cube.hit(x, y)
        if self.cube.set_hover(part):
            try:
                from PySide6.QtCore import Qt
                widget = self.p.interactor
                if part is None:
                    widget.unsetCursor()
                else:
                    widget.setCursor(Qt.PointingHandCursor if part != "ring" else Qt.SizeHorCursor)
            except Exception:   # noqa: BLE001 - no Qt widget (tests)
                pass
            self.request_render()

    def leave(self):
        """The mouse left the 3D view: no face stays lit."""
        if self.cube is not None and self.cube.set_hover(None):
            self.request_render()

    def _orbit(self, dx, dy):
        """Turntable orbit around self.pivot, keeping world Z up."""
        cam = self.renderer.GetActiveCamera()
        pos = np.array(cam.GetPosition())
        foc = np.array(cam.GetFocalPoint())
        piv = self.pivot if self.pivot is not None else foc

        # 1) spin around the vertical axis through the pivot
        z = np.array([0.0, 0.0, 1.0])
        yaw = -math.radians(dx * ROTATE_DEG_PER_PX)
        pos = piv + _rotate(pos - piv, z, yaw)
        foc = piv + _rotate(foc - piv, z, yaw)

        # 2) tilt around the camera's horizontal axis through the pivot,
        #    limited so the camera never flips over the top or bottom
        fwd = foc - pos
        dist = float(np.linalg.norm(fwd))
        if dist < 1e-9:
            return
        fwd /= dist
        pitch_now = math.degrees(math.asin(max(-1.0, min(1.0, fwd[2]))))
        pitch_delta = dy * ROTATE_DEG_PER_PX           # drag up = look from lower down
        pitch_new = max(-MAX_PITCH, min(MAX_PITCH, pitch_now + pitch_delta))
        tilt = math.radians(pitch_new - pitch_now)
        right = np.cross(fwd, z)
        n = float(np.linalg.norm(right))
        if n > 1e-9 and tilt != 0.0:
            right /= n
            pos = piv + _rotate(pos - piv, right, tilt)
            foc = piv + _rotate(foc - piv, right, tilt)

        cam.SetPosition(*pos)
        cam.SetFocalPoint(*foc)
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

"""Handles to move the cuts of View -> Clip by dragging them in the 3D view.

An option (Settings -> Viewer, off by default). While a cut is on, it gets a handle: a round knob
on the edge of its cutting plane, with a short line through it that shows which way it moves.

  * Clip from the top: the knob sits on the edge of the flat cut, at the side of the model that is
    furthest right on the screen (never in the part Clip facing you takes away). Dragging it moves
    the cut up and down.
  * Clip facing you: the knob sits on the top edge of the upright cut, in the middle. Dragging it
    moves the cut further away or nearer.

A drag follows the mouse along the direction the cut moves in as it is seen on the screen. When
that direction is seen end-on (the flat cut straight from above, the upright cut from eye level)
it would hardly show on the screen: then dragging up moves the cut up / further away, at the
scale of the model under the mouse.

The handles only report the new position (on_drag); the main window moves the cut's slider, so
the slider, the numbers under it and the 3D view stay one and the same thing. The knobs are drawn
in a renderer of their own above the model (layer 2, the main camera), so they are never hidden.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

import numpy as np
from vtkmodules.vtkCommonCore import vtkPoints, vtkUnsignedCharArray
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper, vtkRenderer

CUTS = ("top", "face")
KNOB_PX = 16                  # the knob's size on the screen
KNOB_HOVER_PX = 20            # ... with the mouse over it
GRAB_PX = 14                  # a press this close to a knob takes it
AXIS_PX = 34                  # the line through the knob reaches this far on the screen, each way
AXIS_WIDTH = 3
MIN_SCREEN_SHARE = 0.3        # the direction a cut moves in, seen on the screen, shorter than this
                              # share of what it would be seen side-on: dragging up moves it instead


def _rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class ClipHandles:
    def __init__(self, plotter, scene, get_cuts: Callable[[], dict], on_drag: Callable[[str, float], None],
                 request_render: Optional[Callable[[], None]] = None):
        """get_cuts(): {"top": height in mm, "face": distance of the upright cut from the centre of
        the view in mm} for the cuts that are on. on_drag(cut, value): the user dragged a cut there."""
        self.p = plotter
        self.scene = scene
        self.get_cuts = get_cuts
        self.on_drag = on_drag
        self.request_render = request_render or plotter.render
        self.enabled = False
        self.hover: Optional[str] = None
        self.dragging: Optional[str] = None
        self._drag = None                   # (cut, value at the press, press x/y, px per mm, screen dir)
        self._knobs: dict = {}              # cut -> (knob, axis direction) in world coordinates
        self._ren: Optional[vtkRenderer] = None
        self._poly = self._axis_poly = None
        self._knob_actor = self._lit_actor = self._axis_actor = None
        self._lit_poly = None
        self._hidden = False                # for a moment (screenshots)
        self._ensure_overlay()              # its hook places the knobs before every frame
        self._ren.SetDraw(False)
        self._rgb = (20, 115, 106)
        self._hover_rgb = (44, 193, 178)

    # ------------------------------------------------------------ on / off, colours
    def set_enabled(self, on: bool):
        self.enabled = bool(on)
        if not self.enabled:
            self.hover = self.dragging = None
            self._drag = None
        self.refresh()

    def set_colors(self, t: dict):
        """The cutting planes' colour (accent ink); the knob under the mouse in the main colour."""
        self._rgb = _rgb(t.get("accent_ink", "#14736a"))
        self._hover_rgb = _rgb(t.get("primary", "#2cc1b2"))
        self.refresh()

    def refresh(self):
        """Draw the knobs where the cuts are now (also runs before every frame)."""
        self._place()
        if self._ren is not None:
            self._draw()

    @property
    def shown(self) -> list:
        """The cuts that have a knob now."""
        return list(self._knobs)

    # ------------------------------------------------------------ where the knobs are
    def _bounds(self):
        return self.scene.focus_bounds if getattr(self.scene, "model_actors", None) else None

    def _place(self, *_):
        self._knobs = {}
        cuts = self.get_cuts() if self.enabled else {}
        b = self._bounds()
        if not cuts or not b:
            if self._ren is not None:
                self._ren.SetDraw(False)
            return
        self._ensure_overlay()
        self._ren.SetDraw(not self._hidden)
        pad = max(2.0, 0.04 * max(b[1] - b[0], b[3] - b[2], b[5] - b[4]))
        face = self.scene.face_plane() if "face" in cuts else None
        if "top" in cuts:
            z = float(cuts["top"])
            xs, ys = (b[0] - pad, (b[0] + b[1]) / 2, b[1] + pad), (b[2] - pad, (b[2] + b[3]) / 2, b[3] + pad)
            # The corners and the middles of the sides of the flat cutting plane.
            cand = np.array([(x, y, z) for x in xs for y in ys if not (x == xs[1] and y == ys[1])], dtype=float)
            if face is not None:                         # not in what Clip facing you takes away
                o, n = face
                behind = (cand - o) @ n >= -1e-9
                if behind.any():
                    cand = cand[behind]
            scr = np.array([self._to_screen(c) for c in cand])
            self._knobs["top"] = (cand[int(np.argmax(scr[:, 0]))], np.array([0.0, 0.0, 1.0]))
        if face is not None:
            o, n = face
            top = b[5] + pad
            if "top" in cuts:
                top = min(top, float(cuts["top"]))
            knob = np.array([o[0], o[1], top], dtype=float)
            # The middle of the upright plane as wide as the model is, seen from the cut's side.
            side = np.array([-n[1], n[0], 0.0])
            corners = np.array([(x, y) for x in (b[0], b[1]) for y in (b[2], b[3])])
            s = (corners - o[:2]) @ side[:2]
            knob[:2] += side[:2] * (s.min() + s.max()) / 2
            self._knobs["face"] = (knob, np.array(n, dtype=float))

    # ------------------------------------------------------------ screen
    def _to_screen(self, p) -> np.ndarray:
        ren = self.p.renderer
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0)
        ren.WorldToDisplay()
        d = ren.GetDisplayPoint()
        return np.array([d[0], d[1]], dtype=float)

    def _world_per_px(self, point) -> float:
        ren = self.p.renderer
        cam = ren.GetActiveCamera()
        h = max(1, ren.GetSize()[1])
        if cam.GetParallelProjection():
            return 2.0 * cam.GetParallelScale() / h
        pos = np.array(cam.GetPosition())
        fwd = np.array(cam.GetDirectionOfProjection())
        depth = float(np.dot(np.asarray(point, float) - pos, fwd))
        return 2.0 * max(depth, 1e-6) * math.tan(math.radians(cam.GetViewAngle()) / 2.0) / h

    def _scale(self) -> float:
        try:
            return float(self.p.interactor.devicePixelRatioF())
        except Exception:   # noqa: BLE001 - no Qt widget (tests)
            return 1.0

    # ------------------------------------------------------------ mouse
    def hit(self, x: int, y: int) -> Optional[str]:
        """The cut whose knob is under display position x, y, or None."""
        if not self.enabled:
            return None
        self._place()
        best, best_d = None, GRAB_PX * self._scale()
        for cut, (knob, _axis) in self._knobs.items():
            d = float(np.linalg.norm(self._to_screen(knob) - (x, y)))
            if d <= best_d:
                best, best_d = cut, d
        return best

    def set_hover(self, cut: Optional[str]) -> bool:
        """Light up the knob under the mouse. True when that changed (redraw)."""
        if cut == self.hover:
            return False
        self.hover = cut
        if self._ren is not None:
            self._draw()
        return True

    def begin(self, cut: str, x: int, y: int) -> bool:
        """A press on the knob of `cut`: start moving it."""
        cuts = self.get_cuts()
        if cut not in cuts or cut not in self._knobs:
            return False
        knob, axis = self._knobs[cut]
        wpp = self._world_per_px(knob)
        span = 10.0 * wpp                                # a short piece of the axis, in mm
        d = self._to_screen(knob + axis * span) - self._to_screen(knob)
        px_per_mm = float(np.linalg.norm(d)) / span
        if px_per_mm < MIN_SCREEN_SHARE / wpp:           # seen end-on: dragging up moves it
            direction, px_per_mm = np.array([0.0, 1.0]), 1.0 / wpp
        else:
            direction = d / float(np.linalg.norm(d))
        self._drag = (cut, float(cuts[cut]), np.array([x, y], dtype=float), px_per_mm, direction)
        self.dragging = cut
        if self._ren is not None:
            self._draw()
        return True

    def drag_to(self, x: int, y: int):
        if self._drag is None:
            return
        cut, start, press, px_per_mm, direction = self._drag
        moved = float(np.dot(np.array([x, y], dtype=float) - press, direction)) / px_per_mm
        self.on_drag(cut, start + moved)
        self.refresh()
        self.request_render()

    def end(self):
        self._drag = None
        self.dragging = None
        if self._ren is not None:
            self._draw()
        self.request_render()

    # ------------------------------------------------------------ drawing
    def _ensure_overlay(self):
        if self._ren is not None:
            return
        win = self.p.ren_win
        main = self.p.renderer
        ren = vtkRenderer()
        ren.SetLayer(2)
        ren.InteractiveOff()
        if win.GetNumberOfLayers() < 3:
            win.SetNumberOfLayers(3)
        win.AddRenderer(ren)
        ren.SetActiveCamera(main.GetActiveCamera())
        # The cuts follow the view (Clip facing you) and the knob of the flat cut changes sides as
        # the view turns: place them before every frame, through the main view's camera.
        main.AddObserver("StartEvent", lambda *_: (ren.SetActiveCamera(main.GetActiveCamera()), self.refresh()))
        self._ren = ren

        self._axis_poly = vtkPolyData()
        am = vtkPolyDataMapper()
        am.SetInputData(self._axis_poly)
        am.SetColorModeToDirectScalars()
        self._axis_actor = vtkActor()
        self._axis_actor.SetMapper(am)
        ap = self._axis_actor.GetProperty()
        ap.SetLineWidth(AXIS_WIDTH)
        ap.SetRenderLinesAsTubes(True)
        ap.LightingOff()
        self._axis_actor.PickableOff()
        ren.AddActor(self._axis_actor)

        def knob_actor(poly):
            km = vtkPolyDataMapper()
            km.SetInputData(poly)
            km.SetColorModeToDirectScalars()
            a = vtkActor()
            a.SetMapper(km)
            kp = a.GetProperty()
            kp.SetRenderPointsAsSpheres(True)
            kp.LightingOff()
            a.PickableOff()
            ren.AddActor(a)
            return a

        self._poly, self._lit_poly = vtkPolyData(), vtkPolyData()
        self._knob_actor = knob_actor(self._poly)
        self._lit_actor = knob_actor(self._lit_poly)          # the one under the mouse: bigger

    @staticmethod
    def _points(poly, points: list, rgb: tuple):
        pts, colors, verts = vtkPoints(), vtkUnsignedCharArray(), vtkCellArray()
        colors.SetNumberOfComponents(3)
        for p in points:
            pts.InsertNextPoint(*p)
            colors.InsertNextTuple3(*rgb)
            verts.InsertNextCell(1)
            verts.InsertCellPoint(pts.GetNumberOfPoints() - 1)
        poly.SetPoints(pts)
        poly.SetVerts(verts)
        poly.GetPointData().SetScalars(colors)
        poly.Modified()

    def _draw(self):
        lpts, lcolors, lines = vtkPoints(), vtkUnsignedCharArray(), vtkCellArray()
        lcolors.SetNumberOfComponents(3)
        lit = self.dragging or self.hover
        self._points(self._poly, [k for c, (k, _) in self._knobs.items() if c != lit], self._rgb)
        self._points(self._lit_poly, [k for c, (k, _) in self._knobs.items() if c == lit], self._hover_rgb)
        for cut, (knob, axis) in self._knobs.items():
            rgb = self._hover_rgb if cut == lit else self._rgb
            reach = AXIS_PX * self._scale() * self._world_per_px(knob)
            i = lpts.GetNumberOfPoints()
            for p in (knob - axis * reach, knob + axis * reach):
                lpts.InsertNextPoint(*p)
                lcolors.InsertNextTuple3(*rgb)
            lines.InsertNextCell(2)
            lines.InsertCellPoint(i)
            lines.InsertCellPoint(i + 1)
        self._axis_poly.SetPoints(lpts)
        self._axis_poly.SetLines(lines)
        self._axis_poly.GetPointData().SetScalars(lcolors)
        self._axis_poly.Modified()
        self._knob_actor.GetProperty().SetPointSize(KNOB_PX * self._scale())
        self._lit_actor.GetProperty().SetPointSize(KNOB_HOVER_PX * self._scale())
        self._axis_actor.GetProperty().SetLineWidth(AXIS_WIDTH * self._scale())

    def set_visible(self, on: bool):
        """Hide the knobs for a moment (screenshots) and show them again."""
        self._hidden = not on
        if self._ren is not None:
            self._ren.SetDraw(bool(on) and bool(self._knobs))

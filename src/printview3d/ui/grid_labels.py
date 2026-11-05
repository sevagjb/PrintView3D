"""Numbers in millimetres along the build plate's major grid lines (Settings -> Viewer, off by
default).

Decisions
  * The numbers are on the plate's major grid lines: every 50 mm on a normal plate (every 25 mm
    on a tiny one, every 250 mm on a huge one), the same spacing the grid itself uses. Where that
    would give more than MAX_LABELS numbers along an edge, only every 2nd, 5th, 10th ... is
    written, so a 120 mm plate and a 500 mm plate both get a few readable numbers.
    A small plate or area (too few major lines) gets numbers on the lines in between.
    Settings can set another spacing (5 .. 100 mm) instead: then it is exactly that.
  * They sit just outside the two edges of the plate nearest to the camera, the X numbers along
    one and the Y numbers along the other, and move to the other edges when the view turns round.
  * They are upright, always readable text in the plate edge's colour with no box: small and
    quiet. They are hidden while the camera is under the plate.
  * The endless grid has no edge: its numbers follow the area around the model (the rectangle
    the grid is drawn for), so they stay near the model.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

import numpy as np

from .. import units
from ..i18n import tr
from .overlay_text import Sprites, device_scale, label_picture, make_overlay, _rgb

MAX_LABELS = 8                # along one edge (automatic spacing)
STEPS = (5, 10, 20, 25, 50, 100)     # the fixed spacings Settings offers, in mm
MAX_FIXED = 120               # a fixed spacing never writes more than this many numbers along an edge
MULTIPLES = (1, 2, 5, 10, 20, 50, 100)
OFFSET_PX = 13                # how far outside the edge the text sits


def major_step(width: float, depth: float, scene=None) -> float:
    """The spacing of the plate's major grid lines in mm (as the scene draws them; without a
    scene: the automatic millimetre grid, a major line every 5th minor one)."""
    if scene is not None:
        return scene.grid_spacing(max(width, depth))[1]
    from .scene import Scene
    return Scene._grid_step(max(width, depth)) * 5


def _whole(step_mm: float) -> bool:
    """Is this a spacing worth writing: a whole number, or at most 3 decimals in inches?"""
    v = units.to_display(step_mm) * 1000
    return abs(v - round(v)) < 1e-6 and (units.imperial() or float(step_mm).is_integer())


def text_for(mm: float) -> str:
    """'50 mm', '2 in', '0.5 in'."""
    return tr("{d} {unit}").format(d=units.short(units.to_display(mm)), unit=units.name())


def _multiples(lo: float, hi: float, step: float) -> list:
    first = math.ceil(lo / step - 1e-9)
    last = math.floor(hi / step + 1e-9)
    return [i * step for i in range(first, last + 1) if i != 0]


def label_values(lo: float, hi: float, major: float, max_labels: int = MAX_LABELS, step: float = 0) -> list:
    """The values to write along an edge running from lo to hi: multiples of `major` (the major
    grid lines), thinned to every 2nd, 5th, ... when there would be more than max_labels. Zero is
    not written. A small plate or area that holds fewer than 2 major lines gets the lines in
    between (half or a fifth of `major`, when that is a whole number), so it is never bare.
    step > 0 is a spacing you chose: every `step` mm, exactly, not thinned (only capped at
    MAX_FIXED numbers, so a 5 mm step on a huge plate stays sane)."""
    if step and step > 0:
        vals = _multiples(lo, hi, step)
        return vals if len(vals) <= MAX_FIXED else []
    for k in MULTIPLES:
        vals = _multiples(lo, hi, major * k)
        if len(vals) <= max_labels:
            break
    if len(vals) >= 2 or k != MULTIPLES[0]:
        return vals
    for div in (2, 4, 5, 10):
        step = major / div
        if not _whole(step):
            continue
        finer = _multiples(lo, hi, step)
        if 2 <= len(finer) <= max_labels:
            return finer
    return vals


class GridLabels:
    def __init__(self, plotter, scene, request_render: Optional[Callable[[], None]] = None):
        self.p = plotter
        self.scene = scene
        self.request_render = request_render or plotter.render
        self.enabled = False
        self.step = 0                     # 0: automatic (the major lines); else a spacing in mm
        self.items: list = []             # what is shown now: (text, world position)
        self._fg = (122, 130, 141)
        self._cache: dict = {}
        self._ren = make_overlay(plotter)
        self.sprites = Sprites(self._ren)
        plotter.renderer.AddObserver("StartEvent", self._layout)

    def set_enabled(self, on: bool):
        self.enabled = bool(on)
        self._layout()
        self.request_render()

    def set_step(self, mm):
        """Settings -> Viewer: the spacing of the numbers in mm; 0 (or empty) is automatic."""
        try:
            self.step = max(0.0, float(mm or 0))
        except (TypeError, ValueError):
            self.step = 0
        self._layout()
        self.request_render()

    def set_colors(self, t: dict):
        """The grid's own colours: the plate edge's, which the lines around the plate use."""
        self._fg = _rgb(t["plate_edge"])
        self._cache = {}
        self._layout()
        self.request_render()

    def _picture(self, text: str, scale: float):
        key = (text, scale, self._fg)
        hit = self._cache.get(key)
        if hit is None:
            if len(self._cache) > 80:
                self._cache = {}
            hit = self._cache[key] = label_picture(text, self._fg, None, scale, font_px=12, pad=(2, 1),
                                                   first_bold=False)
        return hit

    def _to_screen(self, p) -> tuple:
        ren = self.p.renderer
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0)
        ren.WorldToDisplay()
        d = ren.GetDisplayPoint()
        return d[0], d[1]

    def wanted(self) -> list:
        """[(text, world position of the line's end on the edge, the plate's centre line there)]
        for the camera as it is now, or [] when nothing is to be shown."""
        b = self.scene.bed_bounds
        if not self.enabled or b is None or not getattr(self.scene, "bed_visible", True):
            return []
        xmin, xmax, ymin, ymax, z = b[0], b[1], b[2], b[3], b[4]
        cam = self.p.renderer.GetActiveCamera().GetPosition()
        if cam[2] < z - 1e-3:                         # under the plate: the text would be back to front
            return []
        major = major_step(xmax - xmin, ymax - ymin, self.scene)
        y_edge = ymin if cam[1] <= (ymin + ymax) / 2 else ymax       # the edges nearest the camera
        x_edge = xmin if cam[0] <= (xmin + xmax) / 2 else xmax
        cy, cx = (ymin + ymax) / 2, (xmin + xmax) / 2
        out = []
        for x in label_values(xmin, xmax, major, step=self.step):
            out.append((text_for(x), (x, y_edge, z), (x, cy, z)))
        for y in label_values(ymin, ymax, major, step=self.step):
            out.append((text_for(y), (x_edge, y, z), (cx, y, z)))
        return out

    def _layout(self, *_):
        scale = device_scale(self.p)
        wanted = self.wanted()
        self.items = [(t, a) for t, a, _c in wanted]
        off = OFFSET_PX * scale
        for i, (text, anchor, centre) in enumerate(wanted):
            tex, w, h = self._picture(text, scale)
            sx, sy = self._to_screen(anchor)
            cx, cy = self._to_screen(centre)
            v = np.array([sx - cx, sy - cy], dtype=float)
            n = float(np.linalg.norm(v))
            v = v / n if n > 1e-6 else np.array([0.0, -1.0])         # outwards, away from the plate
            self.sprites.put(i, tex, sx + v[0] * off - w / 2, sy + v[1] * off - h / 2, w, h)
        self.sprites.hide_from(len(wanted))

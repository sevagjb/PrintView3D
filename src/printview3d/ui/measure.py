"""The Measure tool: distances, angles and circles on the model.

Three kinds (picked with the toolbar's Measure button):
  * distance - two points: the straight line between them (and its ΔX / ΔY / ΔZ in the panel);
  * angle    - three points: a point on one side, the corner, a point on the other side;
  * circle   - three points on the edge of a circle or hole: its diameter and radius.

How it works
  * A click on the model places a point; a click on nothing does nothing. While a measurement is
    unfinished, the line (or angle, or circle) follows the mouse and its value is live. Finished
    measurements stay on screen; the next click starts another one. Clear removes them all.
  * A click is a point, a drag still turns the view (camera_controls.py tells them apart), so you
    can turn the model between two points. A drag that starts on a placed point moves that point
    instead.
  * The value is written next to the line, the angle's arc and the circle.
  * Snapping: first to the model's corners (vertices), then to the middle of an edge, then to
    the nearest point on an edge. Only the corners and edges of the triangle under the mouse are
    looked at, and only real edges of the model: the diagonals that split a flat face into
    triangles and the edges inside a smooth curve are not edges.
  * Speed: finding the point under the mouse on every mouse move would walk every triangle, which
    gets slow on big models. Each part gets a vtkStaticCellLocator, built once when Measure is
    turned on (and again only when another model is shown), and the picker uses it.
  * The markers, lines and values are drawn in a second renderer on top of the 3D view (layer 1,
    the same camera, like the view cube), so they stay visible when a line runs through the model.
  * Dotted line (an option, drawn as short dashes): every line, arc and circle.
  * Values that would overlap on the screen (concentric circles share their centre) are stacked
    above each other, and re-ordered as the view turns.

The tool knows nothing about Qt widgets: the main window gives it a callback for changes (to fill
the side panel) and one to ask for a redraw.
"""

from __future__ import annotations

import math
from typing import Callable, NamedTuple, Optional

import numpy as np
from vtkmodules.vtkCommonCore import vtkFloatArray, vtkIdList, vtkPoints, vtkUnsignedCharArray
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData, vtkStaticCellLocator
from vtkmodules.vtkRenderingCore import (
    vtkActor, vtkCellPicker, vtkPolyDataMapper, vtkPolyDataMapper2D, vtkRenderer, vtkTexturedActor2D,
)

from ..i18n import num, tr
from .overlay_text import label_picture

UNIT = "mm"                   # the one place that knows the unit (a global unit setting comes later)
KINDS = ("distance", "angle", "circle")
NEED = {"distance": 2, "angle": 3, "circle": 3}      # points a measurement needs

SNAP_PX = 16                  # a corner this close to the mouse (screen pixels) is snapped to
MID_PX = 12                   # the middle of an edge this close ...
EDGE_PX = 8                   # ... or the edge itself this close
GRAB_PX = 12                  # a placed point this close to the mouse can be dragged
MARKER_PX = 12                # size of the markers of placed points
HOVER_PX = 9                  # size of the marker that follows the mouse
CORE_PX = 4                   # the small black dot in the middle of every marker
DOT_MIN_WIDTH = 3             # a dotted line is at least this thick: 1 px dots can hardly be seen
START_RGB = (46, 196, 255)    # first point
MIDDLE_RGB = (199, 146, 255)  # the corner of an angle, the second point of a circle
END_RGB = (125, 220, 31)      # last point
LINE_RGB = (255, 255, 255)    # the defaults are the dark theme's; set_colors() follows the theme
LINE_WIDTH_DEFAULT = 4        # thickness of the lines in screen pixels (Settings -> Viewer)
DOT_LENGTH = 0.3              # the dotted line: a dot is this long and the dots are this far
DOT_PERIOD = 2.6              # apart, both in line widths, so they stay round dots at every zoom
MAX_DOTS = 3000
ARC_STEPS = 24
CIRCLE_STEPS = 72
LABEL_FONT_PX = 13            # the value's text; its box has rounded corners
LABEL_PAD = (7, 3)            # space around the text (x, y), and the corner radius:
LABEL_RADIUS = 6
LABEL_OFFSET_PX = 14          # the value sits this far above its anchor
LABEL_GAP_PX = 4              # space between values stacked above each other


# ---------------------------------------------------------------- geometry (no VTK needed)
def _rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def distances(a, b) -> tuple[float, float, float, float]:
    """(distance, dX, dY, dZ) going from point a to point b. Signed deltas: b minus a."""
    d = np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
    return float(np.linalg.norm(d)), float(d[0]), float(d[1]), float(d[2])


def _unit(v: np.ndarray) -> Optional[np.ndarray]:
    n = float(np.linalg.norm(v))
    return None if n < 1e-12 else v / n


def angle_at(a, v, b) -> Optional[float]:
    """The angle in degrees at corner v between the points a and b; None if a or b is v."""
    u = _unit(np.asarray(a, dtype=float) - np.asarray(v, dtype=float))
    w = _unit(np.asarray(b, dtype=float) - np.asarray(v, dtype=float))
    if u is None or w is None:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(u, w))))))


def circle_through(a, b, c) -> Optional[tuple]:
    """(centre, radius, unit normal) of the circle through three points in space; None when the
    points lie on one line (or coincide)."""
    a, b, c = (np.asarray(p, dtype=float) for p in (a, b, c))
    ab, ac = b - a, c - a
    n = np.cross(ab, ac)
    nn = float(np.dot(n, n))
    scale = max(float(np.dot(ab, ab)), float(np.dot(ac, ac)), 1e-30)
    if nn < 1e-12 * scale * scale:
        return None
    centre = a + np.cross(float(np.dot(ab, ab)) * ac - float(np.dot(ac, ac)) * ab, n) / (2.0 * nn)
    return centre, float(np.linalg.norm(centre - a)), n / math.sqrt(nn)


def _perpendicular(n: np.ndarray) -> np.ndarray:
    helper = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    return _unit(np.cross(n, helper))


def circle_points(centre, radius: float, normal, steps: int = CIRCLE_STEPS) -> np.ndarray:
    """Points around a circle, the first repeated at the end (a closed polyline)."""
    n = _unit(np.asarray(normal, dtype=float))
    e1 = _perpendicular(n)
    e2 = np.cross(n, e1)
    t = np.linspace(0.0, 2.0 * math.pi, steps + 1)
    return np.asarray(centre, float) + radius * (np.outer(np.cos(t), e1) + np.outer(np.sin(t), e2))


def arc_points(v, a, b, radius: float, steps: int = ARC_STEPS) -> Optional[np.ndarray]:
    """Points on the arc around corner v from the direction of a to the direction of b."""
    v = np.asarray(v, float)
    u = _unit(np.asarray(a, float) - v)
    w = _unit(np.asarray(b, float) - v)
    if u is None or w is None:
        return None
    theta = math.acos(max(-1.0, min(1.0, float(np.dot(u, w)))))
    perp = w - np.dot(w, u) * u
    e2 = _unit(perp)
    if e2 is None:                                   # straight on (0° or 180°): any sideways direction
        e2 = _perpendicular(u)
    t = np.linspace(0.0, theta, steps + 1)
    return v + radius * (np.outer(np.cos(t), u) + np.outer(np.sin(t), e2))


class Shape(NamedTuple):
    """What to draw for one measurement."""
    dist_lines: list             # [(p, q)]: the distance line (the one that can be dotted)
    lines: list                  # polylines (arrays of points): angle sides and arc, circle, rays
    label: Optional[tuple]       # (anchor point, text, lines apart by a line break) or None
    values: Optional[dict]       # for the side panel; None while there is nothing to read yet


EMPTY = Shape([], [], None, None)


def half_text(diameter: float) -> str:
    """The radius belonging to a diameter that is shown rounded to 0.01: exactly half of what is
    written (three decimals when half of it needs them: 19.99 -> 9.995), so R is never a
    rounded-up R."""
    d = round(float(diameter), 2)
    return num(d / 2, 2 if round(d * 100) % 2 == 0 else 3)


def _signed(v: float) -> str:
    return ("+" if v > 0.005 else ("−" if v < -0.005 else "")) + num(abs(v), 2)


def shape_of(kind: str, pts: list, deltas: bool = False) -> Shape:
    """The drawing and the numbers for a measurement of `kind` with these points (the last may
    be the mouse, for the live preview). deltas: a distance's value also lists its ΔX, ΔY, ΔZ."""
    pts = [np.asarray(p, dtype=float) for p in pts]
    if kind == "distance":
        if len(pts) < 2:
            return EMPTY
        d, dx, dy, dz = distances(pts[0], pts[1])
        text = tr("{d} {unit}").format(d=num(d, 2), unit=UNIT)
        if deltas:
            text += "\n" + tr("ΔX {x}   ΔY {y}   ΔZ {z}").format(x=_signed(dx), y=_signed(dy), z=_signed(dz))
        return Shape([(pts[0], pts[1])], [], ((pts[0] + pts[1]) / 2, text),
                     {"kind": "distance", "distance": d, "dx": dx, "dy": dy, "dz": dz})
    if len(pts) < 2:
        return EMPTY
    if len(pts) == 2:                                # the first side, still on its way
        return Shape([], [np.array(pts[:2])], None, None)
    a, b, c = pts[:3]
    if kind == "angle":                              # a: one side, b: the corner, c: the other side
        ang = angle_at(a, b, c)
        sides = [np.array([b, a]), np.array([b, c])]
        if ang is None:
            return Shape([], sides, None, None)
        la, lc = float(np.linalg.norm(a - b)), float(np.linalg.norm(c - b))
        r = 0.35 * min(la, lc)
        arc = arc_points(b, a, c, r)
        bis = _unit(_unit(a - b) + _unit(c - b))
        if bis is None:
            bis = _perpendicular(_unit(a - b))
        return Shape([], sides + ([arc] if arc is not None else []),
                     (b + bis * r * 1.25, tr("{a}°").format(a=num(ang, 1))),
                     {"kind": "angle", "angle": ang, "len_a": la, "len_b": lc})
    res = circle_through(a, b, c)                    # circle
    if res is None:
        return Shape([], [np.array([a, b]), np.array([b, c])], None, None)
    centre, r, normal = res
    across = np.array([a, 2 * centre - a])           # a diameter, from the first point
    return Shape([], [circle_points(centre, r, normal), across],
                 (centre, tr("Ø {d} {unit}  ·  R {r} {unit}").format(d=num(2 * r, 2), r=half_text(2 * r), unit=UNIT)),
                 {"kind": "circle", "diameter": 2 * r, "radius": r})


def is_valid(kind: str, pts: list) -> bool:
    """Can a finished measurement have these points? (No circle through points on a line, no
    angle with its corner on top of a side's point.)"""
    if len(pts) < NEED[kind]:
        return True
    if kind == "angle":
        return angle_at(pts[0], pts[1], pts[2]) is not None
    if kind == "circle":
        return circle_through(*pts[:3]) is not None
    return True


class Item:
    """One measurement: its kind and the points placed so far."""
    __slots__ = ("kind", "points")

    def __init__(self, kind: str):
        self.kind = kind
        self.points: list[np.ndarray] = []

    @property
    def complete(self) -> bool:
        return len(self.points) >= NEED[self.kind]


# ---------------------------------------------------------------- the tool
class MeasureTool:
    def __init__(self, plotter, scene, on_change: Optional[Callable[[], None]] = None,
                 request_render: Optional[Callable[[], None]] = None):
        self.p = plotter
        self.scene = scene
        self.on_change = on_change
        self.request_render = request_render or plotter.render
        self.active = False
        self.snap = True
        self.dotted = False
        self.line_width = LINE_WIDTH_DEFAULT
        self.deltas = False                          # a distance's value also lists ΔX, ΔY, ΔZ
        self.mode = "distance"
        self.items: list[Item] = []
        self.current: Optional[Item] = None          # the one the panel shows: the latest touched
        self.hover_point: Optional[np.ndarray] = None
        self.hover_kind = "free"
        self._grab: Optional[tuple] = None           # (item, index of its point) under the press
        self._dragging = False
        self._locators: dict = {}                    # id(actor) -> (actor, its mesh, locator)
        self._picker = vtkCellPicker()
        self._picker.SetTolerance(0.0005)
        self._ren: Optional[vtkRenderer] = None
        self._ren_top: Optional[vtkRenderer] = None
        self._marks = self._lines = None
        self._mark_poly = self._lines_poly = self._core_poly = self._core = None
        # Colours that follow the theme (set_colors): the lines and the value text, the value's
        # background, and what the marker under the mouse looks like for each kind of snap.
        self._line_rgb = LINE_RGB
        self._label_rgb = (255, 255, 255)
        self._label_bg = (15, 20, 25)
        self._hover_rgb = {"corner": (44, 193, 178), "mid": (79, 208, 195), "edge": (255, 255, 255),
                           "free": (190, 190, 190)}
        self._solid_src: list = []                # the lines before dotting
        self._dots_for = None                     # the view the dots were made for
        self._label_items: list = []              # (anchor, width, height) of the values shown
        self.label_texts: list = []               # their texts, and where they sit on the screen
        self.label_rects: list = []
        self._label_cache: dict = {}              # (text, colours, scale) -> (texture, width, height)
        self._labels: list = []
        self._label_polys: list = []

    # ------------------------------------------------------------ on / off
    def start(self):
        self.active = True
        self._reset()
        self._ensure_overlay()
        self._ren.SetDraw(True)
        self._ren_top.SetDraw(True)
        self.refresh_model()
        self._update()

    def stop(self):
        self.active = False
        self._reset()
        self._locators = {}
        if self._ren is not None:
            self._ren.SetDraw(False)
            self._ren_top.SetDraw(False)
        self._update()

    def _reset(self):
        self.items = []
        self.current = None
        self.hover_point = None
        self._grab = None
        self._dragging = False

    def clear(self):
        """Remove every measurement (the tool stays on)."""
        self._reset()
        self._update()

    def set_colors(self, t: dict):
        """Colours for the theme `t` (theme.colors()): lines and value text in the text colour
        (light on dark themes, dark on light ones), the value on the window colour, and the marker
        under the mouse in the theme's main colour, like the view cube's hovered part."""
        self._line_rgb = _rgb(t["text"])
        self._label_rgb = _rgb(t["text"])
        self._label_bg = _rgb(t["window"])
        self._hover_rgb = {"corner": _rgb(t["primary"]), "mid": _rgb(t["primary_hover"]),
                           "edge": _rgb(t["text"]), "free": _rgb(t["muted"])}
        self._label_cache = {}
        if self._ren is not None:
            self._lines.GetProperty().SetColor(*(v / 255 for v in self._line_rgb))
            self._draw()
            self.request_render()

    def set_line_width(self, px: float):
        """Thickness of the lines in screen pixels (Settings -> Viewer)."""
        self.line_width = max(1.0, float(px))
        self._apply_width()
        if self.active:
            self.request_render()

    def set_deltas(self, on: bool):
        self.deltas = bool(on)
        if self.active:
            self._update()

    def set_snap(self, on: bool):
        self.snap = bool(on)

    def drawn_width(self) -> float:
        """The thickness the lines are drawn with: the setting, but at least DOT_MIN_WIDTH while
        they are dotted (a thin line is fine, thin dots are not)."""
        return max(self.line_width, DOT_MIN_WIDTH) if self.dotted else self.line_width

    def _apply_width(self):
        if self._lines is not None:
            self._lines.GetProperty().SetLineWidth(self.drawn_width())
            self._rebuild_lines()

    def set_dotted(self, on: bool):
        self.dotted = bool(on)
        self._apply_width()
        self._apply_dotted()
        if self.active:
            self.request_render()

    def set_mode(self, kind: str):
        """Distance, angle or circle. A measurement that is not finished is dropped."""
        if kind not in KINDS or kind == self.mode:
            return
        self.mode = kind
        if self.items and not self.items[-1].complete:
            self.items.pop()
        self.current = self.items[-1] if self.items else None
        self._grab = None
        self._update()

    def refresh_model(self) -> bool:
        """Call after a model was shown: new parts, new locators, no old measurements. True if
        it was another model than before."""
        actors = self._actors()
        known = [e[0] for e in self._locators.values()]
        same = len(known) == len(actors) and all(a is b for a, b in zip(known, actors))
        if same:
            return False
        self._locators = {}
        self._reset()
        for a in actors:                             # build now, not on the first mouse move
            self._locator(a)
        self._update()                               # the old lines and values go from the view too
        return True

    # ------------------------------------------------------------ state
    @property
    def has_items(self) -> bool:
        return bool(self.items)

    def _preview(self, item: Item) -> list:
        """The item's points, and - while it is unfinished - the mouse as its next point."""
        pts = list(item.points)
        if not item.complete and self.hover_point is not None and not self._dragging:
            pts.append(self.hover_point)
        return pts

    def current_values(self) -> Optional[dict]:
        """The numbers of the measurement the panel shows (as drawn, live while unfinished)."""
        if self.current is None:
            return None
        return shape_of(self.current.kind, self._preview(self.current), self.deltas).values

    # ------------------------------------------------------------ mouse
    def click(self, x: int, y: int):
        """A click (not a drag) at display position x, y: the next point."""
        self._grab = None
        hit = self._pick(x, y)
        if hit is None:
            return
        pos, kind = hit
        item = self.items[-1] if self.items and not self.items[-1].complete else None
        pts = (item.points if item else []) + [pos]
        if not is_valid(item.kind if item else self.mode, pts):
            return                                   # e.g. three points on one line: no circle
        if item is None:
            item = Item(self.mode)
            self.items.append(item)
        item.points.append(pos)
        self.current = item
        self.hover_point, self.hover_kind = pos, kind
        self._update()

    def hover(self, x: int, y: int):
        """The mouse moved over the view with no button down."""
        hit = self._pick(x, y)
        if hit is None:
            if self.hover_point is None:
                return
            self.hover_point = None
        else:
            if self.hover_point is not None and np.allclose(hit[0], self.hover_point):
                return
            self.hover_point, self.hover_kind = hit
        self._update()

    def leave(self):
        if self.hover_point is not None:
            self.hover_point = None
            self._update()

    # --- moving a placed point
    def grab(self, x: int, y: int) -> bool:
        """A press at x, y: is it on a placed point? Then a drag moves that point."""
        best, best_d = None, GRAB_PX
        m = np.array([x, y], dtype=float)
        for item in self.items:
            for i, p in enumerate(item.points):
                d = float(np.linalg.norm(np.array(self._to_screen(p)) - m))
                if d <= best_d:
                    best, best_d = (item, i), d
        self._grab = best
        return best is not None

    def drag_to(self, x: int, y: int):
        """The grabbed point follows the mouse (and snaps, like a new point)."""
        if self._grab is None:
            return
        item, i = self._grab
        self._dragging = True
        hit = self._pick(x, y)
        if hit is None:
            return
        pts = list(item.points)
        pts[i] = hit[0]
        if not is_valid(item.kind, pts):
            return
        item.points[i] = hit[0]
        self.current = item
        self.hover_point = None
        self._update()

    def drop(self):
        """The mouse button was let go after moving a point."""
        self._grab = None
        self._dragging = False
        self._update()

    # ------------------------------------------------------------ picking
    def _actors(self) -> list:
        return [a for a in self.scene.model_actors if a.GetVisibility()]

    def _locator(self, actor):
        mesh = actor.GetMapper().GetInput()
        ent = self._locators.get(id(actor))
        if ent is not None and ent[0] is actor and ent[1] is mesh:
            return ent[2]
        try:
            mesh.BuildLinks()                        # which triangles share an edge (see _is_edge)
        except Exception:   # noqa: BLE001 - without it there is simply no edge snapping
            pass
        loc = vtkStaticCellLocator()
        loc.SetDataSet(mesh)
        loc.AutomaticOn()
        loc.BuildLocator()
        self._locators[id(actor)] = (actor, mesh, loc)
        return loc

    def _to_screen(self, p) -> tuple:
        ren = self.p.renderer
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0)
        ren.WorldToDisplay()
        d = ren.GetDisplayPoint()
        return d[0], d[1]

    def _pick(self, x: int, y: int) -> Optional[tuple]:
        """(point, how) on the model under display position x, y, or None. `how` says what the
        point snapped to: "corner", "mid" (middle of an edge), "edge", or "free" (no snapping)."""
        actors = self._actors()
        if not actors:
            return None
        pk = self._picker
        pk.InitializePickList()
        pk.PickFromListOn()
        pk.RemoveAllLocators()
        for a in actors:
            pk.AddPickList(a)
            pk.AddLocator(self._locator(a))
        if not pk.Pick(x, y, 0, self.p.renderer) or pk.GetCellId() < 0 or pk.GetActor() is None:
            return None
        pos = np.array(pk.GetPickPosition(), dtype=float)
        if self.snap:
            snapped = self._snap(pk.GetActor(), pk.GetCellId(), x, y)
            if snapped is not None:
                return snapped
        return pos, "free"

    @staticmethod
    def _is_edge(mesh, cell_id: int, p1: int, p2: int) -> bool:
        """A real edge of the model: no triangle on its other side in the drawn mesh. The mesh is
        drawn with its sharp edges split apart, so those have no neighbour; the diagonals of a flat
        face and the edges inside a smooth curve do, and are not edges."""
        try:
            ids = vtkIdList()
            mesh.GetCellEdgeNeighbors(cell_id, p1, p2, ids)
            return ids.GetNumberOfIds() == 0
        except Exception:   # noqa: BLE001
            return False

    def _snap(self, actor, cell_id: int, x: int, y: int) -> Optional[tuple]:
        mesh = actor.GetMapper().GetInput()
        ids = vtkIdList()
        mesh.GetCellPoints(cell_id, ids)
        pids = [ids.GetId(i) for i in range(ids.GetNumberOfIds())]
        wp = [np.array(mesh.GetPoint(i), dtype=float) for i in pids]
        sp = [np.array(self._to_screen(p), dtype=float) for p in wp]
        m = np.array([x, y], dtype=float)
        # 1. a corner
        best = None
        for p, s in zip(wp, sp):
            d = float(np.linalg.norm(s - m))
            if d <= SNAP_PX and (best is None or d < best[0]):
                best = (d, p)
        if best is not None:
            return best[1], "corner"
        # 2. the middle of an edge, 3. the nearest point on an edge
        mid_best = edge_best = None
        n = len(pids)
        for i in range(n):
            j = (i + 1) % n
            if not self._is_edge(mesh, cell_id, pids[i], pids[j]):
                continue
            a, b, sa, sb = wp[i], wp[j], sp[i], sp[j]
            d = float(np.linalg.norm((sa + sb) / 2 - m))
            if d <= MID_PX and (mid_best is None or d < mid_best[0]):
                mid_best = (d, (a + b) / 2)
            seg = sb - sa
            l2 = float(np.dot(seg, seg))
            t = min(1.0, max(0.0, float(np.dot(m - sa, seg)) / l2)) if l2 > 1e-9 else 0.0
            d = float(np.linalg.norm(sa + t * seg - m))
            if d <= EDGE_PX and (edge_best is None or d < edge_best[0]):
                edge_best = (d, a + t * (b - a))
        if mid_best is not None:
            return mid_best[1], "mid"
        if edge_best is not None:
            return edge_best[1], "edge"
        return None

    # ------------------------------------------------------------ drawing
    def _ensure_overlay(self):
        if self._ren is not None:
            return
        ren = vtkRenderer()
        ren.SetLayer(1)
        ren.InteractiveOff()
        win = self.p.ren_win
        if win.GetNumberOfLayers() < 2:
            win.SetNumberOfLayers(2)
        win.AddRenderer(ren)
        main = self.p.renderer
        ren.SetActiveCamera(main.GetActiveCamera())
        # The small black dots get a renderer of their own above this one (layer 2, which starts
        # with a clean depth buffer): sphere points are round in depth too, so the big marker's
        # front would otherwise hide the dot in its middle.
        top = vtkRenderer()
        top.SetLayer(2)
        top.InteractiveOff()
        if win.GetNumberOfLayers() < 3:
            win.SetNumberOfLayers(3)
        win.AddRenderer(top)
        top.SetActiveCamera(main.GetActiveCamera())
        self._ren_top = top
        # Always look through the main view's camera, even if it is swapped for another one.
        main.AddObserver("StartEvent", lambda *_: (ren.SetActiveCamera(main.GetActiveCamera()),
                                                   top.SetActiveCamera(main.GetActiveCamera())))
        self._ren = ren

        self._mark_poly = vtkPolyData()
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(self._mark_poly)
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
        self._marks = vtkActor()
        self._marks.SetMapper(mapper)
        prop = self._marks.GetProperty()
        prop.SetRenderPointsAsSpheres(True)
        prop.SetPointSize(MARKER_PX)
        prop.LightingOff()
        self._marks.PickableOff()
        # A very small black dot in the middle of every marker: helps where the marker's colour
        # is close to the model's or the background's.
        self._core_poly = vtkPolyData()
        cmapper = vtkPolyDataMapper()
        cmapper.SetInputData(self._core_poly)
        cmapper.ScalarVisibilityOff()
        self._core = vtkActor()
        self._core.SetMapper(cmapper)
        cp = self._core.GetProperty()
        cp.SetColor(0.0, 0.0, 0.0)
        cp.SetRenderPointsAsSpheres(True)
        cp.SetPointSize(CORE_PX)
        cp.LightingOff()
        self._core.PickableOff()

        def line_actor(poly, width):
            lmapper = vtkPolyDataMapper()
            lmapper.SetInputData(poly)
            act = vtkActor()
            act.SetMapper(lmapper)
            lp = act.GetProperty()
            lp.SetColor(*(v / 255 for v in self._line_rgb))
            lp.SetLineWidth(width)
            lp.SetRenderLinesAsTubes(True)
            lp.SetOpacity(0.9)
            lp.LightingOff()
            act.PickableOff()
            ren.AddActor(act)
            return act

        self._lines_poly = vtkPolyData()
        self._lines = line_actor(self._lines_poly, self.drawn_width())
        # Keep the values from overlapping, also while the view turns.
        main.AddObserver("StartEvent", self._layout_labels)
        ren.AddActor(self._marks)
        top.AddActor(self._core)
        self._apply_dotted()
        ren.SetDraw(False)
        top.SetDraw(False)

    def _apply_dotted(self):
        """Dotted is drawn as many short dashes (VTK's own line stipple is not drawn by the
        OpenGL2 renderer), so redraw."""
        if self._lines is not None:
            self._draw()

    def _world_per_px(self, point) -> float:
        """How long one screen pixel is in world units at `point`."""
        ren = self.p.renderer
        cam = ren.GetActiveCamera()
        h = max(1, ren.GetSize()[1])
        if cam.GetParallelProjection():
            return 2.0 * cam.GetParallelScale() / h
        pos = np.array(cam.GetPosition())
        fwd = np.array(cam.GetFocalPoint()) - pos
        n = float(np.linalg.norm(fwd))
        depth = float(np.dot(np.asarray(point, float) - pos, fwd / n)) if n > 1e-12 else 1.0
        return 2.0 * max(depth, 1e-6) * math.tan(math.radians(cam.GetViewAngle()) / 2.0) / h

    def _dots(self, line) -> list:
        """A polyline as round dots: each as long as 0.3 line widths with 2.6 line widths between
        their starts, measured on the screen where the dot is (a list of polylines)."""
        pts = [np.asarray(q, float) for q in line]
        seg = [float(np.linalg.norm(pts[i + 1] - pts[i])) for i in range(len(pts) - 1)]
        total = sum(seg)
        if total <= 0:
            return []

        def at(d: float):                            # the point and the next vertex index at length d
            for i, l in enumerate(seg):
                if d <= l or i == len(seg) - 1:
                    t = 0.0 if l <= 0 else min(1.0, d / l)
                    return pts[i] + (pts[i + 1] - pts[i]) * t, i + 1
                d -= l
            return pts[-1], len(pts) - 1

        w = self.drawn_width()
        out, t = [], 0.0
        while t < total and len(out) < MAX_DOTS:
            start, i0 = at(t)
            px = self._world_per_px(start)
            end, i1 = at(min(t + DOT_LENGTH * w * px, total))
            out.append(np.array([start] + pts[i0:i1] + [end]))
            t += DOT_PERIOD * w * px
        return out

    def _view_signature(self) -> tuple:
        ren = self.p.renderer
        cam = ren.GetActiveCamera()
        return (tuple(round(v, 6) for v in cam.GetPosition()), tuple(round(v, 6) for v in cam.GetFocalPoint()),
                round(cam.GetViewAngle(), 4), round(cam.GetParallelScale(), 6), tuple(ren.GetSize()))

    def _rebuild_lines(self):
        """The lines as drawn: solid, or - dotted - as dots whose size follows the zoom."""
        if self._lines_poly is None:
            return
        lines = self._solid_src
        if self.dotted:
            lines = [d for line in lines for d in self._dots(line)]
            self._dots_for = self._view_signature()
        self._lines_data(self._lines_poly, lines)

    # --- the values: a rounded box with text, drawn by Qt and laid over the view as a picture
    def _scale(self) -> float:
        try:
            return float(self.p.interactor.devicePixelRatioF())
        except Exception:   # noqa: BLE001 - no Qt widget (tests)
            return 1.0

    def _label_picture(self, text: str):
        """(texture, width, height in pixels) of a value: its text on a box with rounded corners
        in the theme's colours. Made once per text."""
        scale = self._scale()
        key = (text, self._label_rgb, self._label_bg, scale)
        hit = self._label_cache.get(key)
        if hit is None:
            if len(self._label_cache) > 200:
                self._label_cache = {}
            hit = self._label_cache[key] = label_picture(text, self._label_rgb, self._label_bg, scale,
                                                         font_px=LABEL_FONT_PX, pad=LABEL_PAD, radius=LABEL_RADIUS)
        return hit

    def _label_actor(self, i: int):
        while len(self._labels) <= i:
            poly = vtkPolyData()
            pts = vtkPoints()
            for _ in range(4):
                pts.InsertNextPoint(0.0, 0.0, 0.0)
            poly.SetPoints(pts)
            cells = vtkCellArray()
            cells.InsertNextCell(4, [0, 1, 2, 3])
            poly.SetPolys(cells)
            tc = vtkFloatArray()
            tc.SetNumberOfComponents(2)
            for uv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                tc.InsertNextTuple2(*uv)
            poly.GetPointData().SetTCoords(tc)
            mapper = vtkPolyDataMapper2D()
            mapper.SetInputData(poly)
            a = vtkTexturedActor2D()
            a.SetMapper(mapper)
            a.PickableOff()
            self._ren.AddViewProp(a)
            self._labels.append(a)
            self._label_polys.append(poly)
        return self._labels[i]

    def _update(self):
        """Redraw, tell the panel, ask for a frame."""
        if self._ren is not None:
            self._draw()
        if self.on_change:
            self.on_change()
        self.request_render()

    @staticmethod
    def _lines_data(poly: vtkPolyData, polylines: list):
        pts = vtkPoints()
        cells = vtkCellArray()
        n = 0
        for line in polylines:
            if len(line) < 2:
                continue
            cells.InsertNextCell(len(line))
            for p in line:
                pts.InsertNextPoint(float(p[0]), float(p[1]), float(p[2]))
                cells.InsertCellPoint(n)
                n += 1
        poly.SetPoints(pts)
        poly.SetLines(cells)
        poly.Modified()

    def _draw(self):
        pts = vtkPoints()
        colors = vtkUnsignedCharArray()
        colors.SetNumberOfComponents(3)
        solid, labels = [], []
        for item in self.items:
            need = NEED[item.kind]
            for i, p in enumerate(item.points):
                pts.InsertNextPoint(float(p[0]), float(p[1]), float(p[2]))
                colors.InsertNextTuple3(*(START_RGB if i == 0 else END_RGB if i == need - 1 else MIDDLE_RGB))
            shape = shape_of(item.kind, self._preview(item), self.deltas)
            lines = [np.array(seg) for seg in shape.dist_lines] + list(shape.lines)
            for line in lines:
                solid.append(line)
            if shape.label is not None:
                labels.append(shape.label)
        # The mouse's marker: where a click would put the next point.
        if self.hover_point is not None and not self._dragging:
            h = self.hover_point
            pts.InsertNextPoint(float(h[0]), float(h[1]), float(h[2]))
            colors.InsertNextTuple3(*self._hover_rgb.get(self.hover_kind, self._hover_rgb["free"]))
        verts = vtkCellArray()
        for i in range(pts.GetNumberOfPoints()):
            verts.InsertNextCell(1)
            verts.InsertCellPoint(i)
        self._mark_poly.SetPoints(pts)
        self._mark_poly.SetVerts(verts)
        self._mark_poly.GetPointData().SetScalars(colors)
        self._mark_poly.Modified()
        self._core_poly.SetPoints(pts)
        self._core_poly.SetVerts(verts)
        self._core_poly.Modified()
        self._solid_src = solid
        self._rebuild_lines()
        items = []
        for i, (anchor, text) in enumerate(labels):
            a = self._label_actor(i)
            tex, w, h = self._label_picture(text)
            a.SetTexture(tex)
            a.SetVisibility(True)
            items.append((anchor, w, h))
        for a in self._labels[len(labels):]:
            a.SetVisibility(False)
        self._label_items = items
        self.label_texts = [t for _, t in labels]
        self._layout_labels()

    def _layout_labels(self, *_):
        """Put each value above its place on the screen; values that would sit on top of each
        other (the circles of one hole share their centre) are stacked so each stays readable.
        Runs before every frame, so it follows the view as it turns."""
        if self.dotted and self._ren is not None and self._dots_for != self._view_signature():
            self._rebuild_lines()                    # the dots keep their size on the screen
        placed = []
        scale = self._scale()
        gap = LABEL_GAP_PX * scale
        for i, (anchor, w, h) in enumerate(self._label_items):
            sx, sy = self._to_screen(anchor)
            x0, y0 = sx - w / 2, sy + LABEL_OFFSET_PX * scale
            for _ in range(len(self._label_items) + 1):
                hit = [r for r in placed if x0 < r[0] + r[2] and r[0] < x0 + w and y0 < r[1] + r[3] and r[1] < y0 + h]
                if not hit:
                    break
                y0 = max(r[1] + r[3] for r in hit) + gap
            placed.append((x0, y0, w, h))
            pts = self._label_polys[i].GetPoints()
            for k, (qx, qy) in enumerate(((x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h))):
                pts.SetPoint(k, qx, qy, 0.0)
            pts.Modified()
            self._label_polys[i].Modified()
        self.label_rects = placed

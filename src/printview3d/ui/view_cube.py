"""The view cube in the top-right corner of the 3D view, as in CAD programs and slicers.

  * Click a face         jump to that view (Top, Front, Right, Back, Left, Bottom)
  * Drag the cube        orbit, exactly like dragging in the 3D view
  * Drag the ring        turn around the vertical axis only (no tilt)
  * Arrows (on hover)    turn to the next 45° stop: < > around the model, ^ v up and down
  * Home (on hover)      back to the Iso view, fitted

How it is built: the cube lives in its own small VTK renderer, drawn on a second layer of the same
render window, in a fixed-size square in the corner. Before every frame its camera copies the
direction of the main camera, so the cube always shows how the scene is turned. It never moves
anything itself: TurntableControls asks it what is under the mouse (hit()) and does the orbit or
calls the view, so the cube rotates exactly like the 3D view does.

Look: see-through faces (only the three facing the camera are drawn, so the labels on the back
never shine through mirrored), thin edges, and a dashed ring. The arrows and the Home icon only
appear while the mouse is over the cube's square, so at rest the corner stays calm.

Colours come from the theme with one rule for every theme: the part under the mouse is filled with
the theme's primary colour (the slicer button's colour: amber in Ember, teal elsewhere), with
white or dark text, whichever reads better on it. The face labels are drawn with Qt (any language,
including Arabic) into textures.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkImageData, vtkPolyData
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkActor2D,
    vtkCoordinate,
    vtkPolyDataMapper,
    vtkPolyDataMapper2D,
    vtkRenderer,
    vtkTexture,
)

SIZE = 132              # size of the cube's corner square, in screen pixels (before HiDPI scaling)
MARGIN = 6              # gap to the corner of the 3D view
VIEW_SCALE = 1.27       # the cube camera's parallel scale: leaves room for the arrows around it
RING_Z = -0.62          # the ring lies just under the cube
RING_IN, RING_OUT = 0.80, 0.92      # the ring's hit zone; the dashes run along the middle of it
RING_DASHES = 16        # long dashes around the ring ...
DASH_FILL = 0.7         # ... each one 70 % dash, 30 % gap
FACE_ALPHA = 0.55       # see-through faces
HOVER_ALPHA = 0.92      # the face under the mouse is almost solid
EDGE_PX = 1.5           # line widths in screen pixels (before HiDPI scaling)
RING_PX = 1.5
HOME_PX = 1.5
TEX = 256               # texture size of one face
DARK_INK = "#1a1d21"    # dark text on a light hover colour

# The arrows and the Home icon, in the corner square's own coordinates: (0, 0) bottom-left,
# (1, 1) top-right. Each arrow sits ARROW_R from the centre and is 2 * ARROW_S wide.
ARROW_R, ARROW_S = 0.455, 0.05
ARROW_HIT = 0.075       # how close to an arrow's centre a click must be
ARROWS = {"arrow_up": 90, "arrow_down": 270, "arrow_left": 180, "arrow_right": 0}
HOME_BOX = (0.05, 0.80, 0.125, 0.875)      # u0, v0, u1, v1 (top-left corner)
HOME_HIT = 0.03         # extra room around the Home icon for the click
CONTROLS = tuple(ARROWS) + ("home",)

# Each face as seen from outside: its corners bottom-left, bottom-right, top-right, top-left, in the
# same orientation the camera has in Scene.set_view() for that view, so the label reads upright.
FACES = {
    "front":  [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5), (-.5, -.5, .5)],
    "right":  [(.5, -.5, -.5), (.5, .5, -.5), (.5, .5, .5), (.5, -.5, .5)],
    "back":   [(.5, .5, -.5), (-.5, .5, -.5), (-.5, .5, .5), (.5, .5, .5)],
    "left":   [(-.5, .5, -.5), (-.5, -.5, -.5), (-.5, -.5, .5), (-.5, .5, .5)],
    "top":    [(-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)],
    "bottom": [(.5, -.5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5), (.5, .5, -.5)],
}
# Which face a ray enters through: (axis, side) -> face
_SLAB_FACE = {(0, -1): "left", (0, 1): "right", (1, -1): "front", (1, 1): "back",
              (2, -1): "bottom", (2, 1): "top"}

_EDGES = [((-.5, -.5, -.5), (.5, -.5, -.5)), ((.5, -.5, -.5), (.5, .5, -.5)), ((.5, .5, -.5), (-.5, .5, -.5)),
          ((-.5, .5, -.5), (-.5, -.5, -.5)), ((-.5, -.5, .5), (.5, -.5, .5)), ((.5, -.5, .5), (.5, .5, .5)),
          ((.5, .5, .5), (-.5, .5, .5)), ((-.5, .5, .5), (-.5, -.5, .5)), ((-.5, -.5, -.5), (-.5, -.5, .5)),
          ((.5, -.5, -.5), (.5, -.5, .5)), ((.5, .5, -.5), (.5, .5, .5)), ((-.5, .5, -.5), (-.5, .5, .5))]


def _rgb(hex_color: str) -> tuple[float, float, float]:
    c = QColor(hex_color)
    return c.redF(), c.greenF(), c.blueF()


def _luminance(hex_color: str) -> float:
    """Relative luminance (WCAG), 0 = black, 1 = white."""
    c = QColor(hex_color)

    def lin(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(c.redF()) + 0.7152 * lin(c.greenF()) + 0.0722 * lin(c.blueF())


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio of two colours (1 = none, 21 = black on white)."""
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable_text(fill: str) -> str:
    """White or dark text, whichever reads better on the fill."""
    return "#ffffff" if contrast(fill, "#ffffff") >= contrast(fill, DARK_INK) else DARK_INK


def cube_colors(t: dict) -> dict:
    """The cube's colours in a theme. Plain faces like the toolbar buttons; edges, ring and arrows
    in the theme's teal; the part under the mouse in the theme's primary colour (amber in Ember,
    teal elsewhere) with white or dark text, whichever reads better."""
    light = QColor(t["window"]).lightnessF() > 0.5
    filled = t["view_bg"] != t["button"]
    hover = t["primary"]
    return {
        "face": t["base"] if light else t["button"],
        "text": t["accent_ink"] if light else t["text"],
        "edge": t["view_bg"] if filled else t["accent_ink"] if light else t["accent"],
        "hover": hover,
        "hover_text": readable_text(hover),
    }


def face_image(label: str, fill: str, text: str, edge: str, alpha: float = 1.0) -> np.ndarray:
    """One face as an RGBA picture (rows from the bottom up, as VTK textures expect). The fill is
    `alpha` see-through; the label and the border stay solid."""
    img = QImage(TEX, TEX, QImage.Format_RGBA8888)
    bg = QColor(fill)
    bg.setAlphaF(max(0.0, min(1.0, alpha)))
    img.fill(bg)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setPen(QPen(QColor(edge), 6))
    p.drawRect(QRectF(3, 3, TEX - 6, TEX - 6))
    font = QFont()
    font.setBold(True)
    size = 60.0
    font.setPixelSize(int(size))
    w = QFontMetricsF(font).horizontalAdvance(label)
    if w > TEX * 0.8:                                 # long words (German, Arabic) get smaller
        font.setPixelSize(max(20, int(size * TEX * 0.8 / w)))
    p.setFont(font)
    p.setPen(QColor(text))
    p.drawText(QRectF(0, 0, TEX, TEX), Qt.AlignCenter, label)
    p.end()
    arr = np.frombuffer(img.constBits(), np.uint8).reshape(TEX, img.bytesPerLine() // 4, 4)[:, :TEX]
    return np.ascontiguousarray(arr[::-1])


def _texture(arr: np.ndarray) -> vtkTexture:
    data = vtkImageData()
    data.SetDimensions(arr.shape[1], arr.shape[0], 1)
    scalars = numpy_to_vtk(arr.reshape(-1, 4), deep=True)
    scalars.SetNumberOfComponents(4)
    data.GetPointData().SetScalars(scalars)
    tex = vtkTexture()
    tex.SetInputData(data)
    tex.InterpolateOn()
    tex.MipmapOn()
    return tex


def _quad(corners) -> vtkPolyData:
    pts = vtkPoints()
    for c in corners:
        pts.InsertNextPoint(*c)
    cells = vtkCellArray()
    cells.InsertNextCell(4, [0, 1, 2, 3])
    poly = vtkPolyData()
    poly.SetPoints(pts)
    poly.SetPolys(cells)
    tc = numpy_to_vtk(np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32), deep=True)
    tc.SetName("tcoords")
    poly.GetPointData().SetTCoords(tc)
    return poly


def _lines(segments) -> vtkPolyData:
    pts = vtkPoints()
    cells = vtkCellArray()
    for a, b in segments:
        i = pts.InsertNextPoint(*a)
        j = pts.InsertNextPoint(*b)
        cells.InsertNextCell(2, [i, j])
    poly = vtkPolyData()
    poly.SetPoints(pts)
    poly.SetLines(cells)
    return poly


def dashed_ring(radius: float = (RING_IN + RING_OUT) / 2, z: float = RING_Z,
                dashes: int = RING_DASHES, fill: float = DASH_FILL, steps: int = 8) -> vtkPolyData:
    """The ring as `dashes` curved line pieces, each `fill` of its share of the circle."""
    pts = vtkPoints()
    cells = vtkCellArray()
    share = 2 * math.pi / dashes
    for k in range(dashes):
        a0 = k * share
        ids = []
        for s in range(steps + 1):
            a = a0 + share * fill * s / steps
            ids.append(pts.InsertNextPoint(radius * math.cos(a), radius * math.sin(a), z))
        cells.InsertNextCell(len(ids), ids)
    poly = vtkPolyData()
    poly.SetPoints(pts)
    poly.SetLines(cells)
    return poly


def arrow_triangle(name: str, grow: float = 1.0) -> list[tuple[float, float]]:
    """The arrow's three corners in the square's coordinates (tip first)."""
    a = math.radians(ARROWS[name])
    s = ARROW_S * grow
    ca, sa = math.cos(a), math.sin(a)
    tip = (0.5 + (ARROW_R + 0.6 * s) * ca, 0.5 + (ARROW_R + 0.6 * s) * sa)
    bx, by = 0.5 + (ARROW_R - 0.6 * s) * ca, 0.5 + (ARROW_R - 0.6 * s) * sa
    return [tip, (bx - sa * s, by + ca * s), (bx + sa * s, by - ca * s)]


def home_lines() -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """The Home icon (a little house) as line pieces in the square's coordinates."""
    u0, v0, u1, v1 = HOME_BOX
    w, h = u1 - u0, v1 - v0
    roof_l, peak, roof_r = (u0, v0 + 0.5 * h), (u0 + 0.5 * w, v1), (u1, v0 + 0.5 * h)
    wall_l, wall_r = u0 + 0.17 * w, u0 + 0.83 * w
    eave = v0 + 0.62 * h
    return [(roof_l, peak), (peak, roof_r),
            ((wall_l, eave), (wall_l, v0)), ((wall_l, v0), (wall_r, v0)), ((wall_r, v0), (wall_r, eave))]


def control_at(u: float, v: float) -> str | None:
    """The arrow or Home icon at (u, v) in the square's coordinates, or None."""
    u0, v0, u1, v1 = HOME_BOX
    if u0 - HOME_HIT <= u <= u1 + HOME_HIT and v0 - HOME_HIT <= v <= v1 + HOME_HIT:
        return "home"
    for name, ang in ARROWS.items():
        a = math.radians(ang)
        cx, cy = 0.5 + ARROW_R * math.cos(a), 0.5 + ARROW_R * math.sin(a)
        if math.hypot(u - cx, v - cy) <= ARROW_HIT:
            return name
    return None


def ray_hit(origin: np.ndarray, direction: np.ndarray) -> str | None:
    """What a ray from the camera hits first: a face name, 'ring', or None."""
    # Cube [-0.5, 0.5]^3 (slab method): the face it enters through.
    t_near, t_far, enter = -np.inf, np.inf, None
    for axis in range(3):
        d, o = direction[axis], origin[axis]
        if abs(d) < 1e-12:
            if o < -0.5 or o > 0.5:
                break
            continue
        t1, t2 = (-0.5 - o) / d, (0.5 - o) / d
        side = -1 if t1 < t2 else 1                      # entering through the -0.5 or +0.5 face
        lo, hi = min(t1, t2), max(t1, t2)
        if lo > t_near:
            t_near, enter = lo, (axis, side)
        t_far = min(t_far, hi)
    else:
        if t_near <= t_far and t_far >= 0 and enter is not None:
            return _SLAB_FACE[enter]
    # The ring around the base.
    if abs(direction[2]) > 1e-9:
        t = (RING_Z - origin[2]) / direction[2]
        if t >= 0:
            x, y = origin[0] + t * direction[0], origin[1] + t * direction[1]
            if RING_IN - 0.06 <= (x * x + y * y) ** 0.5 <= RING_OUT + 0.08:
                return "ring"
    return None


def _poly2d(points, polys=(), lines=()) -> vtkPolyData:
    pts = vtkPoints()
    for x, y in points:
        pts.InsertNextPoint(x, y, 0.0)
    poly = vtkPolyData()
    poly.SetPoints(pts)
    if polys:
        cells = vtkCellArray()
        for ids in polys:
            cells.InsertNextCell(len(ids), list(ids))
        poly.SetPolys(cells)
    if lines:
        cells = vtkCellArray()
        for ids in lines:
            cells.InsertNextCell(len(ids), list(ids))
        poly.SetLines(cells)
    return poly


def _actor2d(poly: vtkPolyData) -> vtkActor2D:
    """A flat overlay whose coordinates are the renderer's own 0..1 square."""
    coord = vtkCoordinate()
    coord.SetCoordinateSystemToNormalizedViewport()
    mapper = vtkPolyDataMapper2D()
    mapper.SetInputData(poly)
    mapper.SetTransformCoordinate(coord)
    actor = vtkActor2D()
    actor.SetMapper(mapper)
    return actor


class ViewCube:
    def __init__(self, plotter, colors: dict, labels: dict[str, str]):
        self.p = plotter
        self.ren_win = plotter.ren_win
        self.main = plotter.renderer
        self.ren = vtkRenderer()
        self.ren.SetLayer(1)
        self.ren.InteractiveOff()
        if self.ren_win.GetNumberOfLayers() < 2:
            self.ren_win.SetNumberOfLayers(2)
        self.ren_win.AddRenderer(self.ren)
        cam = self.ren.GetActiveCamera()
        cam.ParallelProjectionOn()
        cam.SetParallelScale(VIEW_SCALE)
        self.visible = True
        self.hover: str | None = None
        self.show_controls = False          # arrows + Home: only while the mouse is over the cube
        self.labels = dict(labels)
        self.tooltips: dict[str, str] = {}
        self.colors = cube_colors(colors)
        self._ratio = None

        self.face_actors: dict[str, vtkActor] = {}
        for name, corners in FACES.items():
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(_quad(corners))
            actor = vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetAmbient(0.85)
            prop.SetDiffuse(0.2)
            prop.SetSpecular(0.0)
            prop.BackfaceCullingOn()        # only the faces turned to the camera: no mirrored labels
            self.ren.AddActor(actor)
            self.face_actors[name] = actor

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(_lines(_EDGES))
        self.edges = vtkActor()
        self.edges.SetMapper(mapper)
        self.edges.GetProperty().LightingOff()
        self.ren.AddActor(self.edges)

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(dashed_ring())
        self.ring = vtkActor()
        self.ring.SetMapper(mapper)
        self.ring.GetProperty().LightingOff()
        self.ren.AddActor(self.ring)

        # Arrows and Home: flat overlays in the corner square, rebuilt when the hover changes.
        self.arrow_actors: dict[str, vtkActor2D] = {}
        for name in ARROWS:
            actor = _actor2d(_poly2d(arrow_triangle(name), polys=[(0, 1, 2)]))
            self.ren.AddViewProp(actor)
            self.arrow_actors[name] = actor
        pts, segs = [], []
        for a, b in home_lines():
            segs.append((len(pts), len(pts) + 1))
            pts += [a, b]
        self.home_actor = _actor2d(_poly2d(pts, lines=segs))
        self.ren.AddViewProp(self.home_actor)

        self._draw()
        self._apply_line_widths()
        # Follow the main camera before every frame (and keep the corner size fixed).
        self.main.AddObserver("StartEvent", self._sync)

    # ------------------------------------------------------------- appearance
    def set_colors(self, theme_colors: dict):
        self.colors = cube_colors(theme_colors)
        self._draw()

    def set_labels(self, labels: dict[str, str]):
        self.labels = dict(labels)
        self._draw_faces()

    def set_tooltips(self, tips: dict[str, str]):
        """Tooltips of the arrows and the Home icon (translated by the main window)."""
        self.tooltips = dict(tips)

    def _draw(self):
        self._draw_faces()
        self._draw_controls()

    def _draw_faces(self):
        c = self.colors
        for name, actor in self.face_actors.items():
            on = name == self.hover
            img = face_image(self.labels.get(name, name).upper(),
                             c["hover"] if on else c["face"], c["hover_text"] if on else c["text"],
                             c["edge"], HOVER_ALPHA if on else FACE_ALPHA)
            actor.SetTexture(_texture(img))
        self.edges.GetProperty().SetColor(*_rgb(c["edge"]))
        ring = self.ring.GetProperty()
        ring.SetColor(*_rgb(c["hover"] if self.hover == "ring" else c["edge"]))
        ring.SetOpacity(1.0 if self.hover == "ring" else 0.8)

    def _draw_controls(self):
        c = self.colors
        for name, actor in self.arrow_actors.items():
            on = name == self.hover
            actor.GetMapper().SetInputData(
                _poly2d(arrow_triangle(name, 1.3 if on else 1.0), polys=[(0, 1, 2)]))
            prop = actor.GetProperty()
            prop.SetColor(*_rgb(c["hover"] if on else c["edge"]))
            prop.SetOpacity(1.0 if on else 0.5)
            actor.SetVisibility(self.show_controls)
        prop = self.home_actor.GetProperty()
        on = self.hover == "home"
        prop.SetColor(*_rgb(c["hover"] if on else c["edge"]))
        prop.SetOpacity(1.0 if on else 0.85)
        self.home_actor.SetVisibility(self.show_controls)

    def _apply_line_widths(self):
        """Line widths are in device pixels: scale them for HiDPI screens."""
        ratio = self._device_ratio()
        if ratio == self._ratio:
            return
        self._ratio = ratio
        self.edges.GetProperty().SetLineWidth(EDGE_PX * ratio)
        self.ring.GetProperty().SetLineWidth(RING_PX * ratio)
        self.home_actor.GetProperty().SetLineWidth(HOME_PX * ratio)

    def set_hover(self, part: str | None, inside: bool | None = None) -> bool:
        """Highlight the face, ring, arrow or Home icon under the mouse; `inside` says whether the
        mouse is over the cube's square (then the arrows and Home show). True if anything changed."""
        show = self.show_controls if inside is None else bool(inside and self.visible)
        if part == self.hover and show == self.show_controls:
            return False
        faces_changed = part != self.hover and (part in FACES or self.hover in FACES
                                                or "ring" in (part, self.hover))
        self.hover = part
        self.show_controls = show
        if faces_changed:
            self._draw_faces()
        self._draw_controls()
        return True

    def set_visible(self, visible: bool):
        self.visible = visible
        self.ren.SetDraw(bool(visible))
        if not visible:
            self.hover = None
            self.show_controls = False
            self._draw()

    # ------------------------------------------------------------- geometry
    def _device_ratio(self) -> float:
        try:
            return float(self.p.interactor.devicePixelRatioF())
        except Exception:   # noqa: BLE001 - no Qt widget (tests)
            return 1.0

    def _corner(self) -> tuple[float, float, float, float]:
        """The cube's square in display pixels: (x0, y0, x1, y1), origin bottom-left."""
        w, h = self.ren_win.GetSize()
        ratio = self._device_ratio()
        s, m = SIZE * ratio, MARGIN * ratio
        return w - m - s, h - m - s, w - m, h - m

    def contains(self, x: float, y: float) -> bool:
        """Is display position (x, y) inside the cube's square (while the cube is shown)?"""
        if not self.visible:
            return False
        x0, y0, x1, y1 = self._corner()
        return x0 <= x <= x1 and y0 <= y <= y1

    def _sync(self, *_):
        w, h = self.ren_win.GetSize()
        if w <= 0 or h <= 0:
            return
        self._apply_line_widths()
        x0, y0, x1, y1 = self._corner()
        self.ren.SetViewport(max(0.0, x0 / w), max(0.0, y0 / h), x1 / w, y1 / h)
        main = self.main.GetActiveCamera()
        d = np.array(main.GetFocalPoint()) - np.array(main.GetPosition())
        n = float(np.linalg.norm(d))
        if n < 1e-12:
            return
        d /= n
        cam = self.ren.GetActiveCamera()
        cam.SetFocalPoint(0, 0, 0)
        cam.SetPosition(*(-d * 6))
        cam.SetViewUp(*main.GetViewUp())
        cam.SetClippingRange(1, 12)

    def hit(self, x: float, y: float) -> str | None:
        """What is at display position (x, y): a face ('top', 'front', ...), 'ring', an arrow
        ('arrow_up', 'arrow_down', 'arrow_left', 'arrow_right'), 'home', or None."""
        if not self.contains(x, y):
            return None
        x0, y0, x1, y1 = self._corner()
        control = control_at((x - x0) / max(x1 - x0, 1e-9), (y - y0) / max(y1 - y0, 1e-9))
        if control is not None:
            return control
        self._sync()
        ren = self.ren
        ren.SetDisplayPoint(x, y, 0.0)
        ren.DisplayToWorld()
        near = np.array(ren.GetWorldPoint()[:3]) / (ren.GetWorldPoint()[3] or 1.0)
        ren.SetDisplayPoint(x, y, 1.0)
        ren.DisplayToWorld()
        far = np.array(ren.GetWorldPoint()[:3]) / (ren.GetWorldPoint()[3] or 1.0)
        direction = far - near
        n = float(np.linalg.norm(direction))
        if n < 1e-12:
            return None
        return ray_hit(near, direction / n)

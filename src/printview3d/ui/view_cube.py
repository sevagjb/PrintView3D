"""The view cube in the top-right corner of the 3D view, as in CAD programs and slicers.

  * Click a face         jump to that view (Top, Front, Right, Back, Left, Bottom)
  * Drag the cube        orbit, exactly like dragging in the 3D view
  * Drag the ring        turn around the vertical axis only (no tilt)

How it is built: the cube lives in its own small VTK renderer, drawn on a second layer of the same
render window, in a fixed-size square in the corner. Before every frame its camera copies the
direction of the main camera, so the cube always shows how the scene is turned. It never moves
anything itself: TurntableControls asks it what is under the mouse (hit()) and does the orbit or
calls the view, so the cube rotates exactly like the 3D view does.

The face labels are drawn with Qt (any language, including Arabic) into textures. Colours come
from the theme, so the cube matches the toolbar buttons (teal in Ember Light).
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkImageData, vtkPolyData
from vtkmodules.vtkFiltersSources import vtkDiskSource
from vtkmodules.vtkRenderingCore import (vtkActor, vtkPolyDataMapper, vtkRenderer, vtkTexture)

SIZE = 118              # size of the cube's corner square, in screen pixels (before HiDPI scaling)
MARGIN = 6              # gap to the corner of the 3D view
RING_Z = -0.62          # the ring lies just under the cube
RING_IN, RING_OUT = 0.80, 0.92
TEX = 256               # texture size of one face

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


def cube_colors(t: dict) -> dict:
    """The cube's colours in a theme: plain faces like the toolbar buttons, the face under the
    mouse filled like the view buttons (teal + white text in Ember Light, the accent elsewhere)."""
    light = QColor(t["window"]).lightnessF() > 0.5
    filled = t["view_bg"] != t["button"]
    return {
        "face": t["base"] if light else t["button"],
        "text": t["accent_ink"] if light else t["text"],
        "edge": t["view_bg"] if filled else t["accent_ink"] if light else t["accent"],
        "hover": t["view_bg"] if filled else t["accent"],
        "hover_text": "#ffffff",
    }


def face_image(label: str, fill: str, text: str, edge: str) -> np.ndarray:
    """One face as an RGBA picture (rows from the bottom up, as VTK textures expect)."""
    img = QImage(TEX, TEX, QImage.Format_RGBA8888)
    img.fill(QColor(fill))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setPen(QPen(QColor(edge), 10))
    p.drawRect(QRectF(5, 5, TEX - 10, TEX - 10))
    font = QFont()
    font.setBold(True)
    size = 64.0
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
        cam.SetParallelScale(1.0)
        self.visible = True
        self.hover: str | None = None
        self.labels = dict(labels)
        self.colors = cube_colors(colors)

        self.face_actors: dict[str, vtkActor] = {}
        for name, corners in FACES.items():
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(_quad(corners))
            actor = vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetAmbient(0.78)
            prop.SetDiffuse(0.3)
            prop.SetSpecular(0.0)
            self.ren.AddActor(actor)
            self.face_actors[name] = actor

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(_lines(_EDGES))
        self.edges = vtkActor()
        self.edges.SetMapper(mapper)
        self.edges.GetProperty().SetLineWidth(2.0)
        self.edges.GetProperty().LightingOff()
        self.ren.AddActor(self.edges)

        disk = vtkDiskSource()
        disk.SetInnerRadius(RING_IN)
        disk.SetOuterRadius(RING_OUT)
        disk.SetCircumferentialResolution(96)
        disk.Update()
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(disk.GetOutputPort())
        self.ring = vtkActor()
        self.ring.SetMapper(mapper)
        self.ring.SetPosition(0, 0, RING_Z)
        self.ring.GetProperty().LightingOff()
        self.ren.AddActor(self.ring)

        self._draw_faces()
        # Follow the main camera before every frame (and keep the corner size fixed).
        self.main.AddObserver("StartEvent", self._sync)

    # ------------------------------------------------------------- appearance
    def set_colors(self, theme_colors: dict):
        self.colors = cube_colors(theme_colors)
        self._draw_faces()

    def set_labels(self, labels: dict[str, str]):
        self.labels = dict(labels)
        self._draw_faces()

    def _draw_faces(self):
        c = self.colors
        for name, actor in self.face_actors.items():
            on = name == self.hover
            img = face_image(self.labels.get(name, name).upper(),
                             c["hover"] if on else c["face"], c["hover_text"] if on else c["text"], c["edge"])
            actor.SetTexture(_texture(img))
        self.edges.GetProperty().SetColor(*_rgb(c["edge"]))
        ring = self.ring.GetProperty()
        ring.SetColor(*_rgb(c["hover"] if self.hover == "ring" else c["edge"]))
        ring.SetOpacity(1.0 if self.hover == "ring" else 0.55)

    def set_hover(self, part: str | None) -> bool:
        """Highlight the face (or ring) under the mouse. True if that changed."""
        if part == self.hover:
            return False
        self.hover = part
        self._draw_faces()
        return True

    def set_visible(self, visible: bool):
        self.visible = visible
        self.ren.SetDraw(bool(visible))
        if not visible:
            self.hover = None

    # ------------------------------------------------------------- geometry
    def _corner(self) -> tuple[float, float, float, float]:
        """The cube's square in display pixels: (x0, y0, x1, y1), origin bottom-left."""
        w, h = self.ren_win.GetSize()
        try:
            ratio = self.p.interactor.devicePixelRatioF()
        except Exception:   # noqa: BLE001 - no Qt widget (tests)
            ratio = 1.0
        s, m = SIZE * ratio, MARGIN * ratio
        return w - m - s, h - m - s, w - m, h - m

    def _sync(self, *_):
        w, h = self.ren_win.GetSize()
        if w <= 0 or h <= 0:
            return
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
        """The face ('top', 'front', ...) or 'ring' at display position (x, y), or None."""
        if not self.visible:
            return None
        x0, y0, x1, y1 = self._corner()
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            return None
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

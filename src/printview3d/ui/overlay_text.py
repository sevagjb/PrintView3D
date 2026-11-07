"""Text laid over the 3D view as small pictures.

The text is drawn with Qt (so every language, also right-to-left ones, comes out right and the
font is the program's own) and put on a flat quad over the view. Used for the values written next
to measurements, the hints at the bottom of the view and the numbers on the plate's grid.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.vtkCommonCore import vtkFloatArray, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkImageData, vtkPolyData
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper2D, vtkRenderer, vtkTexture, vtkTexturedActor2D

FONT_PX = 13                  # the text of a value or a hint
PAD = (7, 3)                  # space around the text inside its box (x, y)
RADIUS = 6                    # the box's rounded corners


def device_scale(plotter) -> float:
    """Screen pixels per Qt pixel (1 on a normal screen, 2 on many laptops)."""
    try:
        return float(plotter.interactor.devicePixelRatioF())
    except Exception:   # noqa: BLE001 - no Qt widget (tests)
        return 1.0


def wrap(text: str, max_px: float, scale: float = 1.0, font_px: int = FONT_PX) -> str:
    """Break `text` into lines at spaces so each is at most max_px wide (one long word stays whole,
    a break in the text stays a break)."""
    f = QFont()
    f.setWeight(QFont.DemiBold)
    f.setPixelSize(max(8, int(round(font_px * scale))))
    fm = QFontMetricsF(f)
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            trial = word if not line else line + " " + word
            if line and fm.horizontalAdvance(trial) > max_px:
                out.append(line)
                line = word
            else:
                line = trial
        out.append(line)
    return "\n".join(out)


def label_picture(text: str, fg: tuple, bg: Optional[tuple], scale: float = 1.0, font_px: int = FONT_PX,
                  pad: tuple = PAD, radius: float = RADIUS, alpha: float = 0.95,
                  first_bold: bool = True) -> tuple:
    """(texture, width, height) of `text` (lines apart by line breaks) in colour fg. With a
    background colour bg the text sits on a box with rounded corners; with None it is the bare
    text. The first line is semibold, the others a little smaller and regular."""
    lines = text.split("\n")
    fonts = []
    for i in range(len(lines)):
        f = QFont()
        f.setWeight(QFont.DemiBold if (i == 0 and first_bold) else QFont.Normal)
        f.setPixelSize(max(8, int(round(font_px * scale * (1.0 if i == 0 else 0.88)))))
        fonts.append(f)
    metrics = [QFontMetricsF(f) for f in fonts]
    px, py = pad[0] * scale, pad[1] * scale
    w = int(math.ceil(max(m.horizontalAdvance(t) for m, t in zip(metrics, lines)) + 2 * px))
    h = int(math.ceil(sum(m.height() for m in metrics) + 2 * py))
    img = QImage(w, h, QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    if bg is not None:
        box = QColor(*bg)
        box.setAlphaF(alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(box)
        p.drawRoundedRect(QRectF(0, 0, w, h), radius * scale, radius * scale)
    p.setPen(QColor(*fg))
    y = py
    for f, m, t in zip(fonts, metrics, lines):
        p.setFont(f)
        p.drawText(QRectF(0, y, w, m.height()), Qt.AlignHCenter | Qt.AlignVCenter, t)
        y += m.height()
    p.end()
    arr = np.frombuffer(img.constBits(), np.uint8).reshape(h, img.bytesPerLine() // 4, 4)[:, :w]
    arr = np.ascontiguousarray(arr[::-1])            # VTK textures run from the bottom row up
    data = vtkImageData()
    data.SetDimensions(w, h, 1)
    scalars = numpy_to_vtk(arr.reshape(-1, 4), deep=True)
    scalars.SetNumberOfComponents(4)
    data.GetPointData().SetScalars(scalars)
    tex = vtkTexture()
    tex.SetInputData(data)
    tex.InterpolateOn()
    return tex, w, h


class Sprites:
    """A pool of flat pictures on a renderer, placed by screen position (pixels from the
    bottom-left of the view)."""

    def __init__(self, renderer: vtkRenderer):
        self.ren = renderer
        self.actors: list = []
        self._polys: list = []

    def _make(self):
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
        self.ren.AddViewProp(a)
        self.actors.append(a)
        self._polys.append(poly)

    def put(self, i: int, tex, x0: float, y0: float, w: float, h: float):
        """Show picture `tex` as sprite i, its lower left corner at (x0, y0)."""
        while len(self.actors) <= i:
            self._make()
        a = self.actors[i]
        a.SetTexture(tex)
        a.SetVisibility(True)
        pts = self._polys[i].GetPoints()
        for k, (qx, qy) in enumerate(((x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h))):
            pts.SetPoint(k, qx, qy, 0.0)
        pts.Modified()
        self._polys[i].Modified()

    def hide_from(self, n: int):
        for a in self.actors[n:]:
            a.SetVisibility(False)

    def shown(self) -> int:
        return sum(1 for a in self.actors if a.GetVisibility())


def make_overlay(plotter) -> vtkRenderer:
    """A second renderer over the 3D view (layer 1, like the view cube) for flat pictures."""
    ren = vtkRenderer()
    ren.SetLayer(1)
    ren.InteractiveOff()
    win = plotter.ren_win
    if win.GetNumberOfLayers() < 2:
        win.SetNumberOfLayers(2)
    win.AddRenderer(ren)
    return ren


def _rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class HintOverlay:
    """Short instructions in the bottom centre of the 3D view, in the same boxes as the values
    written next to measurements. Several at once are stacked; long ones wrap to the view's width."""

    MARGIN_PX = 8                 # from the bottom edge
    GAP_PX = 6                    # between stacked hints

    def __init__(self, plotter, request_render=None):
        self.p = plotter
        self.request_render = request_render or plotter.render
        self.texts: list[str] = []
        self.rects: list = []     # where each hint sits: (x0, y0, w, h)
        self._fg = (255, 255, 255)
        self._bg = (15, 20, 25)
        self._cache: dict = {}
        self._ren = make_overlay(plotter)
        self.sprites = Sprites(self._ren)
        plotter.renderer.AddObserver("StartEvent", self._layout)

    def set_colors(self, t: dict):
        self._fg = _rgb(t["text"])
        self._bg = _rgb(t["window"])
        self._cache = {}
        self._layout()
        self.request_render()

    def set_texts(self, texts: list):
        texts = [t for t in texts if t]
        if texts == self.texts:
            return
        self.texts = texts
        self._layout()
        self.request_render()

    def _picture(self, text: str, scale: float, max_px: float):
        key = (text, scale, int(max_px), self._fg, self._bg)
        hit = self._cache.get(key)
        if hit is None:
            if len(self._cache) > 60:
                self._cache = {}
            hit = self._cache[key] = label_picture(wrap(text, max_px, scale), self._fg, self._bg, scale)
        return hit

    def _layout(self, *_):
        width = self.p.renderer.GetSize()[0]
        scale = device_scale(self.p)
        self.rects = []
        y = self.MARGIN_PX * scale
        for i, text in enumerate(self.texts):
            tex, w, h = self._picture(text, scale, max(120.0, width - 40 * scale - 2 * PAD[0] * scale))
            x0 = (width - w) / 2
            self.sprites.put(i, tex, x0, y, w, h)
            self.rects.append((x0, y, w, h))
            y += h + self.GAP_PX * scale
        self.sprites.hide_from(len(self.texts))

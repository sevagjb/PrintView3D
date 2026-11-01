"""Everything that draws into the 3D view (build plate, models, toolpaths)."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pyvista as pv

from ..loaders import FEATURES, GcodeData, ModelData
from ..loaders.gcode import TRAVEL
from . import theme

MODEL_COLORS = ["#4aa3df", "#f59f4c", "#69c66b", "#b98cff", "#ff6b6b", "#ffd166", "#3cc8c8", "#e88fc7"]


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


FEATURE_RGB = np.array([_hex_to_rgb(c) for _, _, c in FEATURES], dtype=np.uint8)


def _lines_polydata(a: np.ndarray, b: np.ndarray) -> pv.PolyData:
    """Build a PolyData of independent line segments a[i] -> b[i]."""
    n = len(a)
    pts = np.empty((2 * n, 3), dtype=np.float32)
    pts[0::2] = a
    pts[1::2] = b
    cells = np.empty((n, 3), dtype=np.int64)
    cells[:, 0] = 2
    cells[:, 1] = np.arange(0, 2 * n, 2)
    cells[:, 2] = cells[:, 1] + 1
    return pv.PolyData(pts, lines=cells.ravel())


class Scene:
    def __init__(self, plotter):
        self.p = plotter
        self.c = theme.colors()
        self.p.set_background(self.c["bg_bottom"], top=self.c["bg_top"])
        try:
            self.p.enable_anti_aliasing("fxaa")
        except Exception:
            pass
        try:
            self.p.add_axes(line_width=2, labels_off=False)
        except Exception:
            pass
        self.bed_visible = True
        self.focus_bounds: Optional[tuple] = None
        self.bed_bounds: Optional[tuple] = None
        self.model_actors: list = []
        self.gcode: Optional[GcodeData] = None
        self._bed_actor_names: list[str] = []
        self._bed_z = 0.0
        self._real_bed = True
        self._bed_from_below = None
        self._view = "iso"
        # Check before every frame whether the camera is under the plate.
        self.p.renderer.AddObserver("StartEvent", self._update_plate_side)
        self._color_axes()

    # ------------------------------------------------------------------ theme
    _BED_COLOR_KEYS = {"bed_plate": "plate", "bed_minor": "grid_minor", "bed_major": "grid_major"}

    def set_colors(self, c: dict):
        """Recolour background, plate and grid for a new theme (models and
        toolpaths keep their colours)."""
        self.c = c
        self.p.set_background(c["bg_bottom"], top=c["bg_top"])
        for name, key in self._BED_COLOR_KEYS.items():
            a = self.p.actors.get(name)
            if a is not None:
                a.GetProperty().SetColor(*(v / 255 for v in _hex_to_rgb(c[key])))
        a = self.p.actors.get("bed_edge")
        if a is not None:
            key = "plate_edge" if self._real_bed else "grid_major"
            a.GetProperty().SetColor(*(v / 255 for v in _hex_to_rgb(c[key])))
        self._color_axes()

    def _color_axes(self):
        """The small X/Y/Z marker in the corner: labels readable on any background."""
        axes = getattr(self.p.renderer, "axes_actor", None)
        if axes is None:
            return
        rgb = tuple(v / 255 for v in _hex_to_rgb(self.c["axes_label"]))
        try:
            for cap in (axes.GetXAxisCaptionActor2D(), axes.GetYAxisCaptionActor2D(),
                        axes.GetZAxisCaptionActor2D()):
                prop = cap.GetCaptionTextProperty()
                prop.SetColor(*rgb)
                prop.SetShadow(False)
        except AttributeError:
            pass

    # ------------------------------------------------------------------ basics
    def clear(self):
        for name in list(self.p.actors.keys()):
            self.p.remove_actor(name, render=False)
        # PyVista remembers the last mesh it drew (plotter.mesh / plotter.mapper). Without this,
        # a big G-code's toolpaths stay in memory after the file is closed or replaced.
        for attr in ("mesh", "mapper"):
            if getattr(self.p, attr, None) is not None:
                try:
                    setattr(self.p, attr, None)
                except (AttributeError, TypeError):
                    pass
        self.model_actors = []
        self.gcode = None
        self._bed_actor_names = []
        self.focus_bounds = None
        self.bed_bounds = None

    def render(self):
        self.p.render()

    # --------------------------------------------------------------- bed/grid
    def draw_bed(self, bounds: Optional[tuple], z: float = 0.0, has_real_bed: bool = True):
        for n in self._bed_actor_names:
            self.p.remove_actor(n, render=False)
        self._bed_actor_names = []
        self.bed_bounds = None
        if bounds is None:
            return
        xmin, xmax, ymin, ymax = bounds
        self.bed_bounds = (xmin, xmax, ymin, ymax, z, z)
        w, h = xmax - xmin, ymax - ymin

        plate = pv.Plane(center=((xmin + xmax) / 2, (ymin + ymax) / 2, z - 0.05),
                         direction=(0, 0, 1), i_size=w, j_size=h, i_resolution=1, j_resolution=1)
        self.p.add_mesh(plate, color=self.c["plate"], name="bed_plate", lighting=False,
                        pickable=False, reset_camera=False)

        step = 10.0
        big = max(w, h)
        if big > 600:
            step = 50.0
        elif big < 60:
            step = 5.0
        major_every = 5
        # Grid sits just under z so it never flickers against the model's bottom face.
        gz = z - 0.02
        minor_a, minor_b, major_a, major_b = [], [], [], []

        def add_line(ax, bx, major):
            (major_a if major else minor_a).append(ax)
            (major_b if major else minor_b).append(bx)

        for x in np.arange(math.ceil(xmin / step) * step, xmax + 1e-6, step):
            add_line((x, ymin, gz), (x, ymax, gz), int(round(x / step)) % major_every == 0)
        for y in np.arange(math.ceil(ymin / step) * step, ymax + 1e-6, step):
            add_line((xmin, y, gz), (xmax, y, gz), int(round(y / step)) % major_every == 0)

        if minor_a:
            self.p.add_mesh(_lines_polydata(np.array(minor_a), np.array(minor_b)), color=self.c["grid_minor"],
                            line_width=1, name="bed_minor", lighting=False, pickable=False, reset_camera=False)
        if major_a:
            self.p.add_mesh(_lines_polydata(np.array(major_a), np.array(major_b)), color=self.c["grid_major"],
                            line_width=1, name="bed_major", lighting=False, pickable=False, reset_camera=False)
        edge_a = np.array([(xmin, ymin, gz), (xmax, ymin, gz), (xmax, ymax, gz), (xmin, ymax, gz)])
        edge_b = np.roll(edge_a, -1, axis=0)
        self.p.add_mesh(_lines_polydata(edge_a, edge_b), color=self.c["plate_edge"] if has_real_bed else self.c["grid_major"],
                        line_width=2, name="bed_edge", lighting=False, pickable=False, reset_camera=False)
        self._bed_actor_names = ["bed_plate", "bed_minor", "bed_major", "bed_edge"]
        self._bed_z = z
        self._real_bed = has_real_bed
        self._bed_from_below = None
        self.set_bed_visible(self.bed_visible)

    def set_bed_visible(self, visible: bool):
        self.bed_visible = visible
        self._bed_from_below = None          # force re-evaluation below
        for n in self._bed_actor_names:
            a = self.p.actors.get(n)
            if a is not None:
                a.SetVisibility(visible)
        self._update_plate_side()

    def _update_plate_side(self, *_):
        """Hide the solid plate when looking at the model from below.

        Earlier versions made the plate semi-transparent, but transparency is
        drawn differently by different graphics drivers and on some (as on a
        real Windows laptop) the plate still covered the part. Hiding the
        plate surface and the fine grid lines - keeping only the outline and
        the main grid lines - works the same on every GPU.
        """
        if not self._bed_actor_names:
            return
        cam_z = self.p.renderer.GetActiveCamera().GetPosition()[2]
        below = cam_z < self._bed_z - 1e-3
        if below == self._bed_from_below:
            return
        self._bed_from_below = below
        hide_from_below = {"bed_plate", "bed_minor"}
        for n in self._bed_actor_names:
            a = self.p.actors.get(n)
            if a is not None:
                a.SetVisibility(self.bed_visible and not (below and n in hide_from_below))

    def pickable_actors(self) -> list:
        """Actors the mouse can 'grab' to choose the rotation centre."""
        out = [a for a in self.model_actors if a.GetVisibility()]
        for n in ("gcode", "travel"):
            a = self.p.actors.get(n)
            if a is not None and a.GetVisibility():
                out.append(a)
        return out

    def default_pivot(self):
        """Rotation centre when the mouse is not over the model: its centre."""
        b = self.focus_bounds or self.bed_bounds
        if not b:
            return None
        return ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2)

    # ------------------------------------------------- interaction quality
    def interaction_started(self):
        """Use cheaper drawing while the user is rotating/panning."""
        a = self.p.actors.get("gcode")
        if a is not None:
            a.GetProperty().SetRenderLinesAsTubes(False)
            a.GetProperty().SetLineWidth(1.5)

    def interaction_ended(self):
        a = self.p.actors.get("gcode")
        if a is not None:
            a.GetProperty().SetRenderLinesAsTubes(True)
            a.GetProperty().SetLineWidth(2.5)

    @staticmethod
    def _auto_bed(b: tuple, margin: float = 20.0) -> tuple:
        xmin, xmax, ymin, ymax = b[0], b[1], b[2], b[3]
        step = 10.0
        return (math.floor((xmin - margin) / step) * step, math.ceil((xmax + margin) / step) * step,
                math.floor((ymin - margin) / step) * step, math.ceil((ymax + margin) / step) * step)

    # ----------------------------------------------------------------- models
    def show_model(self, model: ModelData) -> list:
        """Draw all parts of a model. Returns the list of actors (one per part)."""
        self.model_actors = []
        for i, part in enumerate(model.parts):
            faces = np.hstack([np.full((len(part.faces), 1), 3, dtype=np.int64), part.faces]).ravel()
            mesh = pv.PolyData(part.vertices.astype(np.float32), faces=faces)
            style = dict(smooth_shading=True, split_sharp_edges=True, feature_angle=35, specular=0.25,
                         specular_power=20, name=f"part_{i}", reset_camera=False)
            if part.vertex_colors is not None and len(part.vertex_colors) == len(part.vertices):
                mesh.point_data["rgb"] = part.vertex_colors
                actor = self.p.add_mesh(mesh, scalars="rgb", rgb=True, **style)
            elif part.face_colors is not None and len(part.face_colors) == len(part.faces):
                mesh.cell_data["rgb"] = part.face_colors
                actor = self.p.add_mesh(mesh, scalars="rgb", rgb=True, **style)
            else:
                actor = self.p.add_mesh(mesh, color=self.part_color(part, i, len(model.parts)), **style)
            self.model_actors.append(actor)

        b = model.bounds()
        self.focus_bounds = b
        if model.bed:
            self.draw_bed(model.bed, 0.0, True)
        elif b:
            self.draw_bed(self._auto_bed(b), b[4], False)
        return self.model_actors

    @staticmethod
    def model_color(i: int, n: int) -> str:
        return MODEL_COLORS[i % len(MODEL_COLORS)] if n > 1 else MODEL_COLORS[0]

    @staticmethod
    def part_color(part, i: int, n: int) -> str:
        """The colour saved in the file, otherwise PrintView3D's own colour for part i of n.
        For parts coloured per vertex or face it is their average (for the objects list)."""
        if part.color:
            return part.color
        cols = part.vertex_colors if part.vertex_colors is not None else part.face_colors
        if cols is not None and len(cols):
            r, g, b = (int(c) for c in np.asarray(cols, dtype=np.float64).mean(axis=0))
            return f"#{r:02x}{g:02x}{b:02x}"
        return Scene.model_color(i, n)

    # ----------------------------------------------------------------- gcode
    def show_gcode(self, g: GcodeData):
        self.gcode = g
        b = g.extrusion_bounds
        self.focus_bounds = b
        if g.bed:
            self.draw_bed(g.bed, 0.0, True)
        elif b:
            self.draw_bed(self._auto_bed(b), 0.0, False)

    def update_gcode(self, max_layer: int, only_layer: bool, visible: np.ndarray):
        """Redraw toolpaths up to `max_layer`. `visible` is a bool per FEATURES entry."""
        g = self.gcode
        if g is None or g.n_layers == 0:
            return
        max_layer = max(0, min(max_layer, g.n_layers - 1))
        end = int(g.layer_end[max_layer])
        start = int(g.layer_end[max_layer - 1]) if (only_layer and max_layer > 0) else 0

        t = g.types[start:end]
        show = visible[t]
        is_travel = t == TRAVEL
        ext_idx = np.flatnonzero(show & ~is_travel) + start
        trv_idx = np.flatnonzero(show & is_travel) + start

        if len(ext_idx):
            poly = _lines_polydata(g.starts[ext_idx], g.ends[ext_idx])
            poly.cell_data["rgb"] = FEATURE_RGB[g.types[ext_idx]]
            self.p.add_mesh(poly, scalars="rgb", rgb=True, line_width=2.5, render_lines_as_tubes=True,
                            name="gcode", reset_camera=False, show_scalar_bar=False)
        else:
            self.p.remove_actor("gcode", render=False)

        if len(trv_idx):
            poly = _lines_polydata(g.starts[trv_idx], g.ends[trv_idx])
            self.p.add_mesh(poly, color=FEATURES[TRAVEL][2], line_width=1, opacity=0.45,
                            name="travel", reset_camera=False, lighting=False)
        else:
            self.p.remove_actor("travel", render=False)
        self.p.render()

    # ----------------------------------------------------------------- camera
    def set_view(self, view: str = "iso"):
        self._view = view
        b = self.focus_bounds or self.bed_bounds
        if b is None:
            self.p.view_isometric()
            return
        c = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
        size = max(b[1] - b[0], b[3] - b[2], b[5] - b[4], 1.0)
        d = size * 3
        if view == "top":
            pos, up = c + (0, 0, d), (0, 1, 0)
        elif view == "front":
            pos, up = c + (0, -d, 0), (0, 0, 1)
        elif view == "right":
            pos, up = c + (d, 0, 0), (0, 0, 1)
        # The other three come from the view cube.
        elif view == "back":
            pos, up = c + (0, d, 0), (0, 0, 1)
        elif view == "left":
            pos, up = c + (-d, 0, 0), (0, 0, 1)
        elif view == "bottom":
            pos, up = c - (0, 0, d), (0, 1, 0)
        else:  # iso: from the front-right, slightly above
            direction = np.array([0.65, -1.0, 0.75])
            pos, up = c + direction / np.linalg.norm(direction) * d, (0, 0, 1)
        self.p.camera_position = [tuple(pos), tuple(c), up]
        self.p.reset_camera(bounds=b)
        self.p.camera.zoom(0.95)
        self.p.reset_camera_clipping_range()
        self.p.render()

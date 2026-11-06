"""The Check button: overhangs, thin walls and problems in the mesh, coloured in the 3D view.

  * Overhangs: faces facing down that lean further from vertical than an angle (45° by default)
    usually need supports. Faces lying on the plate (the model's bottom) are not overhangs.
  * Thin walls: a short ray is cast from every face, straight into the model; when it meets the
    model's other side within the nozzle width (0.4 mm by default) the wall or pin there is
    thinner than one line of plastic. This runs in the background with progress.
  * Mesh check: open edges (holes: an edge with one face), non-manifold edges (an edge shared by
    more than two faces), flipped normals (faces turned the other way than their neighbours, or a
    closed part that is inside out) and loose parts (pieces not connected to the biggest one).

The analysis works on the parts as loaded (millimetres, triangles), with vertices at the same
place merged first, so a mesh written as separate triangles is still seen as one surface. The
highlights are extra actors on top of the model: its own colours stay as they are, and they
follow its cuts and its hidden objects.
"""

from __future__ import annotations

import math
import threading
from typing import Callable, Optional

import numpy as np
import pyvista as pv
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkCommonCore import reference
from vtkmodules.vtkCommonDataModel import vtkStaticCellLocator

OVERHANG_DEFAULT = 45.0          # degrees from vertical
NOZZLE_DEFAULT = 0.4             # mm
FLOOR_TOL = 0.05                 # mm: a face this close to the model's bottom lies on the plate
MERGE_TOL = 1e-5                 # mm: vertices closer than this are the same vertex

DEFAULT_COLORS = {
    "overhang": "#e5484d",       # red
    "thin": "#f59e0b",           # amber
    "open": "#ff3b30",           # open edges: bright red lines
    "nonmanifold": "#d946ef",    # magenta lines
    "flipped": "#3b82f6",        # blue faces
    "loose": "#facc15",          # yellow faces
}
MESH_KINDS = ("open", "nonmanifold", "flipped", "loose")


# ---------------------------------------------------------------- geometry (no VTK, no Qt)
def merge_vertices(vertices: np.ndarray, faces: np.ndarray, tol: float = MERGE_TOL) -> tuple:
    """(vertices, faces) with vertices at the same place (within tol) made one."""
    v = np.asarray(vertices, dtype=np.float64)
    keys = np.ascontiguousarray(np.round(v / tol).astype(np.int64))
    rows = keys.view(np.dtype((np.void, keys.dtype.itemsize * 3))).reshape(-1)    # one value per row
    _, first, inverse = np.unique(rows, return_index=True, return_inverse=True)
    return v[first], inverse.reshape(-1)[np.asarray(faces, dtype=np.int64)]


def face_normals(vertices: np.ndarray, faces: np.ndarray) -> tuple:
    """(unit normals, areas) of the triangles; degenerate triangles get a zero normal."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    length = np.linalg.norm(n, axis=1)
    out = np.zeros_like(n)
    ok = length > 1e-12
    out[ok] = n[ok] / length[ok, None]
    return out, length / 2


def overhang_faces(vertices, faces, angle_deg: float = OVERHANG_DEFAULT, floor_z: Optional[float] = None,
                   tol: float = FLOOR_TOL) -> np.ndarray:
    """Which faces are overhangs: facing down and leaning further than angle_deg from vertical
    (a flat ceiling leans 90°, a wall 0°). Faces lying on the floor (all three corners within tol
    of floor_z, the model's bottom) rest on the plate and are not overhangs."""
    v = np.asarray(vertices, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    if not len(f):
        return np.zeros(0, dtype=bool)
    n, _ = face_normals(v, f)
    # leaning angle from vertical, for a face facing down: asin(-n_z)
    over = -n[:, 2] > math.sin(math.radians(max(0.0, min(89.9, angle_deg))))
    if floor_z is None:
        floor_z = float(v[:, 2].min())
    on_floor = (v[f][:, :, 2] <= floor_z + tol).all(axis=1)
    return over & ~on_floor


def _edges(faces: np.ndarray) -> np.ndarray:
    """Every face's three edges as directed (a, b) pairs, face by face."""
    f = np.asarray(faces, dtype=np.int64)
    return np.stack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1).reshape(-1, 2)


def components(n_vertices: int, faces: np.ndarray) -> np.ndarray:
    """The connected piece every face belongs to (0, 1, ...; pieces touching at a vertex are
    one). Union-find with pointer jumping, in numpy."""
    f = np.asarray(faces, dtype=np.int64)
    parent = np.arange(n_vertices, dtype=np.int64)
    e = _edges(f)
    a, b = e[:, 0], e[:, 1]
    while True:
        pa, pb = parent[a], parent[b]
        lo, hi = np.minimum(pa, pb), np.maximum(pa, pb)
        before = parent.copy()
        np.minimum.at(parent, hi, lo)
        while True:                                     # point every vertex at its root
            nxt = parent[parent]
            if np.array_equal(nxt, parent):
                break
            parent = nxt
        if np.array_equal(parent, before):
            break
    roots = parent[f[:, 0]]
    _, piece = np.unique(roots, return_inverse=True)
    return piece.reshape(-1)


LOOSE_DEFAULT = 5.0              # mm: a loose piece is at most this big (its longest side)
ZERO_AREA = 1e-9                 # mm²: a triangle this small is a sliver with no surface


def mesh_report(vertices, faces, loose_max: float = LOOSE_DEFAULT) -> dict:
    """What is wrong with a mesh (after merging vertices at the same place):
    open: (k, 2, 3) open edges (edges with one face) as point pairs; nonmanifold: the same for
    edges shared by more than two faces; flipped: bool per face (turned against a neighbour, or
    part of a closed piece that is inside out); loose: bool per face (in a small piece, at most
    loose_max mm across, that is not the biggest and not inside another piece); pieces: the
    number of pieces; inside_out: closed pieces turned inside out; slivers: triangles without
    area.

    Triangles without area (slivers: three corners on one line, or two in the same place) are
    common in exported meshes and invisible. They still close the surface, so they count for
    open edges, but not for the other checks: there they only gave invisible "problems".
    A closed piece inside another one with its normals pointing inwards is a cavity (the inside
    of a hollow part), not an inside-out piece, and not a loose one."""
    v, f = merge_vertices(vertices, faces)
    nf = len(f)
    report = {"open": np.zeros((0, 2, 3)), "nonmanifold": np.zeros((0, 2, 3)),
              "flipped": np.zeros(nf, dtype=bool), "loose": np.zeros(nf, dtype=bool),
              "pieces": 0, "inside_out": 0, "slivers": 0}
    if not nf:
        return report
    _, area = face_normals(v, f)
    solid = area > ZERO_AREA                          # faces with a surface
    report["slivers"] = int((~solid).sum())
    directed = _edges(f)
    face_of = np.repeat(np.arange(nf), 3)
    nv = np.int64(len(v))
    und = np.sort(directed, axis=1)
    # Edges as one number each (a * n + b): unique on numbers is much faster than on rows.
    ukey, inv, cnt = np.unique(und[:, 0] * nv + und[:, 1], return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    pairs = np.column_stack([ukey // nv, ukey % nv])
    report["open"] = v[pairs[cnt == 1]]
    # Only faces with a surface count for shared edges and their direction.
    on_solid = solid[face_of]
    cnt_solid = np.bincount(inv[on_solid], minlength=len(ukey))
    report["nonmanifold"] = v[pairs[cnt_solid > 2]]
    # Two faces that run along a shared edge in the same direction face opposite ways.
    dkey = directed[:, 0] * nv + directed[:, 1]
    _, dinv, dcnt = np.unique(dkey[on_solid], return_inverse=True, return_counts=True)
    same_way = np.zeros(len(dkey), dtype=bool)
    same_way[np.flatnonzero(on_solid)] = dcnt[dinv.reshape(-1)] > 1
    flipped = np.zeros(nf, dtype=bool)
    flipped[face_of[same_way & (cnt_solid[inv] == 2)]] = True
    # Pieces, their size, place and volume.
    piece = components(len(v), f)
    n_pieces = int(piece.max()) + 1
    report["pieces"] = n_pieces
    fv = v[f]
    lo = np.full((n_pieces, 3), np.inf)
    hi = np.full((n_pieces, 3), -np.inf)
    np.minimum.at(lo, piece, fv.min(axis=1))
    np.maximum.at(hi, piece, fv.max(axis=1))
    p0, p1, p2 = fv[:, 0], fv[:, 1], fv[:, 2]
    vol = np.bincount(piece, weights=np.einsum("ij,ij->i", p0, np.cross(p1, p2)) / 6.0, minlength=n_pieces)
    open_piece = np.zeros(n_pieces, dtype=bool)
    open_piece[np.unique(piece[face_of[cnt[inv] == 1]])] = True
    # inside another piece: its box lies within the box of a piece with more volume
    inside = np.zeros(n_pieces, dtype=bool)
    eps = 1e-6
    for i in range(n_pieces):
        others = (np.abs(vol) > abs(vol[i])) & (lo <= lo[i] + eps).all(axis=1) & (hi >= hi[i] - eps).all(axis=1)
        others[i] = False
        inside[i] = bool(others.any())
    # A closed piece with a negative volume is inside out - unless it is a cavity in another piece.
    inside_out = (vol < 0) & ~open_piece & ~inside
    report["inside_out"] = int(inside_out.sum())
    flipped |= inside_out[piece]
    report["flipped"] = flipped & solid
    # Loose: small pieces on their own, away from the biggest one.
    if n_pieces > 1:
        biggest = int(np.argmax(np.bincount(piece, weights=area, minlength=n_pieces)))
        small = (hi - lo).max(axis=1) <= loose_max
        loose_piece = small & ~inside
        loose_piece[biggest] = False
        report["loose"] = loose_piece[piece]
    return report


def thin_faces(vertices, faces, width: float = NOZZLE_DEFAULT, progress: Optional[Callable[[float], None]] = None,
               cancelled: Optional[Callable[[], bool]] = None) -> Optional[np.ndarray]:
    """Which faces lie on a wall or pin thinner than `width` (mm): a ray from the face's centre
    straight into the model meets its other side within `width`. None when cancelled."""
    v, f = merge_vertices(vertices, faces)
    nf = len(f)
    thin = np.zeros(nf, dtype=bool)
    if not nf:
        return thin
    n, area = face_normals(v, f)
    centre = v[f].mean(axis=1)
    mesh = pv.PolyData(v, faces=np.hstack([np.full((nf, 1), 3), f]).ravel())
    loc = vtkStaticCellLocator()
    loc.SetDataSet(mesh)
    loc.BuildLocator()
    eps = max(1e-4, width * 1e-3)
    t, sub, cell = reference(0.0), reference(0), reference(0)
    x, pc = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    step = max(1, nf // 100)
    for i in range(nf):
        if area[i] <= 0:
            continue
        a = centre[i] - n[i] * eps
        b = centre[i] - n[i] * width
        if loc.IntersectWithLine(a, b, 1e-9, t, x, pc, sub, cell) and int(cell) != i:
            thin[i] = True
        if i % step == 0:
            if cancelled is not None and cancelled():
                return None
            if progress is not None:
                progress(i / nf)
    if progress is not None:
        progress(1.0)
    return thin


# ---------------------------------------------------------------- the highlights in the 3D view
class _Signals(QObject):
    thin_done = Signal(int, object)        # token, list of masks per part (or None)
    thin_progress = Signal(int, float)
    mesh_done = Signal(int, object)        # token, list of mesh reports per part


BACKGROUND_FACES = 200_000      # a mesh check on more faces than this runs in the background


def _hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


class PrintCheck:
    """Keeps the analyses of the model on screen and the actors that show them."""

    def __init__(self, plotter, scene, on_change: Optional[Callable[[], None]] = None,
                 request_render: Optional[Callable[[], None]] = None):
        self.p = plotter
        self.scene = scene
        self.on_change = on_change
        self.request_render = request_render or plotter.render
        self.parts: list = []                # the model's parts (MeshPart)
        self.active = False                  # the Check section is open
        self.show = {"overhang": True, "thin": False, **{k: True for k in MESH_KINDS}}
        self.colors = dict(DEFAULT_COLORS)
        self.angle = OVERHANG_DEFAULT
        self.nozzle = NOZZLE_DEFAULT
        self.loose_max = LOOSE_DEFAULT
        self.reports: list = []              # mesh_report per part
        self.overhangs: list = []            # mask per part
        self.thin: Optional[list] = None     # mask per part, None while not (yet) known
        self.thin_progress: Optional[float] = None
        self._token = 0
        self._actors: dict = {}              # name -> actor
        self._signals = _Signals()
        self._signals.thin_done.connect(self._thin_done)
        self._signals.thin_progress.connect(self._thin_step)
        self._signals.mesh_done.connect(self._mesh_done)
        self.mesh_busy = False
        self._mesh_token = 0
        plotter.renderer.AddObserver("StartEvent", self._sync)

    # --- the model
    def set_model(self, parts: list):
        """A new model (or none): forget everything about the old one."""
        self._token += 1
        self._mesh_token += 1
        self.mesh_busy = False
        self.parts = list(parts or [])
        self.reports, self.overhangs, self.thin, self.thin_progress = [], [], None, None
        self._remove_actors()
        if self.active:
            self.analyse()

    def set_active(self, on: bool):
        self.active = bool(on)
        if self.active:
            self.analyse()
        else:
            self._token += 1                 # a thin-wall run still going is not wanted any more
            self.thin_progress = None
            self._remove_actors()
            self._changed()

    def analyse(self):
        """Overhangs and the mesh check now (fast), thin walls in the background if wanted."""
        floor = min((float(p.vertices[:, 2].min()) for p in self.parts if len(p.vertices)), default=0.0)
        self.overhangs = [overhang_faces(p.vertices, p.faces, self.angle, floor) for p in self.parts]
        if len(self.reports) != len(self.parts) and not self.mesh_busy:
            if sum(len(p.faces) for p in self.parts) <= BACKGROUND_FACES:
                self.reports = [mesh_report(p.vertices, p.faces, self.loose_max) for p in self.parts]
            else:
                self._start_mesh()
        if self.show["thin"] and self.thin is None and self.thin_progress is None:
            self.start_thin()
        self._draw()

    # --- options
    def set_angle(self, deg: float):
        self.angle = float(deg)
        if self.active:
            self.analyse()

    def set_nozzle(self, mm: float):
        self.nozzle = float(mm)
        self.thin = None
        self._token += 1
        self.thin_progress = None
        if self.active:
            self.analyse()

    def set_loose_max(self, mm: float):
        """Loose parts are pieces up to this size (mm, their longest side): the mesh check again."""
        self.loose_max = float(mm)
        self._mesh_token += 1
        self.mesh_busy = False
        self.reports = []
        if self.active:
            self.analyse()

    def set_shown(self, kind: str, on: bool):
        self.show[kind] = bool(on)
        if self.active:
            self.analyse()

    def set_color(self, kind: str, color: str):
        self.colors[kind] = color
        if self.active:
            self._draw()

    # --- thin walls, in the background
    def start_thin(self):
        self._token += 1
        token = self._token
        parts = [(p.vertices.copy(), p.faces.copy()) for p in self.parts]
        width = self.nozzle
        total = max(1, sum(len(f) for _, f in parts))
        self.thin_progress = 0.0
        self._changed()

        def work():
            masks, done = [], 0
            for v, f in parts:
                def step(frac, done=done, nf=len(f)):
                    self._signals.thin_progress.emit(token, (done + frac * nf) / total)
                m = thin_faces(v, f, width, step, lambda: token != self._token)
                if m is None:
                    return
                masks.append(m)
                done += len(f)
            self._signals.thin_done.emit(token, masks)

        threading.Thread(target=work, daemon=True).start()

    def _start_mesh(self):
        self._mesh_token += 1
        token = self._mesh_token
        parts = [(p.vertices.copy(), p.faces.copy()) for p in self.parts]
        self.mesh_busy = True
        loose_max = self.loose_max

        def work():
            self._signals.mesh_done.emit(token, [mesh_report(v, f, loose_max) for v, f in parts])

        threading.Thread(target=work, daemon=True).start()

    def _mesh_done(self, token: int, reports):
        if token != self._mesh_token:
            return
        self.reports, self.mesh_busy = reports, False
        if self.active:
            self._draw()

    def _thin_step(self, token: int, frac: float):
        if token == self._token:
            self.thin_progress = frac
            self._changed()

    def _thin_done(self, token: int, masks):
        if token != self._token:
            return
        self.thin, self.thin_progress = masks, None
        if self.active:
            self._draw()

    def wait_for_thin(self, timeout: float = 60.0):
        """Tests: compute thin walls right away (in this thread)."""
        self._token += 1
        self.thin = [thin_faces(p.vertices, p.faces, self.nozzle) for p in self.parts]
        self.thin_progress = None
        if self.active:
            self._draw()

    # --- counts for the side panel
    def counts(self) -> dict:
        c = {"overhang": int(sum(int(m.sum()) for m in self.overhangs)),
             "thin": None if self.thin is None else int(sum(int(m.sum()) for m in self.thin)),
             "open": sum(len(r["open"]) for r in self.reports),
             "nonmanifold": sum(len(r["nonmanifold"]) for r in self.reports),
             "flipped": int(sum(int(r["flipped"].sum()) for r in self.reports)),
             "loose": sum(max(0, r["pieces"] - 1) for r in self.reports)}
        if self.mesh_busy:                   # not known yet
            for k in MESH_KINDS:
                c[k] = None
        return c

    # --- drawing
    def _remove_actors(self):
        for name in list(self._actors):
            if name in self.p.actors:
                self.p.remove_actor(name, render=False)
        self._actors = {}

    def _add_faces(self, name: str, part, mask, color: str):
        if mask is None or not mask.any():
            return
        f = np.asarray(part.faces, dtype=np.int64)[mask]
        mesh = pv.PolyData(np.asarray(part.vertices, dtype=np.float32),
                           faces=np.hstack([np.full((len(f), 1), 3), f]).ravel())
        a = self.p.add_mesh(mesh, color=color, name=name, reset_camera=False, pickable=False,
                            lighting=True, show_scalar_bar=False)
        m = a.GetMapper()
        m.SetResolveCoincidentTopologyToPolygonOffset()
        m.SetRelativeCoincidentTopologyPolygonOffsetParameters(-1.5, -4.0)
        a.SetUseBounds(False)
        self._actors[name] = a

    def _add_edges(self, name: str, pairs: np.ndarray, color: str):
        if not len(pairs):
            return
        pts = pairs.reshape(-1, 3).astype(np.float32)
        cells = np.column_stack([np.full(len(pairs), 2), np.arange(0, 2 * len(pairs), 2),
                                 np.arange(1, 2 * len(pairs), 2)]).ravel()
        a = self.p.add_mesh(pv.PolyData(pts, lines=cells), color=color, name=name, line_width=3,
                            render_lines_as_tubes=True, lighting=False, reset_camera=False, pickable=False,
                            show_scalar_bar=False)
        a.SetUseBounds(False)
        self._actors[name] = a

    def _draw(self):
        self._remove_actors()
        if self.active:
            for i, part in enumerate(self.parts):
                if self.show["overhang"] and i < len(self.overhangs):
                    self._add_faces(f"check_overhang_{i}", part, self.overhangs[i], self.colors["overhang"])
                if self.show["thin"] and self.thin is not None and i < len(self.thin):
                    self._add_faces(f"check_thin_{i}", part, self.thin[i], self.colors["thin"])
                if i >= len(self.reports):
                    continue
                r = self.reports[i]
                # flipped / loose are masks over the merged mesh's faces: the same order as the part's
                for kind in ("loose", "flipped"):
                    if self.show[kind]:
                        self._add_faces(f"check_{kind}_{i}", part, r[kind], self.colors[kind])
                for kind in ("open", "nonmanifold"):
                    if self.show[kind]:
                        self._add_edges(f"check_{kind}_{i}", r[kind], self.colors[kind])
        self._sync()
        self._changed()

    def _sync(self, *_):
        """Before every frame: a highlight is shown while its object is, and is cut by the cuts."""
        if not self._actors:
            return
        actors = self.scene.model_actors
        planes = self.scene._model_planes() if hasattr(self.scene, "_model_planes") else []
        for name, a in self._actors.items():
            i = int(name.rsplit("_", 1)[1])
            visible = i < len(actors) and bool(actors[i].GetVisibility())
            if bool(a.GetVisibility()) != visible:
                a.SetVisibility(visible)
            m = a.GetMapper()
            have = [m.GetClippingPlanes().GetItem(k) for k in range(m.GetNumberOfClippingPlanes())] \
                if m.GetClippingPlanes() is not None else []
            if have != planes:
                m.RemoveAllClippingPlanes()
                for pl in planes:
                    m.AddClippingPlane(pl)

    def _changed(self):
        if self.on_change:
            self.on_change()
        self.request_render()

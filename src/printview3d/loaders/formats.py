"""Readers for general 3D formats: OBJ, PLY, OFF and glTF / GLB.

Like the STL and 3MF readers they return a ModelData (named parts made of
vertices + triangles) and need nothing beyond numpy. Colours stored in the
file are kept (OBJ materials and vertex colours, PLY and OFF colours, glTF
materials and vertex colours); textures are not read.

Units: OBJ, PLY and OFF have none; their numbers are taken as millimetres,
the convention of 3D printing. glTF is defined in metres with Y pointing up,
so it is turned into millimetres with Z up (unless the numbers are clearly
millimetres already, see _gltf_scale).
"""

from __future__ import annotations

import base64
import json
import os
import re
import struct
from typing import Callable, Optional

import numpy as np

from .mesh import MeshPart, ModelData

Progress = Optional[Callable[[float], None]]


# ==========================================================================
# helpers
# ==========================================================================
def _name(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]


def _hex(rgb) -> str:
    r, g, b = (int(max(0, min(255, round(float(c))))) for c in rgb[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _to_u8(colors: np.ndarray) -> np.ndarray:
    """Colours as 0..255 bytes, whether the file wrote 0..1 floats or 0..255 numbers."""
    c = np.asarray(colors, dtype=np.float64)[:, :3]
    if c.size and c.max() <= 1.0:
        c = c * 255.0
    return np.clip(np.rint(c), 0, 255).astype(np.uint8)


def _fan(polys: list[list[int]]) -> np.ndarray:
    """Polygons (lists of vertex indices) -> triangles, as a fan from the first corner."""
    tris = []
    for p in polys:
        for k in range(1, len(p) - 1):
            tris.append((p[0], p[k], p[k + 1]))
    return np.array(tris, dtype=np.int64).reshape(-1, 3)


def _compact(vertices: np.ndarray, faces: np.ndarray, vcolors=None):
    """Keep only the vertices the faces use (parts share one vertex list in OBJ/glTF)."""
    used, inverse = np.unique(faces.ravel(), return_inverse=True)
    v = vertices[used]
    vc = vcolors[used] if vcolors is not None else None
    return v.astype(np.float32), inverse.reshape(-1, 3).astype(np.int64), vc


def _check(model: ModelData, what: str) -> ModelData:
    model.parts = [p for p in model.parts if len(p.faces)]
    if not model.parts:
        raise ValueError(f"This {what} file contains no triangles (only points or lines, or it is empty).")
    # When the file colours some parts, the others (for example textured ones) are neutral grey
    # rather than PrintView3D's own part colours.
    if any(p.color or p.vertex_colors is not None or p.face_colors is not None for p in model.parts):
        for p in model.parts:
            if not (p.color or p.vertex_colors is not None or p.face_colors is not None):
                p.color = _hex(_DEFAULT_RGB)
    return model


def _solid_or_none(colors: Optional[np.ndarray]) -> tuple[Optional[str], Optional[np.ndarray]]:
    """One colour for the whole part when every element has the same colour."""
    if colors is None or not len(colors):
        return None, None
    if (colors == colors[0]).all():
        return _hex(colors[0]), None
    return None, colors


# ==========================================================================
# OBJ (Wavefront)
# ==========================================================================
def _read_mtl(path: str) -> dict[str, str]:
    """Material name -> diffuse colour (Kd) from a .mtl file; missing files are fine."""
    colors: dict[str, str] = {}
    try:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return colors
    current = None
    for line in text.splitlines():
        t = line.strip().split()
        if not t:
            continue
        if t[0] == "newmtl" and len(t) > 1:
            current = " ".join(t[1:])
        elif t[0] == "Kd" and current is not None and len(t) >= 4:
            try:
                colors[current] = _hex([float(x) * 255 for x in t[1:4]])
            except ValueError:
                pass
    return colors


def load_obj(path: str, progress: Progress = None) -> ModelData:
    with open(path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    folder = os.path.dirname(os.path.abspath(path))

    verts: list[list[float]] = []
    vcols: list[list[float]] = []
    materials: dict[str, str] = {}
    # parts in file order: name -> {"polys": [...], "mats": [...]}
    parts: dict[str, dict] = {}
    obj_name = None       # current "o"
    grp_name = None       # current "g"
    material = None
    uses_o = re.search(r"(?m)^\s*o\s", text) is not None   # objects win over groups when both exist

    def current() -> dict:
        key = (obj_name if uses_o else grp_name) or _name(path)
        return parts.setdefault(key, {"polys": [], "mats": []})

    lines = text.splitlines()
    n_lines = max(1, len(lines))
    for i, line in enumerate(lines):
        if progress and i % 200000 == 0:
            progress(0.7 * i / n_lines)
        if not line or line[0] == "#":
            continue
        t = line.split()
        if not t:
            continue
        tag = t[0]
        if tag == "v":
            try:
                verts.append([float(t[1]), float(t[2]), float(t[3])])
                if len(t) >= 7:                                   # "v x y z r g b"
                    vcols.append([float(t[4]), float(t[5]), float(t[6])])
            except (IndexError, ValueError):
                raise ValueError(f"Invalid vertex on line {i + 1} of the OBJ file.") from None
        elif tag == "f":
            n = len(verts)
            poly = []
            for tok in t[1:]:
                s = tok.split("/", 1)[0]
                try:
                    k = int(s)
                except ValueError:
                    raise ValueError(f"Invalid face on line {i + 1} of the OBJ file.") from None
                poly.append(k - 1 if k > 0 else n + k)            # 1-based, or negative = from the end
            if len(poly) >= 3:
                part = current()
                part["polys"].append(poly)
                part["mats"].append(material)
        elif tag == "o":
            obj_name = " ".join(t[1:]) or None
        elif tag == "g":
            grp_name = " ".join(t[1:]) or None
        elif tag == "usemtl":
            material = " ".join(t[1:]) or None
        elif tag == "mtllib":
            for lib in [" ".join(t[1:])] + t[1:]:                 # names may contain spaces
                materials.update(_read_mtl(os.path.join(folder, lib)))

    if not verts:
        raise ValueError("This OBJ file contains no vertices.")
    V = np.array(verts, dtype=np.float64)
    VC = _to_u8(np.array(vcols)) if len(vcols) == len(verts) else None
    if progress:
        progress(0.8)

    model = ModelData(parts=[])
    for name, p in parts.items():
        if not p["polys"]:
            continue
        # triangulate, keeping each triangle's material
        tris, mats = [], []
        for poly, mat in zip(p["polys"], p["mats"]):
            for k in range(1, len(poly) - 1):
                tris.append((poly[0], poly[k], poly[k + 1]))
                mats.append(mat)
        F = np.array(tris, dtype=np.int64)
        if F.min() < 0 or F.max() >= len(V):
            raise ValueError("This OBJ file refers to vertices that do not exist.")
        v, f, vc = _compact(V, F, VC)
        part = MeshPart(name, v, f)
        if vc is not None:
            part.color, part.vertex_colors = _solid_or_none(vc)
        elif materials and any(m in materials for m in mats):
            fc = np.array([_rgb(materials.get(m)) for m in mats], dtype=np.uint8)
            part.color, part.face_colors = _solid_or_none(fc)
        model.parts.append(part)
    if progress:
        progress(1.0)
    return _check(model, "OBJ")


_DEFAULT_RGB = (200, 200, 200)       # faces without a material in a file that uses materials


def _rgb(hex_color: Optional[str]) -> tuple[int, int, int]:
    if not hex_color:
        return _DEFAULT_RGB
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


# ==========================================================================
# PLY (Stanford)
# ==========================================================================
_PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
    "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
}


def _ply_header(data: bytes):
    end = re.search(rb"end_header[ \t]*\r?\n", data)
    if not data.startswith(b"ply") or not end:
        raise ValueError("This is not a valid PLY file (header missing).")
    lines = data[: end.start()].decode("ascii", errors="replace").splitlines()
    fmt = None
    elements = []          # [name, count, [(prop, kind, dtype, count_dtype)]]
    for line in lines[1:]:
        t = line.split()
        if not t or t[0] in ("comment", "obj_info"):
            continue
        if t[0] == "format":
            fmt = t[1]
        elif t[0] == "element":
            elements.append([t[1], int(t[2]), []])
        elif t[0] == "property" and elements:
            if t[1] == "list":
                elements[-1][2].append((t[4], "list", _PLY_TYPES[t[3]], _PLY_TYPES[t[2]]))
            else:
                elements[-1][2].append((t[2], "scalar", _PLY_TYPES[t[1]], None))
    if fmt not in ("ascii", "binary_little_endian", "binary_big_endian"):
        raise ValueError(f"Unsupported PLY format: {fmt}")
    return fmt, elements, end.end()


def load_ply(path: str, progress: Progress = None) -> ModelData:
    with open(path, "rb") as f:
        data = f.read()
    fmt, elements, pos = _ply_header(data)
    end = "<" if fmt == "binary_little_endian" else ">"
    tokens = data[pos:].split() if fmt == "ascii" else None
    ti = 0                                            # next ascii token

    vertex = None          # structured array or dict of columns
    polys = None
    face_cols = None
    for e_i, (name, count, props) in enumerate(elements):
        if progress:
            progress(0.8 * e_i / max(1, len(elements)))
        has_list = any(p[1] == "list" for p in props)
        if fmt == "ascii":
            if not has_list:
                n = len(props)
                block = np.array(tokens[ti: ti + n * count], dtype=np.float64).reshape(count, n)
                ti += n * count
                cols = {p[0]: block[:, j] for j, p in enumerate(props)}
                rows = None
            else:
                rows = []
                cols = {p[0]: [] for p in props if p[1] == "scalar"}
                for _ in range(count):
                    row = {}
                    for p in props:
                        if p[1] == "list":
                            k = int(tokens[ti]); ti += 1
                            row[p[0]] = [int(float(x)) for x in tokens[ti: ti + k]]; ti += k
                        else:
                            cols[p[0]].append(float(tokens[ti])); ti += 1
                    rows.append(row)
                cols = {k: np.array(v) for k, v in cols.items()}
        else:
            if not has_list:
                dt = np.dtype([(p[0], end + p[2]) for p in props])
                arr = np.frombuffer(data, dtype=dt, count=count, offset=pos)
                pos += dt.itemsize * count
                cols = {p[0]: arr[p[0]] for p in props}
                rows = None
            else:
                cols, rows, pos = _ply_binary_lists(data, pos, count, props, end)

        if name == "vertex":
            vertex = cols
        elif name == "face":
            lst = next((p[0] for p in props if p[1] == "list"), None)
            if lst is None:
                continue
            polys = rows if isinstance(rows, np.ndarray) else [r[lst] for r in (rows or [])]
            if all(c in cols for c in ("red", "green", "blue")):
                face_cols = np.stack([cols["red"], cols["green"], cols["blue"]], axis=1)

    if vertex is None or not all(c in vertex for c in ("x", "y", "z")):
        raise ValueError("This PLY file has no vertex positions.")
    V = np.stack([vertex["x"], vertex["y"], vertex["z"]], axis=1).astype(np.float32)
    if polys is None or not len(polys):
        raise ValueError("This PLY file contains no faces (it may be a point cloud).")
    if progress:
        progress(0.85)

    if isinstance(polys, np.ndarray):                     # all triangles, fast path
        F = polys.astype(np.int64)
        tri_owner = np.arange(len(F))
    else:
        F = _fan(polys)
        tri_owner = np.repeat(np.arange(len(polys)), [max(0, len(p) - 2) for p in polys])
    if len(F) and (F.min() < 0 or F.max() >= len(V)):
        raise ValueError("This PLY file refers to vertices that do not exist.")

    part = MeshPart(_name(path), V, F)
    vc_names = ("red", "green", "blue") if "red" in vertex else ("r", "g", "b")
    if all(c in vertex for c in vc_names):
        vc = _to_u8(np.stack([vertex[c] for c in vc_names], axis=1))
        part.color, part.vertex_colors = _solid_or_none(vc)
    elif face_cols is not None:
        fc = _to_u8(face_cols)[tri_owner]
        part.color, part.face_colors = _solid_or_none(fc)
    if progress:
        progress(1.0)
    return _check(ModelData(parts=[part]), "PLY")


def _ply_binary_lists(data: bytes, pos: int, count: int, props, end: str):
    """A binary element with list properties (normally the faces)."""
    # Fast path: everything is triangles -> one fixed-size record per face.
    fields = []
    for p in props:
        if p[1] == "list":
            fields += [(p[0] + "#n", end + p[3]), (p[0], end + p[2], (3,))]
        else:
            fields.append((p[0], end + p[2]))
    dt = np.dtype(fields)
    if pos + dt.itemsize * count <= len(data):
        arr = np.frombuffer(data, dtype=dt, count=count, offset=pos)
        if all((arr[p[0] + "#n"] == 3).all() for p in props if p[1] == "list"):
            lst = next(p[0] for p in props if p[1] == "list")
            cols = {p[0]: arr[p[0]] for p in props if p[1] == "scalar"}
            return cols, arr[lst].copy(), pos + dt.itemsize * count
    # General case: read face by face.
    rows = []
    cols = {p[0]: [] for p in props if p[1] == "scalar"}
    for _ in range(count):
        row = {}
        for p in props:
            if p[1] == "list":
                cdt = np.dtype(end + p[3])
                k = int(np.frombuffer(data, cdt, 1, pos)[0]); pos += cdt.itemsize
                idt = np.dtype(end + p[2])
                row[p[0]] = np.frombuffer(data, idt, k, pos).astype(np.int64).tolist(); pos += idt.itemsize * k
            else:
                sdt = np.dtype(end + p[2])
                cols[p[0]].append(np.frombuffer(data, sdt, 1, pos)[0]); pos += sdt.itemsize
        rows.append(row)
    return {k: np.array(v) for k, v in cols.items()}, rows, pos


# ==========================================================================
# OFF (Object File Format)
# ==========================================================================
def load_off(path: str, progress: Progress = None) -> ModelData:
    with open(path, "rb") as f:
        data = f.read()
    text = data.decode("utf-8", errors="replace")
    lines = [ln.split("#", 1)[0].strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines or not re.match(r"^[A-Z]*OFF", lines[0]):
        raise ValueError("This is not a valid OFF file (it should start with OFF).")
    head = lines[0].split()
    if "BINARY" in head[0] or (len(head) > 1 and head[1] == "BINARY"):
        raise ValueError("Binary OFF files are not supported; only text OFF files.")
    rest = head[1:]
    li = 1
    if len(rest) < 3:
        rest = lines[1].split()
        li = 2
    nv, nf = int(rest[0]), int(rest[1])
    if len(lines) < li + nv + nf:
        raise ValueError("This OFF file is incomplete.")
    if progress:
        progress(0.2)

    vrows = [ln.split() for ln in lines[li: li + nv]]
    V = np.array([r[:3] for r in vrows], dtype=np.float32)
    vc = None
    if "C" in head[0] and vrows and all(len(r) >= 6 for r in vrows):
        vc = _to_u8(np.array([r[3:6] for r in vrows], dtype=np.float64))
    if progress:
        progress(0.5)

    polys, fcols = [], []
    for ln in lines[li + nv: li + nv + nf]:
        t = ln.split()
        k = int(t[0])
        polys.append([int(x) for x in t[1: 1 + k]])
        extra = t[1 + k:]
        fcols.append([float(x) for x in extra[:3]] if len(extra) >= 3 else None)
    F = _fan([p for p in polys if len(p) >= 3])
    if len(F) and (F.min() < 0 or F.max() >= len(V)):
        raise ValueError("This OFF file refers to vertices that do not exist.")

    part = MeshPart(_name(path), V, F)
    if vc is not None:
        part.color, part.vertex_colors = _solid_or_none(vc)
    elif fcols and all(c is not None for c in fcols):
        owner = np.repeat(np.arange(len(polys)), [max(0, len(p) - 2) for p in polys])
        fc = _to_u8(np.array(fcols))[owner]
        part.color, part.face_colors = _solid_or_none(fc)
    if progress:
        progress(1.0)
    return _check(ModelData(parts=[part]), "OFF")


# ==========================================================================
# glTF 2.0 / GLB
# ==========================================================================
_GL_TYPES = {5120: "i1", 5121: "u1", 5122: "i2", 5123: "u2", 5125: "u4", 5126: "f4"}
_GL_SIZES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_UNSUPPORTED_EXT = {
    "KHR_draco_mesh_compression": "Draco",
    "EXT_meshopt_compression": "meshoptimizer",
    "KHR_mesh_quantization": None,      # supported: just other number types, handled by the accessor code
}


_GLTF_DAMAGED = "This glTF file is damaged: it refers to data that is not in the file."


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


class _Gltf:
    def __init__(self, path: str):
        with open(path, "rb") as f:
            data = f.read()
        self.folder = os.path.dirname(os.path.abspath(path))
        self.bin = None
        if data[:4] == b"glTF":
            version, length = struct.unpack_from("<II", data, 4)
            if version != 2:
                raise ValueError(f"Only glTF 2.0 is supported (this file is version {version}).")
            pos, js = 12, None
            while pos + 8 <= min(length, len(data)):
                clen, ctype = struct.unpack_from("<II", data, pos)
                chunk = data[pos + 8: pos + 8 + clen]
                if ctype == 0x4E4F534A:            # JSON
                    js = chunk
                elif ctype == 0x004E4942:          # BIN
                    self.bin = chunk
                pos += 8 + clen
            if js is None:
                raise ValueError("This GLB file has no glTF data.")
            self.doc = json.loads(js.decode("utf-8"))
        else:
            self.doc = json.loads(data.decode("utf-8-sig"))
        if not str(self.doc.get("asset", {}).get("version", "2")).startswith("2"):
            raise ValueError("Only glTF 2.0 is supported.")
        for ext in self.doc.get("extensionsRequired", []):
            if _UNSUPPORTED_EXT.get(ext):
                raise ValueError(f"This file is compressed with {_UNSUPPORTED_EXT[ext]}, which PrintView3D "
                                 "cannot read yet. Export it again without mesh compression.")
        self._buffers: dict[int, bytes] = {}

    def resource_path(self, uri: str) -> str:
        """The file a buffer's "uri" names, which must lie in the glTF file's own folder.

        A crafted file could otherwise name any file on the computer ("/home/me/.ssh/key",
        "../../secret"), or on Windows a network share ("\\\\server\\share\\x.bin"): just opening
        it would then make Windows contact that server and send the user's sign-in hash."""
        from urllib.parse import unquote
        rel = unquote(uri).replace("\\", "/")
        bad = (not rel or rel.startswith("/") or ":" in rel           # absolute, C:, http:, file:
               or any(part in ("", "..") for part in rel.split("/")))  # "//server", "a//b", ".."
        if not bad:
            p = os.path.realpath(os.path.join(self.folder, *rel.split("/")))
            folder = os.path.realpath(self.folder)
            if os.path.commonpath([p, folder]) == folder:            # also through a symlink
                return p
        raise ValueError("This glTF file refers to data outside its own folder, which PrintView3D "
                         "does not read, to protect your computer.")

    def buffer(self, i: int) -> bytes:
        if i not in self._buffers:
            b = self.doc["buffers"][i]
            uri = b.get("uri")
            if uri is None:
                if self.bin is None:
                    raise ValueError("The binary data of this glTF file is missing.")
                self._buffers[i] = self.bin
            elif uri.startswith("data:"):
                self._buffers[i] = base64.b64decode(uri.split(",", 1)[1])
            else:
                p = self.resource_path(uri)
                try:
                    with open(p, "rb") as f:
                        self._buffers[i] = f.read()
                except OSError:
                    raise ValueError(f"The file {os.path.basename(p)} that belongs to this glTF "
                                     "file is missing.") from None
        return self._buffers[i]

    def accessor(self, i: int) -> np.ndarray:
        a = self.doc["accessors"][i]
        comps = _GL_SIZES[a["type"]]
        dt = np.dtype("<" + _GL_TYPES[a["componentType"]])
        count = int(a["count"])
        if count < 0:
            raise ValueError(_GLTF_DAMAGED)
        if "bufferView" in a:
            bv = self.doc["bufferViews"][a["bufferView"]]
            buf = self.buffer(bv["buffer"])
            start = int(bv.get("byteOffset", 0)) + int(a.get("byteOffset", 0))
            stride = int(bv.get("byteStride") or dt.itemsize * comps)
            # Everything that is read must lie inside the buffer. The interleaved case below reads
            # by address, so without this check a crafted stride or count read whatever followed
            # the buffer in memory (or crashed).
            if start < 0 or stride <= 0 or (
                    count and start + (count - 1) * stride + dt.itemsize * comps > len(buf)):
                raise ValueError(_GLTF_DAMAGED)
            if stride == dt.itemsize * comps:
                out = np.frombuffer(buf, dt, count * comps, start).reshape(count, comps)
            else:                                   # interleaved data
                rows = np.lib.stride_tricks.as_strided(
                    np.frombuffer(buf, np.uint8, len(buf) - start, start),
                    shape=(count, dt.itemsize * comps), strides=(stride, 1))
                out = rows.copy().view(dt).reshape(count, comps)
        else:
            out = np.zeros((count, comps), dt)
        if "sparse" in a:
            out = out.copy()
            s = a["sparse"]
            idx_a = {"bufferView": s["indices"]["bufferView"], "byteOffset": s["indices"].get("byteOffset", 0),
                     "componentType": s["indices"]["componentType"], "count": s["count"], "type": "SCALAR"}
            val_a = {"bufferView": s["values"]["bufferView"], "byteOffset": s["values"].get("byteOffset", 0),
                     "componentType": a["componentType"], "count": s["count"], "type": a["type"]}
            self.doc["accessors"].extend([idx_a, val_a])
            n = len(self.doc["accessors"])
            out[self.accessor(n - 2).ravel().astype(np.int64)] = self.accessor(n - 1)
        if a.get("normalized") and dt.kind in "iu":
            out = out.astype(np.float64) / float(np.iinfo(dt).max)
        return out

    def material_rgb(self, i: Optional[int]) -> Optional[np.ndarray]:
        if i is None:
            return None
        m = self.doc.get("materials", [])[i]
        f = m.get("pbrMetallicRoughness", {}).get("baseColorFactor")
        if f is None:
            return None
        return _linear_to_srgb(np.array(f[:3], dtype=np.float64)) * 255.0


def _node_matrix(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], dtype=np.float64).reshape(4, 4).T      # glTF is column-major
    t = np.array(node.get("translation", [0, 0, 0]), dtype=np.float64)
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    s = np.array(node.get("scale", [1, 1, 1]), dtype=np.float64)
    r = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    m = np.eye(4)
    m[:3, :3] = r * s
    m[:3, 3] = t
    return m


def _primitive_triangles(g: _Gltf, prim: dict, n_vertices: int) -> Optional[np.ndarray]:
    mode = prim.get("mode", 4)
    idx = g.accessor(prim["indices"]).ravel().astype(np.int64) if "indices" in prim else np.arange(n_vertices)
    if mode == 4:                                    # TRIANGLES
        return idx[: len(idx) // 3 * 3].reshape(-1, 3)
    if mode == 5:                                    # TRIANGLE_STRIP
        t = np.stack([idx[:-2], idx[1:-1], idx[2:]], axis=1)
        t[1::2] = t[1::2][:, [1, 0, 2]]
        return t
    if mode == 6:                                    # TRIANGLE_FAN
        return np.stack([np.full(len(idx) - 2, idx[0]), idx[1:-1], idx[2:]], axis=1)
    return None                                      # points or lines: nothing to show


def _gltf_scale(parts: list[MeshPart]) -> float:
    """glTF is in metres. A model that would be over 10 m tall in millimetres was almost
    certainly written in millimetres already (some CAD exporters do that)."""
    allv = np.vstack([p.vertices for p in parts])
    size = float((allv.max(axis=0) - allv.min(axis=0)).max())
    return 1.0 if size * 1000.0 > 10000.0 else 1000.0


def load_gltf(path: str, progress: Progress = None) -> ModelData:
    g = _Gltf(path)
    doc = g.doc
    nodes = doc.get("nodes", [])
    meshes = doc.get("meshes", [])
    scenes = doc.get("scenes", [])
    if scenes:
        roots = scenes[doc.get("scene", 0)].get("nodes", [])
    else:                                            # no scene: every node that is nobody's child
        children = {c for n in nodes for c in n.get("children", [])}
        roots = [i for i in range(len(nodes)) if i not in children]

    # Y up (glTF) -> Z up (3D printing)
    y_to_z = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=np.float64)

    instances = []                                   # (name, mesh index, world matrix)

    visited: set[int] = set()

    def walk(i: int, parent: np.ndarray, depth: int = 0):
        # glTF nodes form a tree: every node has one parent at most. A node seen before is
        # skipped, so a crafted file whose nodes list themselves (or each other) as children,
        # several times over, ends at once instead of never.
        if depth > 64 or i in visited:
            return
        visited.add(i)
        n = nodes[i]
        m = parent @ _node_matrix(n)
        if "mesh" in n:
            mesh = meshes[n["mesh"]]
            instances.append((n.get("name") or mesh.get("name") or f"Object {len(instances) + 1}", n["mesh"], m))
        for c in n.get("children", []):
            walk(c, m, depth + 1)

    for r in roots:
        walk(r, y_to_z)
    if not instances and meshes and not nodes:       # meshes without any nodes
        instances = [(mm.get("name") or f"Object {k + 1}", k, y_to_z) for k, mm in enumerate(meshes)]

    model = ModelData(parts=[])
    for k, (name, mesh_i, mat) in enumerate(instances):
        if progress:
            progress(0.9 * k / max(1, len(instances)))
        vs, fs, fcs, vcs = [], [], [], []
        offset = 0
        prims = meshes[mesh_i].get("primitives", [])
        any_vcolor = any("COLOR_0" in p.get("attributes", {}) for p in prims)
        any_material = any(g.material_rgb(p.get("material")) is not None for p in prims)
        for prim in prims:
            attrs = prim.get("attributes", {})
            if "POSITION" not in attrs:
                continue
            pos = g.accessor(attrs["POSITION"]).astype(np.float64)
            tris = _primitive_triangles(g, prim, len(pos))
            if tris is None or not len(tris):
                continue
            if tris.min() < 0 or tris.max() >= len(pos):
                raise ValueError("This glTF file refers to vertices that do not exist.")
            world = pos @ mat[:3, :3].T + mat[:3, 3]
            if np.linalg.det(mat[:3, :3]) < 0:         # mirrored: keep the outside facing out
                tris = tris[:, [0, 2, 1]]
            mat_rgb = g.material_rgb(prim.get("material"))
            # glTF: no material = white, multiplied by the vertex colours; without vertex
            # colours such faces get a neutral grey next to coloured ones.
            base = mat_rgb if mat_rgb is not None else np.array(_DEFAULT_RGB, dtype=np.float64)
            if any_vcolor:
                factor = mat_rgb if mat_rgb is not None else np.full(3, 255.0)
                if "COLOR_0" in attrs:
                    c = g.accessor(attrs["COLOR_0"]).astype(np.float64)[:, :3]
                    c = _linear_to_srgb(c if c.max(initial=0) <= 1.0 else c / 255.0) * 255.0
                    c = c * (factor / 255.0)
                else:
                    c = np.tile(factor, (len(pos), 1))
                vcs.append(c)
            fcs.append(np.tile(base, (len(tris), 1)))
            vs.append(world)
            fs.append(tris + offset)
            offset += len(pos)
        if not fs:
            continue
        V = np.vstack(vs)
        F = np.vstack(fs)
        VC = _to_u8(np.vstack(vcs)) if vcs else None
        v, f, vc = _compact(V, F, VC)
        part = MeshPart(name, v, f)
        if vc is not None:
            part.color, part.vertex_colors = _solid_or_none(vc)
        elif any_material:
            part.color, part.face_colors = _solid_or_none(_to_u8(np.vstack(fcs)))
        model.parts.append(part)

    _check(model, "glTF")
    scale = _gltf_scale(model.parts)
    for p in model.parts:
        p.vertices = (p.vertices.astype(np.float64) * scale).astype(np.float32)
    gen = doc.get("asset", {}).get("generator")
    if gen:
        model.meta["Created with"] = str(gen)
    if progress:
        progress(1.0)
    return model

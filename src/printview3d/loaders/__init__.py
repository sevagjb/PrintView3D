"""File loaders: STL, 3MF, OBJ, PLY, OFF, glTF/GLB, G-code, FreeCAD documents and STEP."""

import os
from typing import Optional

from .gcode import FEATURES, GcodeData, parse_gcode_file, parse_gcode_text
from .formats import load_gltf, load_obj, load_off, load_ply
from .mesh import (
    MeshPart, ModelData, load_3mf, load_stl, read_3mf_for_export, read_embedded_gcode, stl_file_names,
    write_binary_stl,
)

# extension -> kind
_KINDS = {
    ".stl": "stl", ".3mf": "3mf",
    ".obj": "obj", ".ply": "ply", ".off": "off", ".glb": "gltf", ".gltf": "gltf",
    ".gcode": "gcode", ".gco": "gcode", ".g": "gcode",
    ".fcstd": "freecad",
    ".step": "step", ".stp": "step",
}
MESH_EXTENSIONS = (".stl", ".3mf", ".obj", ".ply", ".off", ".glb", ".gltf")
GCODE_EXTENSIONS = (".gcode", ".gco", ".g")
FREECAD_EXTENSIONS = (".fcstd",)
STEP_EXTENSIONS = (".step", ".stp")
SUPPORTED_EXTENSIONS = tuple(_KINDS)
# Kinds that slicers don't all read: "Send to slicer" sends these as STL.
SEND_AS_STL = ("ply", "off", "gltf", "freecad")
_LOADERS = {"stl": load_stl, "3mf": load_3mf, "obj": load_obj, "ply": load_ply, "off": load_off,
            "gltf": load_gltf, "gcode": parse_gcode_file}


def file_kind(path: str) -> str:
    """Return 'stl', '3mf', 'obj', 'ply', 'off', 'gltf', 'gcode', 'freecad', 'step' or ''."""
    return _KINDS.get(os.path.splitext(path)[1].lower(), "")


def load_file(path: str, progress=None, freecad_path: str = ""):
    kind = file_kind(path)
    if kind in ("freecad", "step"):
        from .. import freecad          # not at import time: freecad imports this package
        load = freecad.load_fcstd if kind == "freecad" else freecad.load_step
        return load(path, progress, freecad.find_freecad(freecad_path))
    if kind in _LOADERS:
        return _LOADERS[kind](path, progress)
    raise ValueError(f"Unsupported file type: {os.path.basename(path)}")


# A picture file inside a ZIP: at least this big (smaller ones are icons and logos), at most this
# big (anything larger is no picture to preview).
_ZIP_PICTURE_MIN = 2 * 1024
_ZIP_3MF_MAX = 32 * 1024 ** 2          # a 3MF inside a ZIP is read for its picture up to this size
_PICTURE_FOLDERS = ("images", "image", "pictures", "picture", "photos", "photo", "renders", "render")


def _is_picture(data: bytes) -> bool:
    return data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"


def zip_picture(path: str) -> Optional[bytes]:
    """A preview for a ZIP of 3D files (Printables, Thingiverse, ...), first that it has: a picture
    file in it (the maker's photo or render, from a folder such as images/ first), the picture of
    its first 3MF, then that of its first G-code. Only the one part needed is read, within the
    same limits as opening the ZIP."""
    import io
    import re
    import zipfile
    from . import gcode, mesh, zipsafe

    def natural(text):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]

    with zipfile.ZipFile(path) as z:
        infos = []
        for info in z.infolist():
            parts = [p for p in info.filename.replace("\\", "/").split("/") if p]
            if info.is_dir() or not parts or any(p == "__MACOSX" or p.startswith(".") for p in parts):
                continue
            infos.append((info, [p.lower() for p in parts]))

        pictures = [(i, p) for i, p in infos if p[-1].endswith((".png", ".jpg", ".jpeg"))
                    and _ZIP_PICTURE_MIN <= i.file_size <= zipsafe.MAX_SMALL_BYTES]
        # Pictures in a folder such as images/ first; otherwise as the ZIP lists them (the download
        # sites put the main picture first).
        pictures.sort(key=lambda ip: not any(f in _PICTURE_FOLDERS for f in ip[1][:-1]))
        for info, _ in pictures:
            data = zipsafe.read(z, info.filename, zipsafe.MAX_SMALL_BYTES)
            if _is_picture(data):
                return data

        by_name = sorted(infos, key=lambda ip: natural(ip[0].filename))
        for info, parts in by_name:
            if parts[-1].endswith(".3mf") and not zipsafe.too_big(info, _ZIP_3MF_MAX):
                try:
                    with zipfile.ZipFile(io.BytesIO(zipsafe.read(z, info.filename, _ZIP_3MF_MAX))) as inner:
                        data = mesh._3mf_picture(inner, inner.namelist())
                except (zipfile.BadZipFile, ValueError, KeyError, OSError):
                    data = None
                if data:
                    return data
        for info, parts in by_name:
            if parts[-1].endswith(GCODE_EXTENSIONS) and not zipsafe.too_big(info):
                with z.open(info) as f:
                    data = gcode.thumbnail_from_head(f.read(gcode.THUMBNAIL_HEAD))
                if data:
                    return data
    return None


def read_thumbnail(path: str):
    """Only the preview picture saved in a file (PNG or JPEG bytes), or None: 3MF projects,
    G-code and FreeCAD documents can have one, and a ZIP of 3D files gets one from what is in it
    (zip_picture). Quick: the model itself is not read."""
    import zipfile
    from . import gcode, mesh, zipsafe
    kind = file_kind(path)
    try:
        if path.lower().endswith(".zip"):
            return zip_picture(path)
        if kind == "3mf":
            return mesh.read_3mf_thumbnail(path)
        if kind == "gcode":
            return gcode.read_thumbnail(path)
        if kind == "freecad":
            with zipfile.ZipFile(path) as z:
                names = set(z.namelist())
                for t in ("thumbnails/Thumbnail.png", "Thumbnail.png"):
                    if t in names:
                        return zipsafe.read(z, t, zipsafe.MAX_SMALL_BYTES)
    except (OSError, ValueError, zipfile.BadZipFile):
        pass
    return None


__all__ = [
    "FEATURES", "FREECAD_EXTENSIONS", "GcodeData", "MeshPart", "ModelData", "SEND_AS_STL",
    "SUPPORTED_EXTENSIONS", "file_kind", "load_file", "load_3mf", "load_gltf", "load_obj", "load_off",
    "load_ply", "load_stl", "parse_gcode_file",
    "parse_gcode_text", "read_3mf_for_export", "read_thumbnail", "read_embedded_gcode", "stl_file_names", "write_binary_stl",
]

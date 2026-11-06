"""File loaders: STL, 3MF, OBJ, PLY, OFF, glTF/GLB, G-code, FreeCAD documents and STEP."""

import os

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


def read_thumbnail(path: str):
    """Only the preview picture saved in a file (PNG or JPEG bytes), or None: 3MF projects,
    G-code and FreeCAD documents can have one. Quick: the model itself is not read."""
    import zipfile
    from . import gcode, mesh, zipsafe
    kind = file_kind(path)
    try:
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

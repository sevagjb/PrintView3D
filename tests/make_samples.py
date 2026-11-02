"""Generate small sample files used by the tests (and handy for trying the app).

Run:  python tests/make_samples.py
Creates tests/data/cube_binary.stl, cube_ascii.stl, two_parts.3mf,
cylinder.gcode and the general 3D formats: two_parts.obj (+ .mtl),
cube_binary.ply, quads_ascii.ply, cube_colors.off, two_nodes.glb and
embedded.gltf, and busy_project.3mf (twelve objects and a long description,
issue #62). The 3MF mimics Creality Print / OrcaSlicer's multi-file
layout, and the G-code mimics their comment style.
"""

import base64
import math
import os
import struct
import zipfile


def _fixed_writestr(z, name, data):
    """Write a zip member with a fixed timestamp so regenerated files are identical."""
    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(info, data)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")


def cube_tris(size=20.0, ox=0.0, oy=0.0, oz=0.0):
    s = size
    v = [(0, 0, 0), (s, 0, 0), (s, s, 0), (0, s, 0), (0, 0, s), (s, 0, s), (s, s, s), (0, s, s)]
    v = [(x + ox, y + oy, z + oz) for x, y, z in v]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return v, f


def write_stl_binary(path):
    v, f = cube_tris()
    with open(path, "wb") as fh:
        fh.write(b"PrintView3D sample cube".ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(f)))
        for a, b, c in f:
            fh.write(struct.pack("<3f", 0, 0, 0))
            for i in (a, b, c):
                fh.write(struct.pack("<3f", *v[i]))
            fh.write(b"\0\0")


def write_stl_ascii(path):
    v, f = cube_tris(10)
    lines = ["solid sample_cube"]
    for a, b, c in f:
        lines.append(" facet normal 0 0 0\n  outer loop")
        for i in (a, b, c):
            lines.append("   vertex %f %f %f" % v[i])
        lines.append("  endloop\n endfacet")
    lines.append("endsolid sample_cube")
    with open(path, "w") as fh:
        fh.write("\n".join(lines))


def _png_1px():
    # A tiny valid PNG (2x2 grey) generated with zlib, no Pillow needed.
    import zlib
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * 2 for _ in range(2))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def write_3mf(path):
    core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    prod = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"

    def mesh_xml(size):
        v, f = cube_tris(size, -size / 2, -size / 2, 0)
        vs = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in v)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
        return f"<mesh><vertices>{vs}</vertices><triangles>{ts}</triangles></mesh>"

    obj_model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="{core}">'
                 f'<resources><object id="1" type="model">{mesh_xml(20)}</object>'
                 f'<object id="2" type="model">{mesh_xml(10)}</object></resources><build/></model>')
    root_model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="{core}" '
                  f'xmlns:p="{prod}" requiredextensions="p">'
                  f'<metadata name="Application">CrealityPrint-6.0</metadata>'
                  f'<metadata name="Title">Sample plate</metadata>'
                  f'<resources>'
                  f'<object id="10" name="Big cube" type="model"><components>'
                  f'<component p:path="/3D/Objects/object_1.model" objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
                  f'</components></object>'
                  f'<object id="11" name="Small cube" type="model"><components>'
                  f'<component p:path="/3D/Objects/object_1.model" objectid="2" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
                  f'</components></object>'
                  f'</resources><build>'
                  f'<item objectid="10" transform="1 0 0 0 1 0 0 0 1 160 175 0"/>'
                  f'<item objectid="11" transform="1 0 0 0 1 0 0 0 1 195 175 0"/>'
                  f'</build></model>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    settings = ('{"printer_model": "Creality K2 Plus", "layer_height": "0.2", '
                '"nozzle_diameter": ["0.4"], "filament_type": ["PLA"], '
                '"printable_area": ["0x0", "350x0", "350x350", "0x350"]}')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        _fixed_writestr(z, "[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        _fixed_writestr(z, "_rels/.rels", rels)
        _fixed_writestr(z, "3D/3dmodel.model", root_model)
        _fixed_writestr(z, "3D/Objects/object_1.model", obj_model)
        _fixed_writestr(z, "Metadata/project_settings.config", settings)
        _fixed_writestr(z, "Metadata/plate_1.png", _png_1px())
        _fixed_writestr(z, "Metadata/plate_1.gcode", make_gcode(radius=10, height=4, cx=175, cy=175))


def _png(w, h, rgb=(0x4a, 0xa3, 0xdf)):
    """A plain one-colour PNG of w x h pixels (zlib only, no Pillow)."""
    import zlib
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


BUSY_DESCRIPTION = "\n\n".join([
    "A modular desk organiser set: twelve separate parts that print without supports and "
    "click together with friction-fit joints. Every part fits on a 256 x 256 mm plate.",
    "Print settings: 0.2 mm layer height, 3 walls, 15 % gyroid infill. PLA and PETG both work; "
    "for PETG lower the bridge speed. The pen cups look best with a 0.4 mm nozzle and a matte "
    "filament, the drawers slide more smoothly when printed in PETG.",
    "Assembly: push the connectors into the base plates first, then slide the cups and trays on "
    "from above. If a joint is too tight, scale the connectors to 99 % in your slicer. "
    "No glue or screws are needed.",
    "Remixes are welcome. Please share a photo of your print in the comments and tell me which "
    "filament you used, so other makers can see how it turns out in different colours.",
    "Changelog: v3 thicker drawer walls, v2 rounder edges on the pen cups, v1 first upload.",
])


def write_3mf_busy_project(path):
    """A slicer project like the ones from MakerWorld / Printables: twelve objects, a long
    description, designer, profiles and a large plate picture. In version 0.23.0 the
    Details box of this file pushes the Objects box below the window (issue #62)."""
    core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    names = ["Base plate left", "Base plate right", "Pen cup tall", "Pen cup short", "Phone stand",
             "Card holder", "Drawer frame", "Drawer", "Cable clip", "Connector A", "Connector B",
             "Label plate"]
    objs, items = [], []
    for i, name in enumerate(names):
        size = 12 + (i % 4) * 6
        v, f = cube_tris(size, -size / 2, -size / 2, 0)
        vs = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in v)
        ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
        objs.append(f'<object id="{i + 1}" name="{name}" type="model"><mesh><vertices>{vs}</vertices>'
                    f'<triangles>{ts}</triangles></mesh></object>')
        x, y = 40 + (i % 4) * 55, 50 + (i // 4) * 70
        items.append(f'<item objectid="{i + 1}" transform="1 0 0 0 1 0 0 0 1 {x} {y} 0"/>')
    from xml.sax.saxutils import escape
    model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="{core}">'
             f'<metadata name="Application">BambuStudio-02.03.00.70</metadata>'
             f'<metadata name="Title">Modular desk organiser - 12 parts, no supports</metadata>'
             f'<metadata name="Designer">PrintView3D test files</metadata>'
             f'<metadata name="Description">{escape(BUSY_DESCRIPTION)}</metadata>'
             f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    settings = ('{"printer_model": "Bambu Lab P1S", '
                '"printer_settings_id": "Bambu Lab P1S 0.4 nozzle", '
                '"print_settings_id": "0.20mm Standard @BBL X1C - 3 walls 15% gyroid", '
                '"layer_height": "0.2", "nozzle_diameter": ["0.4"], "filament_type": ["PLA"], '
                '"filament_settings_id": ["Bambu PLA Matte @BBL X1C"], '
                '"printable_area": ["0x0", "256x0", "256x256", "0x256"]}')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        _fixed_writestr(z, "[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        _fixed_writestr(z, "_rels/.rels", rels)
        _fixed_writestr(z, "3D/3dmodel.model", model)
        _fixed_writestr(z, "Metadata/project_settings.config", settings)
        _fixed_writestr(z, "Metadata/plate_1.png", _png(256, 256))


def make_gcode(radius=15.0, height=10.0, cx=110.0, cy=110.0, layer_h=0.2):
    out = []
    w = out.append
    w("; HEADER_BLOCK_START")
    w("; generated by PrintView3D test generator")
    w("; estimated printing time (normal mode) = 12m 34s")
    w("; HEADER_BLOCK_END")
    thumb = base64.b64encode(_png_1px()).decode()
    w(f"; thumbnail begin 2x2 {len(thumb)}")
    for i in range(0, len(thumb), 78):
        w("; " + thumb[i:i + 78])
    w("; thumbnail end")
    w("G28")
    w("G90")
    w("M83")
    w("G1 Z0.3 F600")
    w("G1 X5 Y5 F6000")
    w("G1 X100 Y5 E9.5 F1500 ; purge line")
    n_layers = int(round(height / layer_h))
    for L in range(n_layers):
        z = (L + 1) * layer_h
        w(";LAYER_CHANGE")
        w(f";Z:{z:.2f}")
        w(f"G1 Z{z:.2f} F600")
        # outer wall as two G3 arcs (half circles)
        w(";TYPE:Outer wall")
        w(f"G1 X{cx + radius:.3f} Y{cy:.3f} F9000")
        w(f"G3 X{cx - radius:.3f} Y{cy:.3f} I{-radius:.3f} J0 E{math.pi * radius * 0.033:.4f} F3000")
        w(f"G3 X{cx + radius:.3f} Y{cy:.3f} I{radius:.3f} J0 E{math.pi * radius * 0.033:.4f}")
        # inner wall as polygon
        w(";TYPE:Inner wall")
        r2 = radius - 0.45
        for k in range(37):
            a = 2 * math.pi * k / 36
            w(f"G1 X{cx + r2 * math.cos(a):.3f} Y{cy + r2 * math.sin(a):.3f} E0.08")
        # infill: zig-zag lines
        kind = "Bottom surface" if L < 2 else ("Top surface" if L >= n_layers - 2 else "Sparse infill")
        w(f";TYPE:{kind}")
        step = 0.45 if kind != "Sparse infill" else 3.0
        yv = cy - r2 + step
        flip = False
        while yv < cy + r2 - step:
            half = math.sqrt(max(0.0, r2 * r2 - (yv - cy) ** 2)) - 0.2
            xa, xb = (cx - half, cx + half) if not flip else (cx + half, cx - half)
            w(f"G1 X{xa:.3f} Y{yv:.3f} F9000")
            w(f"G1 X{xb:.3f} Y{yv:.3f} E{2 * half * 0.033:.4f} F4000")
            yv += step
            flip = not flip
    w("; filament used [mm] = 1234.56")
    w("; filament used [g] = 3.70")
    w("; filament_type = PLA")
    w("; layer_height = 0.2")
    w("; nozzle_diameter = 0.4")
    w("; printer_model = Creality K1C")
    w("; printable_area = 0x0,220x0,220x220,0x220")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------- general 3D formats
def write_obj(path):
    """Two objects with materials; the second uses quads and negative indices."""
    lines = ["# PrintView3D sample", "mtllib two_parts.mtl", "o Red cube", "usemtl red"]
    v, f = cube_tris()
    lines += ["v %g %g %g" % p for p in v]
    lines += ["f %d/1/1 %d/1/1 %d/1/1" % (a + 1, b + 1, c + 1) for a, b, c in f]
    lines += ["o Green block", "usemtl green"]
    v2 = [(x + 30, y, z * 0.5) for x, y, z in v]
    lines += ["v %g %g %g" % p for p in v2]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    lines += ["f " + " ".join(str(i - 8) for i in q) for q in quads]      # -8..-1 = last 8 vertices
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.splitext(path)[0] + ".mtl", "w", newline="\n") as fh:
        fh.write("newmtl red\nKd 0.9 0.2 0.2\nnewmtl green\nKd 0.2 0.8 0.3\n")


def write_ply_binary(path):
    """Binary little-endian PLY, triangles, a colour per vertex."""
    v, f = cube_tris()
    head = ("ply\nformat binary_little_endian 1.0\ncomment PrintView3D sample\n"
            "element vertex %d\nproperty float x\nproperty float y\nproperty float z\n"
            "property uchar red\nproperty uchar green\nproperty uchar blue\n"
            "element face %d\nproperty list uchar int vertex_indices\nend_header\n" % (len(v), len(f)))
    with open(path, "wb") as fh:
        fh.write(head.encode("ascii"))
        for i, (x, y, z) in enumerate(v):
            fh.write(struct.pack("<fffBBB", x, y, z, 255 if i & 1 else 40, 128, 255 if i & 4 else 40))
        for a, b, c in f:
            fh.write(struct.pack("<Biii", 3, a, b, c))


def write_ply_ascii(path):
    """Text PLY with quads and an extra element after the faces."""
    v, _ = cube_tris()
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    out = ["ply", "format ascii 1.0", "element vertex %d" % len(v), "property float x",
           "property float y", "property float z", "element face %d" % len(quads),
           "property list uchar int vertex_index", "element edge 1", "property int vertex1",
           "property int vertex2", "end_header"]
    out += ["%g %g %g" % p for p in v]
    out += ["4 %d %d %d %d" % q for q in quads]
    out += ["0 1"]
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


def write_off(path):
    """Text OFF with quads and a colour per face (0..255)."""
    v, _ = cube_tris()
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    cols = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255)]
    out = ["OFF", "# PrintView3D sample", "%d %d 0" % (len(v), len(quads))]
    out += ["%g %g %g" % p for p in v]
    out += ["4 %d %d %d %d %d %d %d" % (q + c) for q, c in zip(quads, cols)]
    with open(path, "w", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


def _gltf_cube(doc, buf):
    """Add a 1 x 1 x 1 m cube mesh (Y up) to a glTF document; returns its mesh index."""
    v, f = cube_tris(size=0.02)                                   # 20 mm, in metres
    v = [(x, z, -y) for x, y, z in v]                             # Z up -> Y up
    pos = b"".join(struct.pack("<fff", *p) for p in v)
    idx = b"".join(struct.pack("<HHH", *t) for t in f)
    off = len(buf)
    buf += pos + idx
    bv = len(doc["bufferViews"])
    doc["bufferViews"] += [{"buffer": 0, "byteOffset": off, "byteLength": len(pos)},
                           {"buffer": 0, "byteOffset": off + len(pos), "byteLength": len(idx)}]
    ac = len(doc["accessors"])
    xs, ys, zs = zip(*v)
    doc["accessors"] += [
        {"bufferView": bv, "componentType": 5126, "count": len(v), "type": "VEC3",
         "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]},
        {"bufferView": bv + 1, "componentType": 5123, "count": len(f) * 3, "type": "SCALAR"},
    ]
    doc["meshes"].append({"name": "Cube", "primitives": [
        {"attributes": {"POSITION": ac}, "indices": ac + 1, "material": 0}]})
    return len(doc["meshes"]) - 1, buf


def _gltf_doc():
    return {"asset": {"version": "2.0", "generator": "PrintView3D sample"}, "scene": 0,
            "scenes": [{"nodes": [0]}], "nodes": [], "meshes": [], "accessors": [], "bufferViews": [],
            "materials": [{"pbrMetallicRoughness": {"baseColorFactor": [0.8, 0.1, 0.1, 1]}}]}


def write_glb(path):
    """GLB: a parent node with two children using the same mesh, one moved 30 mm."""
    import json as _json
    doc = _gltf_doc()
    mesh, buf = _gltf_cube(doc, b"")
    doc["nodes"] = [{"name": "Assembly", "children": [1, 2]},
                    {"name": "Left cube", "mesh": mesh},
                    {"name": "Right cube", "mesh": mesh, "translation": [0.03, 0, 0]}]
    while len(buf) % 4:
        buf += b"\0"
    doc["buffers"] = [{"byteLength": len(buf)}]
    js = _json.dumps(doc, separators=(",", ":"), sort_keys=True).encode()
    while len(js) % 4:
        js += b" "
    with open(path, "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(buf)))
        fh.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        fh.write(struct.pack("<II", len(buf), 0x004E4942) + buf)


def write_gltf(path):
    """Text glTF with its data embedded as base64, the node scaled by 2."""
    import json as _json
    doc = _gltf_doc()
    mesh, buf = _gltf_cube(doc, b"")
    doc["nodes"] = [{"name": "Big cube", "mesh": mesh, "scale": [2, 2, 2]}]
    doc["buffers"] = [{"byteLength": len(buf),
                       "uri": "data:application/octet-stream;base64," + base64.b64encode(buf).decode()}]
    with open(path, "w", newline="\n") as fh:
        _json.dump(doc, fh, indent=1, sort_keys=True)


def _box_xml(oid, name, lx, ly, lz):
    v = [(0, 0, 0), (lx, 0, 0), (lx, ly, 0), (0, ly, 0), (0, 0, lz), (lx, 0, lz), (lx, ly, lz), (0, ly, lz)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    vs = "".join(f'<vertex x="{x}" y="{y}" z="{z}"/>' for x, y, z in v)
    ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in f)
    return (f'<object id="{oid}" name="{name}" type="model"><mesh><vertices>{vs}</vertices>'
            f'<triangles>{ts}</triangles></mesh></object>')


def write_3mf_larger_than_plate(path):
    """A 420 mm shelf rail in a project for a 220 x 220 mm printer: it sticks out of the
    printer's plate on both sides (issue #61, adjustable / infinite build plate)."""
    core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    objs = _box_xml(1, "Long shelf rail", 420, 40, 12) + _box_xml(2, "Bracket", 60, 60, 30)
    items = ('<item objectid="1" transform="1 0 0 0 1 0 0 0 1 -100 60 0"/>'
             '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 80 150 0"/>')
    model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="{core}">'
             f'<metadata name="Application">OrcaSlicer-2.3.1</metadata>'
             f'<metadata name="Title">Shelf rail, longer than the plate</metadata>'
             f'<resources>{objs}</resources><build>{items}</build></model>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    settings = ('{"printer_model": "Creality K1C", "layer_height": "0.2", "nozzle_diameter": ["0.4"], '
                '"filament_type": ["PLA"], "printable_area": ["0x0", "220x0", "220x220", "0x220"]}')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        _fixed_writestr(z, "[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        _fixed_writestr(z, "_rels/.rels", rels)
        _fixed_writestr(z, "3D/3dmodel.model", model)
        _fixed_writestr(z, "Metadata/project_settings.config", settings)


def _mesh_object_xml(oid, name, verts, tris):
    vs = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in verts)
    ts = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris)
    return (f'<object id="{oid}" name="{name}" type="model"><mesh><vertices>{vs}</vertices>'
            f'<triangles>{ts}</triangles></mesh></object>')


def _box(x0, y0, z0, x1, y1, z1, inward=False):
    """Vertices and triangles of a box; inward=True turns the faces inside (a cavity)."""
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    if inward:
        f = [(a, c, b) for a, b, c in f]
    return v, f


def _tube(cx, cy, r_out, r_in, h, n=48):
    """A tube standing on z = 0: outer and inner wall, top and bottom ring."""
    v, f = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        v += [(cx + r_out * c, cy + r_out * s, 0), (cx + r_out * c, cy + r_out * s, h),
              (cx + r_in * c, cy + r_in * s, 0), (cx + r_in * c, cy + r_in * s, h)]
    for k in range(n):
        o0, o1 = 4 * k, 4 * ((k + 1) % n)
        ob, ot, ib, it = o0, o0 + 1, o0 + 2, o0 + 3
        ob2, ot2, ib2, it2 = o1, o1 + 1, o1 + 2, o1 + 3
        f += [(ob, ob2, ot2), (ob, ot2, ot)]          # outer wall, facing out
        f += [(ib, it2, ib2), (ib, it, it2)]          # inner wall, facing the hole
        f += [(ot, ot2, it2), (ot, it2, it)]          # top ring
        f += [(ob, ib2, ob2), (ob, ib, ib2)]          # bottom ring
    return v, f


def write_3mf_inside_view(path):
    """Things you only see with X-ray or the clip slider (issue #60): a closed box with a
    hollow inside and a small part hidden in it, and a tube to look into from the side."""
    core = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    bv, bf = _box(0, 0, 0, 60, 40, 30)
    cv, cf = _box(5, 5, 5, 55, 35, 25, inward=True)    # 5 mm walls, closed on every side
    box_v, box_f = bv + cv, bf + [(a + 8, b + 8, c + 8) for a, b, c in cf]
    hidden_v, hidden_f = _box(20, 12, 5, 40, 28, 15)   # sits on the cavity floor, out of sight
    tube_v, tube_f = _tube(105, 20, 15, 10, 40)
    objs = (_mesh_object_xml(1, "Hollow box", box_v, box_f)
            + _mesh_object_xml(2, "Hidden part", hidden_v, hidden_f)
            + _mesh_object_xml(3, "Tube", tube_v, tube_f))
    items = "".join(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 60 90 0"/>' for i in (1, 2, 3))
    model = (f'<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xmlns="{core}">'
             f'<metadata name="Application">PrintView3D test files</metadata>'
             f'<metadata name="Title">Inside view: hollow box, hidden part and a tube</metadata>'
             f'<resources>{objs}</resources><build>{items}</build></model>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    settings = ('{"printer_model": "Creality K2 Plus", "layer_height": "0.2", "nozzle_diameter": ["0.4"], '
                '"filament_type": ["PLA"], "printable_area": ["0x0", "350x0", "350x350", "0x350"]}')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        _fixed_writestr(z, "[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        _fixed_writestr(z, "_rels/.rels", rels)
        _fixed_writestr(z, "3D/3dmodel.model", model)
        _fixed_writestr(z, "Metadata/project_settings.config", settings)


def main():
    os.makedirs(OUT, exist_ok=True)
    write_stl_binary(os.path.join(OUT, "cube_binary.stl"))
    write_stl_ascii(os.path.join(OUT, "cube_ascii.stl"))
    write_3mf(os.path.join(OUT, "two_parts.3mf"))
    write_3mf_busy_project(os.path.join(OUT, "busy_project.3mf"))
    with open(os.path.join(OUT, "cylinder.gcode"), "w") as fh:
        fh.write(make_gcode())
    write_obj(os.path.join(OUT, "two_parts.obj"))
    write_ply_binary(os.path.join(OUT, "cube_binary.ply"))
    write_ply_ascii(os.path.join(OUT, "quads_ascii.ply"))
    write_off(os.path.join(OUT, "cube_colors.off"))
    write_glb(os.path.join(OUT, "two_nodes.glb"))
    write_gltf(os.path.join(OUT, "embedded.gltf"))
    write_3mf_inside_view(os.path.join(OUT, "inside_view.3mf"))   # issue #60
    write_3mf_larger_than_plate(os.path.join(OUT, "larger_than_plate.3mf"))   # issue #61
    print("Sample files written to", OUT)


if __name__ == "__main__":
    main()

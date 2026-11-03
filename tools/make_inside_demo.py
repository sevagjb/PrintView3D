"""Create examples/demo_housing.3mf: a small pump housing with real insides, for the
"Look inside your models" page of the website and for trying View -> X-ray and the clips.

- Housing: a rounded block with a round chamber, an inlet from the top, an outlet channel to
  the side, four screw holes and a hidden pocket behind a 1 mm wall.
- Impeller: a separate object inside the chamber (only visible with X-ray or a cut).

Needs manifold3d for the solid modelling (only for this script, not for PrintView3D):
    pip install manifold3d
    python tools/make_inside_demo.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from make_demo import OUT, write_3mf  # noqa: E402

try:
    from manifold3d import Manifold
except ImportError:
    raise SystemExit("This script needs manifold3d:  pip install manifold3d")

CX, CY = 175.0, 175.0            # centre of a 350 x 350 plate (Creality K2 Plus)
L, W, H = 96.0, 64.0, 46.0       # housing length (X), width (Y), height (Z)
CORNER = 8.0                     # rounded corners, seen from above
SEG = 128                        # circle segments


def _cyl(h, r, x=0.0, y=0.0, z=0.0):
    return Manifold.cylinder(h, r, r, SEG).translate([x, y, z])


def _hcyl_x(length, r, x, y, z):
    """A cylinder lying along X, starting at x."""
    return Manifold.cylinder(length, r, r, SEG).rotate([0, 90, 0]).translate([x, y, z])


def housing() -> Manifold:
    hx, hy = L / 2 - CORNER, W / 2 - CORNER
    block = Manifold.batch_hull([_cyl(H, CORNER, sx * hx, sy * hy) for sx in (-1, 1) for sy in (-1, 1)])
    chamber_x = -14.0
    cuts = [
        _cyl(H - 10.0, 22.0, chamber_x, 0, 5.0),                    # chamber: 5 mm floor, 5 mm roof
        _cyl(12.0, 7.0, chamber_x, 0, H - 8.0),                     # inlet from the top
        _hcyl_x(L / 2 + 20.0, 6.0, chamber_x, 0, 18.0),             # outlet channel to the right side
        Manifold.cube([18.0, W - 2 * 1.0 - 30.0, 30.0]).translate([22.0, -W / 2 + 1.0, 8.0]),  # pocket, 1 mm wall
    ]
    for sx in (-1, 1):
        for sy in (-1, 1):
            cuts.append(_cyl(34.0, 1.7, sx * (L / 2 - 6.5), sy * (W / 2 - 6.5), H - 34.0))  # screw holes
    return block - Manifold.batch_boolean(cuts, _union())


def _union():
    from manifold3d import OpType
    return OpType.Add


def impeller() -> Manifold:
    """Made around the origin; main() puts it in the chamber."""
    parts = [_cyl(30.0, 5.0, 0, 0, 0), _cyl(3.0, 18.0, 0, 0, 0)]    # hub and back plate
    for k in range(6):
        fin = Manifold.cube([16.0, 2.4, 26.0]).translate([3.0, -1.2, 3.0]).rotate([0, 0, 60.0 * k + 15.0])
        parts.append(fin)
    imp = Manifold.batch_boolean(parts, _union())
    return imp - _cyl(32.0, 2.0, 0, 0, -1.0)                       # shaft hole


def _mesh(m: Manifold, dx: float, dy: float, dz: float):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float64) + (dx, dy, dz)
    f = np.asarray(mesh.tri_verts).astype(np.int64)
    return v, f


def thumbnail(parts, size=256) -> bytes:
    """The plate picture slicers save in a 3MF: the housing seen at an angle (pyvista, offscreen).
    Falls back to a plain colour square without a working offscreen renderer."""
    try:
        import io

        import pyvista as pv
        from PIL import Image
        p = pv.Plotter(off_screen=True, window_size=(size, size))
        p.set_background("#2b2f36")
        for (name, v, f), color in zip(parts, ("#3d8fd1", "#f0a04b")):
            faces = np.hstack([np.full((len(f), 1), 3), f]).ravel()
            p.add_mesh(pv.PolyData(v, faces), color=color, smooth_shading=False)
        p.view_isometric()
        p.camera.zoom(1.25)
        img = Image.fromarray(p.screenshot(None, return_img=True))
        p.close()
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        return buf.getvalue()
    except Exception as e:                       # no offscreen OpenGL here
        print("thumbnail: plain colour (", e, ")")
        from make_demo import tiny_png
        return tiny_png((61, 143, 209))


def main():
    h = housing()
    imp = impeller()
    parts = [
        ("Housing",) + _mesh(h, CX, CY, 0.0),
        ("Impeller",) + _mesh(imp, CX - 14.0, CY, 7.0),
    ]
    path = os.path.join(OUT, "demo_housing.3mf")
    write_3mf(path, parts, thumbnail(parts))
    for name, v, f in parts:
        print(f"{name}: {len(f)} triangles, size {np.ptp(v, axis=0).round(2)} mm")
    print("written", path)


if __name__ == "__main__":
    main()

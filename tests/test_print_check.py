"""The Check section's analyses: overhangs, thin walls and the mesh check."""

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.ui import print_check as pc  # noqa: E402


def box(x0=0.0, y0=0.0, z0=0.0, dx=20.0, dy=20.0, dz=20.0):
    """A closed box as 8 vertices and 12 outward-facing triangles."""
    v = np.array([[x0 + i * dx, y0 + j * dy, z0 + k * dz] for k in (0, 1) for j in (0, 1) for i in (0, 1)],
                 dtype=np.float32)
    f = np.array([[0, 2, 1], [1, 2, 3],          # bottom (z0), facing down
                  [4, 5, 6], [5, 7, 6],          # top, facing up
                  [0, 1, 4], [1, 5, 4],          # front (y0)
                  [2, 6, 3], [3, 6, 7],          # back
                  [0, 4, 2], [2, 4, 6],          # left (x0)
                  [1, 3, 5], [3, 7, 5]],         # right
                 dtype=np.int64)
    return v, f


def test_the_box_is_closed_and_faces_outwards():
    v, f = box()
    n, area = pc.face_normals(v, f)
    centre = v.mean(axis=0)
    assert np.all(np.einsum("ij,ij->i", v[f].mean(axis=1) - centre, n) > 0)       # all point outwards
    r = pc.mesh_report(v, f)
    assert len(r["open"]) == 0 and len(r["nonmanifold"]) == 0
    assert not r["flipped"].any() and not r["loose"].any() and r["pieces"] == 1 and r["inside_out"] == 0


# ------------------------------------------------------------ overhangs
def test_a_box_on_the_plate_has_no_overhangs():
    v, f = box()
    assert not pc.overhang_faces(v, f, 45).any()


def test_a_box_in_the_air_has_its_bottom_as_overhang():
    v, f = box(z0=10)
    mask = pc.overhang_faces(v, f, 45, floor_z=0.0)
    assert mask.tolist() == [True, True] + [False] * 10


def test_the_angle_decides():
    # a roof facing down at 30 degrees from horizontal (60 degrees from vertical)
    a = np.radians(30)
    v = np.array([[0, 0, 10], [10, 0, 10 + 10 * np.tan(a)], [0, 10, 10]], dtype=np.float64)
    f = np.array([[0, 2, 1]])
    n, _ = pc.face_normals(v, f)
    assert n[0, 2] < 0                                    # facing down
    assert pc.overhang_faces(v, f, 45, floor_z=0).tolist() == [True]       # leans 60 > 45
    assert pc.overhang_faces(v, f, 65, floor_z=0).tolist() == [False]      # 60 < 65


# ------------------------------------------------------------ mesh check
def test_a_missing_triangle_leaves_three_open_edges():
    v, f = box()
    r = pc.mesh_report(v, f[1:])
    assert len(r["open"]) == 3 and r["open"].shape[1:] == (2, 3)
    assert r["inside_out"] == 0                           # an open piece is never called inside out


def test_a_flipped_triangle_is_found():
    v, f = box()
    f = f.copy()
    f[4] = f[4][::-1]                                     # one front triangle the wrong way
    r = pc.mesh_report(v, f)
    assert r["flipped"][4]
    assert r["flipped"].sum() == 4                        # and the three it disagrees with


def test_an_inside_out_part_is_flipped_everywhere():
    v, f = box()
    r = pc.mesh_report(v, f[:, ::-1])
    assert r["inside_out"] == 1 and r["flipped"].all()


def test_loose_parts_and_non_manifold_edges():
    v1, f1 = box()
    v2, f2 = box(x0=50, dx=5, dy=5, dz=5)
    v = np.vstack([v1, v2])
    f = np.vstack([f1, f2 + len(v1)])
    r = pc.mesh_report(v, f)
    assert r["pieces"] == 2 and r["loose"].sum() == 12 and r["loose"][12:].all()   # the small box
    extra = np.array([[0, 1, 5]])                         # a fin on the front-bottom edge
    v3 = np.vstack([v1, [[10, -10, 0]]])
    f3 = np.vstack([f1, [[0, 1, 8]]])
    r3 = pc.mesh_report(v3, f3)
    assert len(r3["nonmanifold"]) == 1                    # edge 0-1 has three faces now
    assert extra.shape == (1, 3)


def test_separate_triangles_are_merged_first():
    v, f = box()
    sv = v[f].reshape(-1, 3)                              # every triangle with its own 3 vertices
    sf = np.arange(len(sv)).reshape(-1, 3)
    r = pc.mesh_report(sv, sf)
    assert len(r["open"]) == 0 and r["pieces"] == 1


def test_components_of_a_long_chain():
    n = 2000                                              # a strip of triangles: long to walk through
    v = np.zeros((n + 2, 3))
    f = np.array([[i, i + 1, i + 2] for i in range(n)])
    assert set(pc.components(len(v), f)) == {0}


# ------------------------------------------------------------ thin walls
def test_thin_plate_is_thin_on_its_big_faces_only():
    v, f = box(dx=20, dy=20, dz=0.2)                      # a 0.2 mm plate
    thin = pc.thin_faces(v, f, 0.4)
    assert thin[:4].all()                                 # top and bottom: 0.2 < 0.4
    assert not thin[4:].any()                             # the edges look across 20 mm


def test_a_thick_box_has_no_thin_walls():
    v, f = box()
    assert not pc.thin_faces(v, f, 0.4).any()


def test_thin_walls_report_progress_and_can_be_cancelled():
    v, f = box(dz=0.2)
    steps = []
    assert pc.thin_faces(v, f, 0.4, steps.append) is not None and steps[-1] == 1.0
    assert pc.thin_faces(v, f, 0.4, None, lambda: True) is None

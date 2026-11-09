"""Files made to harm: each of these crashed PrintView3D, kept it loading for ever, read memory
that was not the file's, or had its text carried out as HTML. They must now end in an ordinary
error message, or simply show their text as it is."""

import base64
import json
import os
import struct
import zipfile

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.loaders import load_file  # noqa: E402
from printview3d.settings import Settings  # noqa: E402

NS = 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'
RELS = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="r" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
MESH = ('<mesh><vertices><vertex x="0" y="0" z="0"/><vertex x="10" y="0" z="0"/><vertex x="0" y="10" z="0"/>'
        '</vertices><triangles><triangle v1="0" v2="1" v3="{v3}"/></triangles></mesh>')


def make_3mf(path, resources, build='<item objectid="1"/>', metadata=""):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", f'<model unit="millimeter" {NS}>{metadata}<resources>{resources}'
                                       f'</resources><build>{build}</build></model>')
    return str(path)


def make_gltf(path, doc):
    doc.setdefault("asset", {"version": "2.0"})
    path.write_text(json.dumps(doc), encoding="utf-8")
    return str(path)


def data_uri(raw: bytes) -> str:
    return "data:application/octet-stream;base64," + base64.b64encode(raw).decode()


# ------------------------------------------------------------------ 3MF: triangles
@pytest.mark.parametrize("v3", ["3", "999999999", "-1", "-5"])
def test_3mf_triangle_outside_the_vertex_list_is_refused(tmp_path, v3):
    f = make_3mf(tmp_path / "bad.3mf", f'<object id="1" type="model">{MESH.format(v3=v3)}</object>')
    with pytest.raises(ValueError, match="vertices that do not exist"):
        load_file(f)


@pytest.mark.parametrize("v3", ["", "x", "1.5"])
def test_3mf_triangle_that_is_no_number_is_refused(tmp_path, v3):
    f = make_3mf(tmp_path / "bad.3mf", f'<object id="1" type="model">{MESH.format(v3=v3)}</object>')
    with pytest.raises(ValueError):
        load_file(f)


def test_3mf_with_a_good_triangle_still_opens(tmp_path):
    f = make_3mf(tmp_path / "ok.3mf", f'<object id="1" type="model">{MESH.format(v3=2)}</object>')
    m = load_file(f)
    assert m.n_triangles == 1


# ------------------------------------------------------------------ 3MF: components
def test_3mf_object_that_contains_itself_ends(tmp_path):
    comps = '<component objectid="1"/>' * 10
    f = make_3mf(tmp_path / "self.3mf",
                 f'<object id="1" type="model"><components>{comps}</components></object>')
    with pytest.raises(ValueError, match="no printable objects"):
        load_file(f)                               # at once; it used to run for ever


def test_3mf_objects_that_contain_each_other_end(tmp_path):
    res = ('<object id="1" type="model"><components><component objectid="2"/><component objectid="2"/>'
           '</components></object>'
           '<object id="2" type="model"><components><component objectid="1"/><component objectid="1"/>'
           f'<component objectid="3"/></components></object><object id="3" type="model">{MESH.format(v3=2)}</object>')
    m = load_file(make_3mf(tmp_path / "loop.3mf", res))
    assert m.n_triangles == 2                      # object 3, once through each of the two ways in


def test_3mf_that_places_objects_without_end_is_refused(tmp_path):
    # No object contains itself, but each places the next one ten times: 10^7 objects.
    res = ""
    for i in range(1, 8):
        comps = f'<component objectid="{i + 1}"/>' * 10
        res += f'<object id="{i}" type="model"><components>{comps}</components></object>'
    res += f'<object id="8" type="model">{MESH.format(v3=2)}</object>'
    with pytest.raises(ValueError, match="far more objects"):
        load_file(make_3mf(tmp_path / "many.3mf", res))


def test_3mf_same_object_placed_several_times_still_opens(tmp_path):
    comps = "".join(f'<component objectid="2" transform="1 0 0 0 1 0 0 0 1 {20 * i} 0 0"/>' for i in range(5))
    res = (f'<object id="2" type="model">{MESH.format(v3=2)}</object>'
           f'<object id="1" type="model"><components>{comps}</components></object>')
    m = load_file(make_3mf(tmp_path / "copies.3mf", res))
    assert m.n_triangles == 5


# ------------------------------------------------------------------ glTF: data outside the buffer
def _triangle_doc(**view):
    raw = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
    return {"buffers": [{"uri": data_uri(raw), "byteLength": len(raw)}],
            "bufferViews": [dict({"buffer": 0, "byteOffset": 0, "byteLength": len(raw)}, **view)],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
            "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}]}


def test_gltf_triangle_still_opens(tmp_path):
    assert load_file(make_gltf(tmp_path / "ok.gltf", _triangle_doc())).n_triangles == 1


@pytest.mark.parametrize("change", [
    {"view": {"byteStride": 4096}, "count": 3000},      # read far past the 36 bytes of the buffer
    {"view": {"byteStride": 16}, "count": 3},           # the last vertex ends 8 bytes too late
    {"view": {}, "count": 4},                           # one vertex too many
    {"view": {"byteOffset": 30}, "count": 3},
    {"view": {"byteOffset": -4}, "count": 3},
    {"view": {"byteStride": -12}, "count": 3},
    {"view": {}, "count": -1},
])
def test_gltf_data_outside_its_buffer_is_refused(tmp_path, change):
    doc = _triangle_doc(**change["view"])
    doc["accessors"][0]["count"] = change["count"]
    with pytest.raises(ValueError, match="damaged"):
        load_file(make_gltf(tmp_path / "bad.gltf", doc))


def test_gltf_interleaved_data_inside_its_buffer_still_opens(tmp_path):
    # position (12 bytes) + 4 bytes of something else per vertex: stride 16
    raw = b"".join(struct.pack("<3fI", *p, 7) for p in ((0, 0, 0), (1, 0, 0), (0, 1, 0)))
    doc = _triangle_doc(byteStride=16)
    doc["buffers"] = [{"uri": data_uri(raw), "byteLength": len(raw)}]
    doc["bufferViews"][0]["byteLength"] = len(raw)
    m = load_file(make_gltf(tmp_path / "interleaved.gltf", doc))
    assert m.n_triangles == 1
    size = m.parts[0].vertices.max(axis=0) - m.parts[0].vertices.min(axis=0)
    assert sorted(np.round(size).tolist()) == [0, 1000, 1000]        # metres -> millimetres


@pytest.mark.parametrize("index", [3, 70000, -1])
def test_gltf_triangle_outside_the_vertex_list_is_refused(tmp_path, index):
    doc = _triangle_doc()
    raw = base64.b64decode(doc["buffers"][0]["uri"].split(",", 1)[1]) + struct.pack("<3i", 0, 1, index)
    doc["buffers"] = [{"uri": data_uri(raw), "byteLength": len(raw)}]
    doc["bufferViews"].append({"buffer": 0, "byteOffset": 36, "byteLength": 12})
    doc["accessors"].append({"bufferView": 1, "componentType": 5125, "count": 3, "type": "SCALAR"})
    doc["meshes"][0]["primitives"][0]["indices"] = 1
    with pytest.raises(ValueError, match="vertices that do not exist"):
        load_file(make_gltf(tmp_path / "bad.gltf", doc))


# ------------------------------------------------------------------ glTF: nodes
def test_gltf_node_that_is_its_own_child_ends(tmp_path):
    doc = _triangle_doc()
    doc["nodes"] = [{"mesh": 0, "children": [0, 0, 0]}]
    assert load_file(make_gltf(tmp_path / "self.gltf", doc)).n_triangles == 1     # it used to run for ever


def test_gltf_nodes_listed_as_children_again_and_again_end(tmp_path):
    doc = _triangle_doc()
    n = 40
    doc["nodes"] = [{"children": [i + 1, i + 1]} for i in range(n)] + [{"mesh": 0}]
    doc["scenes"] = [{"nodes": [0]}]
    assert load_file(make_gltf(tmp_path / "fan.gltf", doc)).n_triangles == 1      # not 2^40 times


# ------------------------------------------------------------------ text from a file is only text
@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    from PySide6.QtCore import QEvent
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    w.resize(1280, 760)
    w.show()
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


HTML_TITLE = '<img src="/no/such/picture.png">'
HTML_NAME = "<h1>BIG</h1>"
HTML_LONG = "<b>bold</b> " + "and a long description " * 12


def _html_3mf(tmp_path):
    from xml.sax.saxutils import escape, quoteattr
    meta = (f'<metadata name="Title">{escape(HTML_TITLE)}</metadata>'
            f'<metadata name="Description">{escape(HTML_LONG)}</metadata>')
    return make_3mf(tmp_path / "html.3mf",
                    f'<object id="1" name={quoteattr(HTML_NAME)} type="model">{MESH.format(v3=2)}</object>', metadata=meta)


def test_text_from_a_file_is_shown_as_plain_text(app, window, tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    window.load_sync(_html_3mf(tmp_path))
    app.processEvents()
    found = set()
    for label in window.findChildren(QLabel):
        text = label.text().replace("​", "")
        for what in (HTML_TITLE, HTML_NAME, HTML_LONG.strip()):
            if what[:12] in text:
                found.add(what)
                assert label.textFormat() == Qt.PlainText, text
                tip = label.toolTip()
                assert not tip or "<h1>" not in tip and "<img" not in tip, tip
    assert found == {HTML_TITLE, HTML_NAME, HTML_LONG.strip()}


def test_plain_tip_shows_html_as_text():
    from printview3d.ui.main_window import plain_tip
    assert plain_tip("Bracket\n20 × 10 × 5 mm") == "Bracket\n20 × 10 × 5 mm"         # ordinary text: unchanged
    tip = plain_tip('<img src="x.png">\n12 triangles')
    assert "<img" not in tip and "&lt;img" in tip and "<br>" in tip


def test_error_message_is_plain_text(app, window, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    seen = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: seen.append((self.textFormat(), self.text())) or 0)
    window._load_token = 5
    window._on_failed(5, 'ValueError: <img src="x.png"> in the ZIP is damaged.')
    assert seen == [(Qt.PlainText, 'ValueError: <img src="x.png"> in the ZIP is damaged.')]

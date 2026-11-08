"""The start page's recent files and their preview card: Creality Print's G-code pictures, file names
with "&" or "<", and long names without spaces."""

import base64
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402

# A 2 x 1 PNG (red, blue) and a 4 x 4 PNG.
PNG_2x1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAIAAAB7QOjdAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAD0lE"
                           "QVQImWP4z8DAwPAfAAcAAf/89wURAAAAAElFTkSuQmCC")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _png(w: int, h: int) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QColor, QImage
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor("teal"))
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def _photo(w: int, h: int) -> bytes:
    """A picture with detail (a photo-sized PNG; a plain colour packs to under 2 KB, like an icon)."""
    import random
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QImage
    rnd = random.Random(1)
    img = QImage(w, h, QImage.Format_RGB32)
    for y in range(h):
        for x in range(w):
            img.setPixel(x, y, rnd.getrandbits(24))
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def _block(word: str, size: str, data: bytes) -> str:
    return f"; {word} begin {size} {len(data)}\n; " + base64.b64encode(data).decode() + f"\n; {word} end\n"


def test_creality_print_pictures_are_found(app, tmp_path):
    """Creality Print writes "png begin 96*96 ..." and "thumbnail begin 300 300 ..." (no "x"): the
    pictures were missed, so its G-code had no picture on the start page nor in the side panel."""
    from PySide6.QtGui import QImage
    from printview3d.loaders import read_thumbnail
    from printview3d.loaders.gcode import parse_gcode_file
    small, big = _png(2, 2), _png(6, 6)
    g = tmp_path / "creality.gcode"
    g.write_text(_block("png", "2*2 7757 0 95 192", small) + _block("thumbnail", "6 6", big)
                 + "G1 X1 Y1 E1\nG1 X2 Y2 E2\n", encoding="utf-8")
    for data in (read_thumbnail(str(g)), parse_gcode_file(str(g)).thumbnail):
        img = QImage.fromData(data)
        assert (img.width(), img.height()) == (6, 6)          # the largest of the two


def test_long_names_without_spaces_wrap_instead_of_being_cut(app):
    from PySide6.QtGui import QFont, QFontMetrics
    from printview3d.ui import main_window as mw
    f = QFont()
    f.setPixelSize(14)
    fm = QFontMetrics(f)
    name = "3DBenchy_PLA_K1C_220_60_with_a_much_longer_name.gcode"
    out = mw.wrap_lines(name, f, 200)
    lines = out.split("\n")
    assert len(lines) > 1 and "".join(lines) == name
    assert all(fm.horizontalAdvance(line) <= 200 for line in lines)
    words = mw.wrap_lines("a printed file with spaces in its rather long name.gcode", f, 200).split("\n")
    assert len(words) > 1 and all(not w.startswith(" ") or w.strip() for w in words)


def test_names_with_ampersand_and_angle_brackets_show_as_they_are(app, tmp_path):
    from printview3d.ui import main_window as mw
    folder = tmp_path / "Tom & Jerry"
    folder.mkdir()
    amp = folder / "Tom & Jerry plate.gcode"
    amp.write_text("G1 X1 Y1\n", encoding="utf-8")
    tag = tmp_path / "<b>bold vase.gcode"
    try:
        tag.write_text("G1 X1 Y1\n", encoding="utf-8")
    except OSError:                                            # Windows doesn't allow < > in names
        tag = None
    s = Settings(str(tmp_path / "settings.json"))
    for p in [amp] + ([tag] if tag else []):
        s.add_recent(str(p))
    w = mw.MainWindow(s)
    try:
        w.resize(1280, 800)
        w.show()
        app.processEvents()
        buttons = {os.path.basename(b.path): b for b in w.findChildren(mw._RecentButton)}
        assert buttons["Tom & Jerry plate.gcode"].text() == "Tom && Jerry plate.gcode"    # shows one "&"
        menu = [a.text() for a in w.recent_menu.actions() if "Jerry" in a.text()]
        assert menu and menu[0].startswith("Tom && Jerry plate.gcode")
        card = w.recent_preview
        w._recent_hover(str(amp))
        assert card.name.text().replace("\n", "") == "Tom & Jerry plate.gcode"
        if tag:
            from PySide6.QtCore import Qt
            w._recent_hover(str(tag))
            assert card.name.textFormat() == Qt.PlainText
            assert card.name.text().replace("\n", "") == "<b>bold vase.gcode"
    finally:
        w.close()


# ------------------------------------------------------------------ ZIP files
def _zip(path, files: dict):
    import zipfile
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return str(path)


def _3mf_bytes(picture: bytes) -> bytes:
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("3D/3dmodel.model", "<model/>")
        z.writestr("Metadata/thumbnail.png", picture)
    return buf.getvalue()


def test_zip_preview_prefers_the_makers_picture_then_3mf_then_gcode(app, tmp_path):
    from PySide6.QtGui import QImage
    from printview3d.loaders import read_thumbnail
    photo, plate, sliced = _photo(64, 48), _png(30, 30), _png(20, 10)
    icon = _png(4, 4)                                                  # under 2 KB: an icon, skipped

    def size(data):
        img = QImage.fromData(data)
        return img.width(), img.height()

    both = _zip(tmp_path / "printables.zip", {"files/part.3mf": _3mf_bytes(plate), "images/photo.png": photo})
    assert size(read_thumbnail(both)) == (64, 48)
    only_3mf = _zip(tmp_path / "k2.zip", {"logo.png": icon, "Tray.3mf": _3mf_bytes(plate)})
    assert size(read_thumbnail(only_3mf)) == (30, 30)
    gcode = _block("png", "20*10 1 2 3", sliced) + "G1 X1 Y1 E1\n"
    only_gcode = _zip(tmp_path / "print.zip", {"model.stl": b"solid x\nendsolid x\n", "print.gcode": gcode})
    assert size(read_thumbnail(only_gcode)) == (20, 10)
    nothing = _zip(tmp_path / "plain.zip", {"model.stl": b"solid x\nendsolid x\n", "readme.txt": b"hi",
                                            "__MACOSX/._photo.png": photo})
    assert read_thumbnail(nothing) is None
    broken = tmp_path / "broken.zip"
    broken.write_bytes(b"PK\x03\x04 not really a zip")
    assert read_thumbnail(str(broken)) is None


def test_the_preview_card_can_be_switched_off(app, tmp_path):
    from printview3d.ui import main_window as mw
    from printview3d.ui.settings_dialog import SettingsDialog
    g = tmp_path / "x.gcode"
    g.write_text(_block("thumbnail", "6x6", _png(6, 6)) + "G1 X1 Y1\n", encoding="utf-8")
    s = Settings(str(tmp_path / "settings.json"))
    s.add_recent(str(g))
    w = mw.MainWindow(s)
    try:
        w.resize(1280, 800)
        w.show()
        app.processEvents()
        w._recent_hover(str(g))
        assert w.recent_preview.isVisible()
        w.open_settings("viewer")                                       # as from the menu
        d = w.findChild(SettingsDialog)
        titles = [b.title() for b in d.pages.currentWidget().widget().findChildren(type(d.findChild(
            type(d.toolbar_joined_cb.parentWidget()))))]
        assert titles.index("Build plate") < titles.index("Measure, View and Check") \
            < titles.index("Start page") < titles.index("Graphics")
        assert d.recent_preview_cb.isChecked()
        d.recent_preview_cb.setChecked(False)
        d._save()                                                      # OK
        app.processEvents()
        assert s.get("recent_preview") is False and not w.recent_preview.isVisible()
        w._recent_hover(str(g))
        assert not w.recent_preview.isVisible()                       # stays hidden, nothing read
    finally:
        w.close()

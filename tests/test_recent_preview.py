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

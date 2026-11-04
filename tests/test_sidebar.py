"""The side panel: Objects first and Details last (foldable), the file type and size instead of the
file name, and a colour picker for every object."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CUBE = os.path.join(DATA, "cube_binary.stl")
TWO_PARTS = os.path.join(DATA, "two_parts.3mf")
GCODE = os.path.join(DATA, "cylinder.gcode")
PAINTED = os.path.join(DATA, "cube_colors.off")       # one colour per vertex


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _make(app, tmp_path):
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    w.resize(1280, 760)
    w.show()
    return w


def _close(app, w):
    from PySide6.QtCore import QEvent
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


@pytest.fixture
def window(app, tmp_path):
    w = _make(app, tmp_path)
    yield w
    _close(app, w)


def _order(w):
    lay = w.side_layout
    return [lay.itemAt(i).widget() for i in range(lay.count()) if lay.itemAt(i).widget() is not None]


# ------------------------------------------------------------ order
def test_objects_come_first_and_details_last(window):
    w = window
    order = _order(w)
    for first, then in ((w.objects_box, w.view_box), (w.view_box, w.measure_box), (w.measure_box, w.layers_box),
                        (w.layers_box, w.features_box), (w.features_box, w.details_box)):
        assert order.index(first) < order.index(then)
    assert order[-1] is w.details_box
    boxes = [b for b in order if b.__class__.__name__ == "QGroupBox"]
    assert boxes[0] is w.zip_box or boxes[0] is w.objects_box          # nothing above the objects
    assert order.index(w.objects_box) < order.index(w.embedded_box)


# ------------------------------------------------------------ file type and size
def test_file_name_is_not_in_the_panel_but_type_and_size_are(window):
    w = window
    assert not hasattr(w, "name_label")
    w.load_sync(CUBE)
    text = w.kind_label.text()
    assert text.startswith("Filetype: STL") and "Size: " in text
    assert "cube_binary" not in text
    assert "cube_binary" in w.windowTitle()                             # the name is in the title bar
    w.load_sync(TWO_PARTS)
    assert w.kind_label.text().startswith("Filetype: 3MF")
    w.load_sync(GCODE)
    assert w.kind_label.text().startswith("Filetype: G-code")


@pytest.mark.parametrize("nbytes,text", [(350, "0.34 KB"), (1536, "1.50 KB"), (51200, "50.0 KB"),
                                         (350 * 1024, "350 KB"), (1024 * 1024, "1.00 MB"),
                                         (1.5 * 1024 * 1024, "1.50 MB"), (25 * 1024 * 1024, "25.0 MB")])
def test_size_text(nbytes, text):
    from printview3d.ui.main_window import MainWindow
    assert MainWindow._size_text(nbytes) == text


# ------------------------------------------------------------ details: foldable, remembered
def test_details_fold_and_the_choice_is_remembered(app, tmp_path):
    w = _make(app, tmp_path)
    try:
        w.load_sync(TWO_PARTS)
        assert w.details_body.isVisible() and "▾" in w.details_toggle.text()
        w.set_details_open(False)
        assert w.details_body.isHidden() and "▸" in w.details_toggle.text()
        assert w.settings.get("details_open") is False
        w.load_sync(CUBE)                                              # the next file: still folded
        assert w.details_body.isHidden()
    finally:
        _close(app, w)
    w2 = _make(app, tmp_path)                                          # next start: still folded
    try:
        w2.load_sync(TWO_PARTS)
        assert w2.details_body.isHidden() and w2.details_box.isVisible()
        w2.set_details_open(True)
        assert w2.details_body.isVisible() and w2.settings.get("details_open") is True
    finally:
        _close(app, w2)


# ------------------------------------------------------------ colours
def _boxes(w):
    return [b for b in w.objects_box.findChildren(type(w.view_btn)) if b.objectName() == "colorBox"]


def _color(actor):
    return tuple(round(v * 255) for v in actor.GetProperty().GetColor())


def _pick(monkeypatch, hex_color):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QColorDialog
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *a, **k: QColor(hex_color)))


def test_each_object_has_its_own_colour_box(window, monkeypatch):
    w = window
    w.load_sync(TWO_PARTS)
    boxes = _boxes(w)
    assert len(boxes) == 2 and w.objects_box.isVisible()
    first, second = (a for a in w.scene.model_actors)
    before_second = _color(second)
    _pick(monkeypatch, "#112233")
    boxes[0].click()                                                   # a click opens the picker
    assert _color(first) == (0x11, 0x22, 0x33) and _color(second) == before_second
    assert boxes[0].color == "#112233" and boxes[1].color != "#112233"
    _pick(monkeypatch, "#445566")
    boxes[1].click()
    assert _color(second) == (0x44, 0x55, 0x66) and _color(first) == (0x11, 0x22, 0x33)   # independent
    assert w.scene.part_color_override(0) == "#112233" and w.scene.part_color_override(1) == "#445566"


def test_one_object_can_be_coloured_too(window, monkeypatch):
    w = window
    w.load_sync(CUBE)
    boxes = _boxes(w)
    assert len(boxes) == 1 and w.objects_box.isVisible()
    assert w.objects_box.findChildren(type(w.objects_box)) == []       # no checkbox to hide the only object
    _pick(monkeypatch, "#aa5500")
    boxes[0].click()
    assert _color(w.scene.model_actors[0]) == (0xAA, 0x55, 0x00)


def test_cancelling_the_picker_changes_nothing(window, monkeypatch):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QColorDialog
    w = window
    w.load_sync(CUBE)
    before = _color(w.scene.model_actors[0])
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *a, **k: QColor()))   # invalid: cancelled
    _boxes(w)[0].click()
    assert _color(w.scene.model_actors[0]) == before and w.scene.part_color_override(0) is None


def test_original_colour_comes_back(window, monkeypatch):
    w = window
    w.load_sync(CUBE)
    actor = w.scene.model_actors[0]
    before = _color(actor)
    _pick(monkeypatch, "#00ff00")
    _boxes(w)[0].click()
    assert _color(actor) == (0, 255, 0)
    w.scene.set_part_color(0, None)
    assert _color(actor) == before and w.scene.part_color_override(0) is None


def test_painted_parts_take_the_colour_and_get_their_paint_back(window):
    w = window
    w.load_sync(PAINTED)
    mapper = w.scene.model_actors[0].GetMapper()
    assert mapper.GetScalarVisibility()
    w.scene.set_part_color(0, "#0000ff")
    assert not mapper.GetScalarVisibility() and _color(w.scene.model_actors[0]) == (0, 0, 255)
    w.scene.set_part_color(0, None)
    assert mapper.GetScalarVisibility()


def test_colours_are_not_saved_and_do_not_survive_another_file(window, monkeypatch):
    w = window
    w.load_sync(CUBE)
    _pick(monkeypatch, "#00ff00")
    _boxes(w)[0].click()
    assert not any("color" in k or "colour" in k for k in w.settings.data)   # nothing stored
    w.load_sync(CUBE)                                                  # the same file again: file colours
    assert w.scene.part_color_override(0) is None and _color(w.scene.model_actors[0]) != (0, 255, 0)


def test_the_colour_box_follows_a_change_of_language_rebuild(window, monkeypatch):
    w = window
    w.load_sync(TWO_PARTS)
    _pick(monkeypatch, "#112233")
    _boxes(w)[0].click()
    w._refresh_panel()                                                 # the panel is built again
    assert _boxes(w)[0].color == "#112233"


# ------------------------------------------------------------ buttons in a narrow panel
def _fit_buttons(w):
    return [b for b in w.view_box.findChildren(type(w.view_btn)) + w.measure_box.findChildren(type(w.view_btn))
            if b.objectName() == "sectionButton"]


def _style(b):
    from PySide6.QtCore import Qt
    return {Qt.ToolButtonTextBesideIcon: "both", Qt.ToolButtonTextOnly: "text", Qt.ToolButtonIconOnly: "icon"}[
        b.toolButtonStyle()]


def _set_widths(w, app, width):
    for b in _fit_buttons(w):
        b.setFixedWidth(width)
    app.processEvents()


def test_buttons_shrink_their_font_then_lose_the_icon_then_the_text_but_never_cut_characters(window, app):
    w = window
    w.load_sync(CUBE)
    w.act_view.setChecked(True)
    btn = _fit_buttons(w)[3]                              # "Clip facing you"
    action = btn.defaultAction()
    steps = []
    for width in range(400, 20, -6):
        _set_widths(w, app, width)
        steps.append((_style(btn), round(btn.font().pointSizeF(), 1)))
        # whatever shows, no character is cut: the text is the action's full text, or not shown at all
        assert btn.text() == action.text()
    styles = [st for st, _ in steps]
    assert styles[0] == "both" and styles[-1] == "icon"
    assert styles.index("icon") > styles.index("text") > styles.index("both")        # in that order
    sizes = [sz for st, sz in steps if st == "both"]
    assert sizes == sorted(sizes, reverse=True) and sizes[0] > sizes[-1]            # smaller font before the icon goes
    assert styles == sorted(styles, key=["both", "text", "icon"].index)             # never back and forth


def test_the_buttons_of_a_group_shrink_together(window, app):
    w = window
    w.load_sync(CUBE)
    w.act_view.setChecked(True)
    buttons = _fit_buttons(w)[:4]                         # the four view buttons
    for width in (400, 170, 140, 110, 28):
        _set_widths(w, app, width)
        assert len({(_style(b), round(b.font().pointSizeF(), 1)) for b in buttons}) == 1   # all alike
    # one narrow button pulls its group along, but not the other section
    _set_widths(w, app, 400)
    buttons[3].setFixedWidth(60)
    app.processEvents()
    assert len({_style(b) for b in buttons}) == 1 and _style(buttons[0]) != "both"


def test_a_wide_panel_keeps_icon_and_full_font(window, app):
    w = window
    w.load_sync(CUBE)
    w.act_view.setChecked(True)
    _set_widths(w, app, 300)
    for b in _fit_buttons(w):
        assert _style(b) == "both"


# ------------------------------------------------------------ bold file info, reopening the panel
def test_filetype_and_size_are_bold(window, app):
    from printview3d.ui import theme
    theme.apply_theme(app, "dark")
    w = window
    w.load_sync(CUBE)
    app.processEvents()
    assert w.kind_label.objectName() == "kindLabel"
    assert "QLabel#kindLabel" in app.styleSheet()
    css = app.styleSheet().split("QLabel#kindLabel")[1].split("}")[0]
    assert "font-weight: 700" in css


def test_the_view_and_measure_buttons_open_a_closed_side_panel(window, app):
    w = window
    w.load_sync(CUBE)
    app.processEvents()
    i = w.splitter.indexOf(w.side_scroll)
    sizes = w.splitter.sizes()
    before = sizes[i]
    assert before >= 290
    total = sum(sizes)
    w.splitter.setSizes([total, 0] if i == 1 else [0, total])               # dragged shut
    w.splitter.splitterMoved.emit(0, 0)
    app.processEvents()
    assert w.splitter.sizes()[i] == 0
    w.act_view.trigger()                                                     # View: opens it again
    assert w.splitter.sizes()[i] == pytest.approx(before, abs=2) and w.view_box.isVisible()
    w.splitter.setSizes([total, 0] if i == 1 else [0, total])
    app.processEvents()
    w.act_measure.trigger()                                                  # Measure: the same
    assert w.splitter.sizes()[i] == pytest.approx(before, abs=2) and w.measure_box.isVisible()


def test_an_open_side_panel_keeps_its_width(window, app):
    w = window
    w.load_sync(CUBE)
    app.processEvents()
    i = w.splitter.indexOf(w.side_scroll)
    total = sum(w.splitter.sizes())
    w.splitter.setSizes([total - 350, 350] if i == 1 else [350, total - 350])
    w.splitter.splitterMoved.emit(0, 0)
    w.act_view.trigger()
    assert w.splitter.sizes()[i] == pytest.approx(350, abs=2)                # not reset to the default


def test_the_colour_hint_stays_on_one_line_even_in_the_narrowest_panel(window, app):
    from PySide6.QtGui import QFontMetrics
    w = window
    w.load_sync(TWO_PARTS)
    i = w.splitter.indexOf(w.side_scroll)
    total = sum(w.splitter.sizes())
    for width in (420, 350, 290):                       # the widest, the usual and the narrowest
        w.splitter.setSizes([total - width, width] if i == 1 else [width, total - width])
        for _ in range(4):
            app.processEvents()
        hint = w.objects_hint
        assert not hint.wordWrap() and hint.isVisible()
        fm = QFontMetrics(hint.font())
        assert fm.horizontalAdvance(hint.text()) <= hint.width()          # whole text, one line
        assert hint.height() <= fm.height() * 2 and len(hint.text()) < 50  # and a short text
    assert hint.font().pointSizeF() <= w.font().pointSizeF()

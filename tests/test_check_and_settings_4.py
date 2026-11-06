"""Fit's key, the Settings button, the nozzle width in millimetres, the dots beside problems,
tooltips inside the window, and automatic grid numbers that follow the zoom."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d import units  # noqa: E402
from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CUBE = os.path.join(HERE, "data", "cube_binary.stl")


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    from PySide6.QtCore import QEvent
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(str(tmp_path / "settings.json")))
    w.resize(1280, 800)
    w.show()
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()
    units.set_unit("mm")


# ------------------------------------------------------------ toolbar
def test_fit_says_its_key(window):
    assert window.act_fit.text() == "Fit (R)" and window.act_fit.toolTip().endswith("(R)")


def test_settings_button_right_of_the_theme_button(window):
    tb = window.findChild(type(window.addToolBar("x")), "mainToolbar")
    widgets = [tb.widgetForAction(a) for a in tb.actions()]
    i = widgets.index(window.theme_btn)
    assert widgets[i + 1] is window.settings_btn
    assert window.settings_btn.defaultAction() is window.act_settings
    assert window.settings_btn.toolTip() == "Settings" and not window.settings_btn.icon().isNull()


# ------------------------------------------------------------ nozzle width in mm
def _inches(w, nozzle_too=False):
    w.settings.set("units", "in")
    w.settings.set("nozzle_in_inches", nozzle_too)
    w._apply_grid_label_settings()


def test_nozzle_stays_in_mm_with_inches(window):
    w = window
    _inches(w)
    assert w.check_nozzle.suffix().strip() == "mm" and w.check_nozzle.value() == pytest.approx(0.4)
    assert w.check_loose.suffix().strip() == "in"
    _inches(w, nozzle_too=True)                                  # Settings: in inches too
    assert w.check_nozzle.suffix().strip() == "in"
    assert w.check.nozzle == pytest.approx(0.4)                  # the same nozzle, shown in inches


def test_settings_nozzle_box(window):
    from printview3d.ui.settings_dialog import SettingsDialog
    dlg = SettingsDialog(window.settings, window, {}, page="language")
    assert not dlg.nozzle_in_cb.isEnabled()                      # millimetres: nothing to choose
    dlg.units_combo.setCurrentIndex(dlg.units_combo.findData("in"))
    assert dlg.nozzle_in_cb.isEnabled() and not dlg.nozzle_in_cb.isChecked()
    # beside the unit dropdown
    assert dlg.nozzle_in_cb.parentWidget() is dlg.units_combo.parentWidget()
    dlg.nozzle_in_cb.setChecked(True)
    dlg._save(close=True)
    assert window.settings.get("nozzle_in_inches") is True and window.settings.get("units") == "in"


# ------------------------------------------------------------ Check section
def test_dot_beside_problems_only(window):
    from printview3d.loaders.mesh import MeshPart, ModelData
    from printview3d.ui import theme
    from test_print_check import box
    w = window
    w.load_sync(CUBE)
    v, f = box()
    w._show_model(ModelData([MeshPart("open", v, f[1:])]))      # a box with one triangle missing
    w.model = ModelData([MeshPart("open", v, f[1:])])
    w.act_check.trigger()
    texts = {k: r[1].text() for k, r in w.check_rows.items()}
    dot = "●"
    assert dot in texts["open"] and theme.colors()["primary"] in texts["open"]
    assert dot not in texts["flipped"] and texts["flipped"] == "none"
    # overhangs are not a problem as such (most models have them): a count, no dot
    real = w.check.counts
    w.check.counts = lambda: dict(real(), overhang=120, thin=4)
    w._update_check_panel()
    assert w.check_rows["overhang"][1].text() == "120 faces"
    assert dot in w.check_rows["thin"][1].text()
    assert w.check_mesh_title.text() == "Mesh problems"


# ------------------------------------------------------------ tooltips
def test_long_tooltips_wrap_inside_the_window(app):
    from PySide6.QtCore import QRect
    from PySide6.QtWidgets import QLabel
    from printview3d.ui import tooltips
    tip = QLabel("Jumps to the nearest corner, the middle of an edge or a point on an edge, so a "
                 "measurement starts exactly there. It is on at every start of PrintView3D.")
    tip.adjustSize()
    tip.move(560, 200)                                           # near the window's right edge
    area = QRect(100, 100, 500, 300)
    tooltips.fit(tip, area)
    assert tip.wordWrap() and area.contains(tip.geometry())
    short = QLabel("Settings")
    short.adjustSize()
    short.move(200, 200)
    tooltips.fit(short, area)
    assert not short.wordWrap() and short.pos().x() == 200       # a short one in the window: as it was


# ------------------------------------------------------------ grid numbers follow the zoom
def test_auto_candidates_start_at_the_fine_lines():
    from printview3d.ui import grid_labels as gl
    assert gl.auto_candidates(10, 50)[:5] == [10, 20, 50, 100, 250]
    assert gl.auto_candidates(20, 100)[:4] == [20, 40, 100, 200]
    assert gl.auto_step(10, 50, px_per_mm=10, need_px=60, length=250) == 10    # zoomed in
    assert gl.auto_step(10, 50, px_per_mm=1, need_px=60, length=250) == 100    # zoomed out


def test_numbers_follow_the_zoom(window):
    w = window
    w.load_sync(CUBE)
    w.plotter.ren_win.SetSize(1000, 700)
    g = w.grid_labels
    g.set_enabled(True)
    minor = w.scene.grid_drawn[0]
    cam = w.plotter.renderer.GetActiveCamera()

    def step():
        g._layout()
        xs = sorted({round(a[0], 6) for t, a in g.items if a[1] == g.items[0][1][1]})
        return min(b - a for a, b in zip(xs, xs[1:]))

    w.set_view("top")
    cam.Zoom(4.0)                                                # close to the 20 mm cube
    near = step()
    cam.Zoom(0.1)                                                # far away
    far = step()
    assert near >= minor - 1e-6 and far > near

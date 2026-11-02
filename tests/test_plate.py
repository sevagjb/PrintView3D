"""Build plate: the printer's plate, a plate that grows to fit the model, a plate of your own
size, or an endless grid (issue #61)."""

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from printview3d.settings import Settings  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LONG = os.path.join(DATA, "larger_than_plate.3mf")    # 420 mm rail, 220 x 220 mm printer
TWO_PARTS = os.path.join(DATA, "two_parts.3mf")        # fits its 350 x 350 mm plate
CUBE = os.path.join(DATA, "cube_binary.stl")           # no printer plate in the file
GCODE = os.path.join(DATA, "cylinder.gcode")

PRINTER = (0.0, 220.0, 0.0, 220.0)
MODEL = (-100.0, 320.0, 60.0, 210.0)                    # footprint of LONG (x, y)


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def settings(tmp_path):
    return Settings(str(tmp_path / "settings.json"))


@pytest.fixture
def window(app, settings):
    from PySide6.QtCore import QEvent
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(settings)
    yield w
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def _plate(w):
    """(xmin, xmax, ymin, ymax) of the plate in the 3D view."""
    return tuple(float(v) for v in w.scene.bed_bounds[:4])


def _covers(plate, fp):
    return plate[0] <= fp[0] and plate[1] >= fp[1] and plate[2] <= fp[2] and plate[3] >= fp[3]


def test_default_is_the_printers_plate(window):
    w = window
    assert w.settings.get("plate_mode") == "printer"
    w.load_sync(LONG)
    assert _plate(w) == PRINTER                          # as before: the rail sticks out
    assert not _covers(_plate(w), MODEL)
    assert "bed_plate" in w.scene.p.actors


def test_fit_grows_the_plate_around_the_model(window):
    w = window
    w.load_sync(LONG)
    w.choose_plate_mode("fit")
    plate = _plate(w)
    assert _covers(plate, MODEL) and _covers(plate, PRINTER)
    assert plate == (-120.0, 340.0, 0.0, 230.0)          # model + 20 mm margin, and the printer's plate


def test_fit_keeps_the_printers_plate_when_the_model_fits(window):
    w = window
    w.choose_plate_mode("fit")
    w.load_sync(TWO_PARTS)
    assert _plate(w) == (0.0, 350.0, 0.0, 350.0)
    assert w.scene._real_bed


def test_custom_size_starts_at_the_printers_origin(window):
    w = window
    w.settings.set("plate_size", [500, 400])
    w.load_sync(LONG)
    w.choose_plate_mode("custom", ask=False)
    assert _plate(w) == (0.0, 500.0, 0.0, 400.0)


def test_custom_size_without_printer_plate_is_centred(window):
    w = window
    w.settings.set("plate_size", [100, 60])
    w.choose_plate_mode("custom", ask=False)
    w.load_sync(CUBE)                                    # 20 mm cube at 0..20
    assert _plate(w) == (-40.0, 60.0, -20.0, 40.0)


def test_custom_size_asks_and_cancel_changes_nothing(window, monkeypatch):
    from printview3d.ui import main_window as mw
    w = window
    w.load_sync(LONG)
    monkeypatch.setattr(mw.PlateSizeDialog, "exec", lambda self: 0)
    w.choose_plate_mode("custom")
    assert w.settings.get("plate_mode") == "printer" and _plate(w) == PRINTER
    assert w.plate_actions["printer"].isChecked()

    def ok(self):
        self.width_spin.setValue(260)
        self.depth_spin.setValue(240)
        return 1
    monkeypatch.setattr(mw.PlateSizeDialog, "exec", ok)
    w.choose_plate_mode("custom")
    assert w.settings.get("plate_mode") == "custom"
    assert w.settings.get("plate_size") == [260, 240]
    assert _plate(w) == (0.0, 260.0, 0.0, 240.0)
    assert "260" in w.plate_actions["custom"].text()


def test_plate_size_dialog_limits(app):
    from printview3d.ui.main_window import PlateSizeDialog
    d = PlateSizeDialog((3, 99999))
    try:
        assert d.plate_size() == (PlateSizeDialog.MIN, PlateSizeDialog.MAX)
    finally:
        d.deleteLater()


def test_infinite_grid_fades_out(window):
    w = window
    w.load_sync(LONG)
    w.choose_plate_mode("infinite")
    actors = w.scene.p.actors
    assert "bed_plate" not in actors and "bed_edge" not in actors     # no surface, no edge
    major = actors["bed_major"].mapper.dataset
    pts = np.asarray(major.points)
    alpha = np.asarray(major.point_data["rgba"])[:, 3]
    cx = (MODEL[0] + MODEL[1]) / 2
    cy = (MODEL[2] + MODEL[3]) / 2
    dist = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    assert pts[:, 0].max() - pts[:, 0].min() >= 2000                 # far beyond the model
    assert alpha[dist < 100].min() > 200                              # clear near the model
    assert alpha[dist > dist.max() * 0.72].max() == 0                 # gone at the far end
    assert w.scene.bed_bounds[:4] == pytest.approx((-120, 340, 40, 230))   # Fit / pivot: the model


def test_infinite_grid_survives_a_theme_change(window):
    from printview3d.ui import theme
    w = window
    w.load_sync(LONG)
    w.choose_plate_mode("infinite")
    w.scene.set_colors(theme.colors("light"))
    assert "bed_major" in w.scene.p.actors and "bed_plate" not in w.scene.p.actors
    rgb = np.asarray(w.scene.p.actors["bed_major"].mapper.dataset.point_data["rgba"])[0, :3]
    expected = tuple(int(theme.colors("light")["grid_major"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    assert tuple(rgb) == expected


@pytest.mark.parametrize("mode", ["printer", "fit", "custom", "infinite"])
def test_every_mode_works_for_gcode_and_stl(window, mode):
    w = window
    w.choose_plate_mode(mode, ask=False)
    for path in (GCODE, CUBE):
        w.load_sync(path)
        assert w.scene.bed_bounds is not None
        assert w.scene._bed_actor_names


def test_choosing_a_plate_shows_it(window):
    w = window
    w.load_sync(LONG)
    w.act_bed.setChecked(False)
    w.choose_plate_mode("infinite")
    assert w.act_bed.isChecked()
    assert w.scene.p.actors["bed_major"].GetVisibility()


def test_menu_on_the_plate_button(window):
    from PySide6.QtWidgets import QToolButton
    w = window
    assert w.plate_btn.menu() is w.plate_menu
    assert w.plate_btn.popupMode() == QToolButton.MenuButtonPopup
    assert list(w.plate_actions) == ["printer", "fit", "custom", "infinite"]
    assert w.plate_actions["printer"].isChecked()
    w.choose_plate_mode("fit")
    assert w.plate_actions["fit"].isChecked() and not w.plate_actions["printer"].isChecked()


def test_choice_is_remembered(app, settings, window):
    from printview3d.ui import main_window as mw
    window.choose_plate_mode("infinite")
    again = mw.MainWindow(Settings(settings.path))
    try:
        assert again.scene.plate_mode == "infinite"
        again.load_sync(LONG)
        assert "bed_plate" not in again.scene.p.actors and "bed_major" in again.scene.p.actors
    finally:
        again.close()
        again.deleteLater()


def test_setting_in_the_settings_window(app, settings):
    from printview3d.ui import settings_dialog as sd
    dlg = sd.SettingsDialog(settings, page="viewer")
    try:
        assert dlg.plate_combo.currentData() == "printer"
        assert not dlg.plate_size_row.isEnabled()
        dlg.plate_combo.setCurrentIndex(dlg.plate_combo.findData("custom"))
        assert dlg.plate_size_row.isEnabled()
        dlg.plate_w_spin.setValue(400)
        dlg.plate_d_spin.setValue(320)
        dlg._save()
    finally:
        dlg.deleteLater()
        app.processEvents()
    s = Settings(settings.path)
    assert s.get("plate_mode") == "custom" and s.get("plate_size") == [400, 320]


def test_old_or_broken_settings_fall_back(window):
    w = window
    w.settings.set("plate_size", "nonsense")
    w.settings.set("plate_mode", "giant")
    w.scene.set_plate_mode(w.settings.get("plate_mode"), w._plate_size())
    assert w.scene.plate_mode == "printer"
    assert w._plate_size() == (300.0, 300.0)

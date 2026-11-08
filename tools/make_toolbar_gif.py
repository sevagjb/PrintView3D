"""The short animation of Settings -> Toolbar for the README, the website and What's new (0.30).

The real toolbar on top and the real Settings page below it, step by step: Check and Measure
switched off, the labels shortened to the name, then icons only, the buttons joined, and back to
the defaults. An orange frame shows what changes. No text of its own, so one GIF serves every
language. Few distinct frames and a small palette keep it small.

    xvfb-run -a -s "-screen 0 1600x1000x24" python tools/make_toolbar_gif.py
Result: docs/assets/toolbar-settings.gif
"""

from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtCore import QPoint, QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QToolButton  # noqa: E402

OUT = os.path.join(ROOT, "docs", "assets", "toolbar-settings.gif")
WIDTH = 900                 # the GIF's width (README and website show it at most this wide)
DIALOG_SCALE = 0.86
GAP = 14
HIGHLIGHT = QColor("#ef791b")


def main():
    app = QApplication([])
    from printview3d.settings import Settings
    from printview3d.ui import theme
    from printview3d.ui.main_window import MainWindow
    from printview3d.ui.settings_dialog import SettingsDialog
    from printview3d import i18n
    from PIL import Image

    theme.apply_theme(app, "ember")
    i18n.apply_language(app, "en")
    settings = Settings(os.path.join(tempfile.mkdtemp(), "settings.json"))
    w = MainWindow(settings)
    w.resize(1440, 900)
    w.move(0, 0)
    w.show()
    w.load_sync(os.path.join(ROOT, "examples", "demo_housing.3mf"))
    d = SettingsDialog(settings, w, {}, page="toolbar")
    d.show()
    d.move(300, 60)
    for box in d.findChildren(QDialogButtonBox):          # plain buttons, as on Windows and macOS
        for b in box.buttons():
            b.setIcon(QIcon_empty())

    def settle():
        for _ in range(8):
            app.processEvents()
        for b in w.toolbar.findChildren(QToolButton):
            b.setAttribute(Qt.WA_UnderMouse, False)
        app.processEvents()

    def toolbar_strip() -> QPixmap:
        """The toolbar without its empty middle (a short gap instead)."""
        pm = w.toolbar.grab()
        g = w.toolbar_spacer.geometry()
        r = pm.devicePixelRatio()
        keep = 24
        left = pm.copy(0, 0, round(g.x() * r), pm.height())
        right = pm.copy(round((g.right() + 1) * r), 0, pm.width() - round((g.right() + 1) * r), pm.height())
        out = QPixmap(left.width() + round(keep * r) + right.width(), pm.height())
        out.fill(Qt.transparent)
        p = QPainter(out)
        p.drawPixmap(0, 0, left)
        p.drawPixmap(left.width(), 0, pm.copy(round(g.x() * r), 0, round(keep * r), pm.height()))
        p.drawPixmap(left.width() + round(keep * r), 0, right)
        p.end()
        return out

    frames: list[tuple[Image.Image, int]] = []

    def frame(widget=None, ms: int = 1300):
        settle()
        d._draw_toolbar_preview()
        settle()
        strip = toolbar_strip()
        look = d.toolbar_joined_cb.parentWidget()          # the Look box: the page ends below it
        bottom = look.mapTo(d, QPoint(0, look.height())).y() + 16
        dlg = d.grab(QRect(0, 0, d.width(), bottom))
        s_scale = min(1.0, WIDTH / strip.width())
        strip = strip.scaledToWidth(round(strip.width() * s_scale), Qt.SmoothTransformation)
        dw = round(dlg.width() * DIALOG_SCALE)
        dlg_s = dlg.scaledToWidth(dw, Qt.SmoothTransformation)
        H = strip.height() + GAP + dlg_s.height()
        canvas = QPixmap(WIDTH, H)
        canvas.fill(QColor(theme.colors()["window"]))
        p = QPainter(canvas)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawPixmap((WIDTH - strip.width()) // 2, 0, strip)
        dx, dy = (WIDTH - dw) // 2, strip.height() + GAP
        p.drawPixmap(dx, dy, dlg_s)
        if widget is not None:                         # the control that just changed
            tl = widget.mapTo(d, QPoint(0, 0))
            rect = QRect(dx + round(tl.x() * DIALOG_SCALE) - 4, dy + round(tl.y() * DIALOG_SCALE) - 3,
                         round(widget.width() * DIALOG_SCALE) + 8, round(widget.height() * DIALOG_SCALE) + 6)
            p.setPen(QPen(HIGHLIGHT, 3))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect, 6, 6)
        p.end()
        tmp = os.path.join(tempfile.mkdtemp(), "f.png")
        canvas.save(tmp)
        frames.append((Image.open(tmp).convert("RGB"), ms))

    checks, combo, joined = d.toolbar_checks, d.toolbar_labels_combo, d.toolbar_joined_cb
    frame(ms=1800)                                                    # as it comes
    checks["check"].setChecked(False)
    frame(checks["check"])
    checks["measure"].setChecked(False)
    frame(checks["measure"])
    combo.setCurrentIndex(1)                                          # Icon and name
    frame(combo, 1500)
    combo.setCurrentIndex(3)                                          # Icon only
    frame(combo, 1500)
    joined.setChecked(True)
    frame(joined, 1800)
    combo.setCurrentIndex(1)                                          # joined, with names
    frame(combo, 1800)
    reset = next(b for b in d.findChildren(type(d.apply_btn)) if b.text() == "Reset to defaults")
    reset.click()
    frame(reset, 2200)
    d.reject()

    # Every frame as tall as the tallest (the toolbar's height changes a little with its look).
    bg = theme.colors()["window"]
    tallest = max(f.height for f, _ in frames)
    frames = [(_pad(f, tallest, bg), ms) for f, ms in frames]
    # One shared palette for every frame (no flicker between frames), 96 colours.
    sheet = Image.new("RGB", (WIDTH, sum(f.height for f, _ in frames)))
    y = 0
    for f, _ in frames:
        sheet.paste(f, (0, y))
        y += f.height
    pal = sheet.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    imgs = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f, _ in frames]
    imgs[0].save(OUT, save_all=True, append_images=imgs[1:], duration=[ms for _, ms in frames],
                 loop=0, optimize=True, disposal=1)
    print("saved", os.path.relpath(OUT, ROOT), f"{os.path.getsize(OUT) // 1024} KB,",
          f"{imgs[0].width} x {imgs[0].height}, {len(imgs)} frames")
    w.close()


def _pad(img, height: int, color: str):
    from PIL import Image
    if img.height == height:
        return img
    out = Image.new("RGB", (img.width, height), color)
    out.paste(img, (0, 0))
    return out


def QIcon_empty():
    from PySide6.QtGui import QIcon
    return QIcon()


if __name__ == "__main__":
    main()

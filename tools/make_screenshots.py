"""Regenerate the README screenshots in docs/ from the demo files.

Run (needs a display; on Linux CI use xvfb-run):
    python tools/make_demo.py
    python tools/make_screenshots.py                    # Dark: docs/screenshot-*.png (README, website)
    python tools/make_screenshots.py --theme light      # the website's Light and Ember versions:
    python tools/make_screenshots.py --theme ember      #   docs/screenshot-*--light.webp, --ember.webp

The website shows the version matching its theme (tools/mkdocs_theme_images.py); the README on
GitHub shows the Dark pictures. --no-demo leaves the example files' thumbnails alone.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

DOCS = os.path.join(ROOT, "docs")
EX = os.path.join(ROOT, "examples")


def themed_name(name: str, theme_name: str) -> str:
    """screenshot-model.png -> screenshot-model--light.webp (Dark keeps the plain name). The dots of
    the name become dashes, so the website's language plugin never reads ".ar." as a language."""
    if theme_name == "dark":
        return name
    stem, _ = os.path.splitext(name)
    return f"{stem.replace('.', '-')}--{theme_name}.webp"


def save_image(img, path: str):
    """Save a QImage/QPixmap; .webp through Pillow (smaller than PNG, sharp enough for screenshots)."""
    if not path.endswith(".webp"):
        img.save(path)
        return
    tmp = path[:-5] + ".tmp.png"
    img.save(tmp)
    from PIL import Image
    Image.open(tmp).save(path, "WEBP", quality=88, method=6)
    os.remove(tmp)


def plain_buttons(dialog):
    """Linux's desktop theme puts icons on OK / Cancel / Apply; Windows and macOS show plain
    buttons, so the screenshots do too."""
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QDialogButtonBox
    for box in dialog.findChildren(QDialogButtonBox):
        for b in box.buttons():
            b.setIcon(QIcon())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="dark", choices=["dark", "light", "ember"])
    ap.add_argument("--no-demo", action="store_true", help="don't rewrite the examples' thumbnails")
    args = ap.parse_args()
    dark = args.theme == "dark"
    app = QApplication([])
    from printview3d.settings import Settings
    from printview3d.ui.main_window import MainWindow
    from printview3d.ui.settings_dialog import SettingsDialog
    from printview3d.ui import theme
    import make_demo

    theme.apply_theme(app, args.theme)
    from printview3d import i18n as _i18n
    _i18n.apply_language(app, "en")          # number format as the real program has it (17,751.69)
    import subprocess
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "i18n.py"), "compile"], check=True)
    tmp = tempfile.mkdtemp()
    # Stand-in slicer programs so the slicer menu has something to show.
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir)
    for exe in ("CrealityPrint", "orca-slicer", "bambu-studio"):
        p = os.path.join(bindir, exe + (".exe" if sys.platform == "win32" else ""))
        with open(p, "w") as f:
            f.write("")
        os.chmod(p, 0o755)
    os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")
    settings = Settings(os.path.join(tmp, "settings.json"))
    settings.set("slicer_id", "creality_print")
    w = MainWindow(settings)
    w.resize(1440, 900)
    w.move(0, 0)
    w.show()
    app.processEvents()

    def shot(name, widget=None):
        w.statusBar().clearMessage()
        app.processEvents()
        w.plotter.render()
        app.processEvents()
        name = themed_name(name, args.theme)
        save_image((widget or w).grab(), os.path.join(DOCS, name))
        print("saved", name)

    def camera(azim, elev, zoom=1.0):
        w.scene.set_view("iso")
        cam = w.plotter.camera
        cam.Azimuth(azim)
        cam.Elevation(elev)
        cam.OrthogonalizeViewUp()
        w.plotter.reset_camera(bounds=w.scene.focus_bounds)
        cam.Zoom(zoom)
        w.plotter.reset_camera_clipping_range()

    os.makedirs(DOCS, exist_ok=True)

    # 1) STL model view + a thumbnail for the demo G-code / 3MF
    w.load_sync(os.path.join(EX, "demo_vase.stl"))
    camera(-25, -5, 1.15)
    shot("screenshot-model.png")
    if dark and not args.no_demo:          # a thumbnail for the demo G-code / 3MF
        img = w.plotter.screenshot(None, return_img=True)
        from PIL import Image
        im = Image.fromarray(img)
        h = im.height
        cx = im.width // 2
        im = im.crop((cx - h // 2, 0, cx + h // 2, h)).resize((300, 300))
        import io
        bio = io.BytesIO()
        im.save(bio, "PNG")
        make_demo.main(bio.getvalue())

    # 2) G-code, cut at 60 % height
    w.load_sync(os.path.join(EX, "demo_vase.gcode"))
    w.set_layer(int(w.gcode.n_layers * 0.6))
    w._redraw_gcode()
    camera(-20, -8, 1.25)
    shot("screenshot-gcode.png")

    # 3) Single layer from the top
    w.set_layer(int(w.gcode.n_layers * 0.35))
    w.only_layer_cb.setChecked(True)
    w._redraw_gcode()
    w.scene.set_view("top")
    w.plotter.camera.Zoom(1.6)
    shot("screenshot-layer.png")
    w.only_layer_cb.setChecked(False)

    # 4) 3MF plate with several objects
    w.load_sync(os.path.join(EX, "demo_plate.3mf"))
    camera(-15, -10, 1.1)
    shot("screenshot-3mf.png")

    # 5) Slicer menu (the arrow on the button)
    w._fill_slicer_menu()
    pos = w.slicer_btn.mapToGlobal(QPoint(0, w.slicer_btn.height()))
    w.slicer_menu.popup(pos)
    for _ in range(5):
        app.processEvents()
    screen = app.primaryScreen().grabWindow(0)
    r = w.slicer_menu.geometry()
    b = w.slicer_btn.mapToGlobal(QPoint(0, 0))
    left, top = max(0, b.x() - 160), max(0, b.y() - 8)
    save_image(screen.copy(left, top, max(r.right(), b.x() + w.slicer_btn.width()) - left + 180,
                           r.bottom() - top + 16),
               os.path.join(DOCS, themed_name("screenshot-slicer-menu.png", args.theme)))
    print("saved slicer menu")
    w.slicer_menu.close()

    # 6) Settings
    d = SettingsDialog(settings, w, {"GPU": "(your graphics card)"}, page="slicer")
    d.show()
    for _ in range(5):
        app.processEvents()
    plain_buttons(d)
    app.processEvents()
    save_image(d.grab(), os.path.join(DOCS, themed_name("screenshot-settings.png", args.theme)))
    print("saved settings")
    d.close()

    # 6b) Settings -> Updates with a (pretend) newer version on GitHub
    from printview3d import __version__
    from printview3d import updates as up
    nums = [int(x) for x in __version__.split(".")]
    nums[1] += 1
    settings.set("update_check", True)
    settings.set("update_last_check", __import__("time").time())
    settings.set("update_latest", {"version": f"{nums[0]}.{nums[1]}.0", "notes": "", "page_url": up.RELEASES_PAGE})
    d = SettingsDialog(settings, w, {}, page="updates")
    d.show()
    for _ in range(5):
        app.processEvents()
    plain_buttons(d)
    app.processEvents()
    save_image(d.grab(), os.path.join(DOCS, themed_name("screenshot-updates.png", args.theme)))
    print("saved updates")
    d.close()
    w.refresh_update_badge()
    settings.set("update_latest", {})
    w.refresh_update_badge()

    # 7) Arabic (right-to-left) for the Translations section
    from printview3d import i18n
    i18n.apply_language(app, "ar")
    for _ in range(5):
        app.processEvents()
    w.load_sync(os.path.join(EX, "demo_vase.gcode"))
    w.set_layer(int(w.gcode.n_layers * 0.6))
    w._redraw_gcode()
    camera(-20, -8, 1.25)
    shot("screenshot-arabic.png")
    i18n.apply_language(app, "en")
    for _ in range(5):
        app.processEvents()

    if not dark:                     # the theme pictures and FreeCAD: Dark only
        w.close()
        return

    # 8) The same G-code in the Gray, Graphite and Light themes, plus a 2 x 2 overview
    w.load_sync(os.path.join(EX, "demo_vase.gcode"))
    w.set_layer(int(w.gcode.n_layers * 0.6))
    w._redraw_gcode()
    camera(-20, -8, 1.25)
    for name in ("gray", "graphite", "light"):
        w.apply_theme(name)
        for _ in range(5):
            app.processEvents()
        shot(f"screenshot-theme-{name}.png")
    w.apply_theme("dark")
    from PIL import Image
    tiles = [Image.open(os.path.join(DOCS, f)) for f in
             ("screenshot-gcode.png", "screenshot-theme-gray.png",
              "screenshot-theme-graphite.png", "screenshot-theme-light.png")]
    tw = 720
    tiles = [t.resize((tw, int(t.height * tw / t.width))) for t in tiles]
    th = tiles[0].height
    grid = Image.new("RGB", (tw * 2 + 10, th * 2 + 10), "#888888")
    for i, t in enumerate(tiles):
        grid.paste(t, ((i % 2) * (tw + 10), (i // 2) * (th + 10)))
    grid.save(os.path.join(DOCS, "screenshot-themes.png"))

    # 9) The theme menu (toolbar icon)
    w.theme_menu.popup(w.theme_btn.mapToGlobal(QPoint(0, w.theme_btn.height())))
    for _ in range(5):
        app.processEvents()
    r = w.theme_menu.geometry()
    b = w.theme_btn.mapToGlobal(QPoint(0, 0))
    screen = app.primaryScreen().grabWindow(0)
    left = max(0, r.left() - 420)
    right = max(r.right(), b.x() + w.theme_btn.width()) + 10
    screen.copy(left, max(0, b.y() - 8), right - left,
                r.bottom() - b.y() + 20).save(os.path.join(DOCS, "screenshot-theme-menu.png"))
    print("saved screenshot-theme-menu.png")
    w.theme_menu.close()

    # 10) FreeCAD document: in 3D (needs FreeCAD; PRINTVIEW3D_FREECAD=path/to/freecadcmd
    #     to choose one) and the preview page shown without FreeCAD
    from printview3d import freecad as fc
    settings.set("freecad_path", os.environ.get("PRINTVIEW3D_FREECAD", ""))
    demo_fc = os.path.join(EX, "demo_bracket.FCStd")
    if fc.find_freecad(settings.get("freecad_path")):
        w.load_sync(demo_fc)
        camera(20, 0, 1.0)
        shot("screenshot-freecad.png")
    else:
        print("FreeCAD not found: screenshot-freecad.png not updated")
    real_find = fc.find_freecad
    fc.find_freecad = lambda *_a: None
    w.load_sync(demo_fc)
    shot("screenshot-freecad-preview.png")
    fc.find_freecad = real_find
    settings.set("freecad_path", "")
    print("saved screenshot-themes.png")
    w.close()


if __name__ == "__main__":
    main()

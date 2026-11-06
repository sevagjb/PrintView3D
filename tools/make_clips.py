"""Make the pictures and short videos of the website's "Look inside your models" page from the
real program, with examples/demo_housing.3mf (python tools/make_inside_demo.py).

Videos show only the 3D view, so one set serves every language; the still pictures show the
whole window and are made per language, so the Arabic page shows the Arabic program.

Needs a display (on Linux: xvfb-run) and ffmpeg:
    xvfb-run -a -s "-screen 0 1600x1000x24" python tools/make_clips.py
    python tools/make_clips.py --lang en ar --out docs/assets/inside
Result: docs/assets/inside/*.mp4 (with a .jpg poster each) and *.png.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtCore import QPoint  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

DEMO = os.path.join(ROOT, "examples", "demo_housing.3mf")
FPS = 30
WIDTH = 960                      # video width in pixels (the page shows it at most this wide)


class Capture:
    def __init__(self, app, out: str):
        self.app = app
        self.out = out
        self.w = None

    # ---------------------------------------------------------------- window
    def open(self, lang: str):
        from printview3d import i18n
        from printview3d.settings import Settings
        from printview3d.ui import theme
        from printview3d.ui.main_window import MainWindow
        if self.w is not None:
            self.w.close()
            self.w.deleteLater()
            self.settle()
        theme.apply_theme(self.app, "dark")
        i18n.apply_language(self.app, lang)
        settings = Settings(os.path.join(tempfile.mkdtemp(), "settings.json"))
        settings.set("language", lang)
        settings.set("thumbnail_open", False)      # more room for the panel boxes
        self.w = MainWindow(settings)
        self.w.resize(1440, 900)
        self.w.show()
        self.w.load_sync(DEMO)
        self.settle()

    def settle(self, n: int = 12):
        for _ in range(n):
            self.app.processEvents()

    def render(self):
        self.w.plotter.render()
        self.settle(3)

    def iso(self):
        self.w.scene.set_view("iso", render=False)
        cam = self.w.plotter.camera
        cam.Azimuth(-20)
        cam.Elevation(-4)
        cam.Zoom(1.15)
        self.render()

    def view_rect(self):
        """The 3D view's place in the window (for cropping the videos)."""
        p = self.w.plotter
        tl = p.mapTo(self.w, QPoint(0, 0))
        return tl.x(), tl.y(), p.width(), p.height()

    def frame(self):
        from PIL import Image
        img = self.w.grab().toImage()
        x, y, wd, ht = self.view_rect()
        img = img.copy(x, y, wd, ht).convertToFormat(img.Format.Format_RGB888)
        ptr = img.constBits()
        im = Image.frombuffer("RGB", (img.width(), img.height()), bytes(ptr), "raw", "RGB",
                              img.bytesPerLine(), 1)
        h = round(im.height * WIDTH / im.width / 2) * 2
        return im.resize((WIDTH, h), Image.LANCZOS)

    def still(self, name: str):
        self.w.statusBar().clearMessage()        # "Opened /path/on/this/computer/..."
        self.render()
        self.w.grab().save(os.path.join(self.out, name))
        print("  ", name)

    # ---------------------------------------------------------------- video
    def video(self, name: str, steps, poster_at: float = 0.0):
        """steps: a list of callables, one per frame; each changes the view a little. The poster
        (shown before the video plays) is the frame at poster_at (0 = first, 0.5 = halfway)."""
        tmp = tempfile.mkdtemp()
        for i, step in enumerate(steps):
            step()
            self.render()
            self.frame().save(os.path.join(tmp, f"f{i:04d}.png"))
        mp4 = os.path.join(self.out, name + ".mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(tmp, "f%04d.png"), "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "27", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", mp4], check=True)
        k = min(int(poster_at * len(steps)), len(steps) - 1)
        shutil.copy(os.path.join(tmp, f"f{k:04d}.png"), os.path.join(tmp, "poster.png"))
        from PIL import Image
        Image.open(os.path.join(tmp, "poster.png")).convert("RGB").save(
            os.path.join(self.out, name + ".jpg"), quality=82, optimize=True)
        shutil.rmtree(tmp, ignore_errors=True)
        print("  ", name + ".mp4", f"{os.path.getsize(mp4) // 1024} KB")

    def turn(self, seconds: float, degrees: float = 360.0):
        n = int(seconds * FPS)
        cam = self.w.plotter.camera
        return [lambda: cam.Azimuth(degrees / n) for _ in range(n)]

    def off(self):
        w = self.w
        for a in (w.act_wireframe, w.act_xray, w.act_clip, w.act_clip_face, w.act_measure):
            if a.isChecked():
                a.setChecked(False)
        for i in range(len(w.scene.model_actors)):           # the file's own colours again
            w.scene.set_part_color(i, None)
        self.show_colors()
        w.grid_labels.set_enabled(False)
        w.act_view.setChecked(False)                      # the View section closed
        self.settle()

    def show_colors(self):
        """The colour boxes in the Objects list follow the colours the parts are drawn in."""
        from printview3d.ui.main_window import _ColorButton
        w = self.w
        n = len(w.model.parts)
        for i, box in enumerate(w.findChildren(_ColorButton)):
            if i < n:
                box.set_color(w._object_color(i, w.model.parts[i], n))

    def measurements(self):
        """Measure on, with one of each kind on the housing (world coordinates, mm): the height
        of the front wall with its ΔX ΔY ΔZ, the right angle of the top front edge, and the
        14 mm inlet on top (Ø 14, R 7)."""
        import math
        import numpy as np
        from printview3d.ui.measure import Item
        w = self.w
        w.measure_deltas_cb.setChecked(True)
        w.choose_measure_mode("distance")           # turns Measure on, the section opens
        self.settle()
        m = w.measure
        cx, cy, top = 175.0, 175.0, 46.0           # see tools/make_inside_demo.py
        front = cy - 32.0
        dist = Item("distance")
        dist.points = [np.array(p) for p in ((205.0, front, top), (205.0, front, 0.0))]
        ang = Item("angle")
        ang.points = [np.array(p) for p in ((150.0, front + 16.0, top), (150.0, front, top), (150.0, front, top - 20.0))]
        circ = Item("circle")
        circ.points = [np.array((cx - 14.0 + 7.0 * math.cos(t), cy + 7.0 * math.sin(t), top))
                       for t in (math.radians(200), math.radians(300), math.radians(60))]
        m.items = [dist, ang, circ]
        m.current = dist
        m.hover_point = None
        m._update()
        self.settle()


def make_videos(c: Capture):
    w = c.w
    print("videos")
    # Clip facing you: the model turns through the cut, once round.
    c.off()
    c.iso()
    w.act_clip_face.setChecked(True)
    w.face_slider.setValue(int(w.CLIP_STEPS * 0.52))
    c.video("clip-facing", c.turn(8.0))

    # Clip from the top: the cut moves down through the model and back up, turning slowly.
    c.off()
    c.iso()
    w.act_clip.setChecked(True)
    cam = w.plotter.camera
    n = int(3.0 * FPS)
    top, low = w.CLIP_STEPS, int(w.CLIP_STEPS * 0.12)
    values = [round(top + (low - top) * i / (n - 1)) for i in range(n)]
    values += values[::-1]

    def step(v):
        return lambda: (w.face_slider.setValue(v), cam.Azimuth(40.0 / len(values)))
    c.video("clip-top", [step(v) for v in values], poster_at=0.4)   # poster: cut part-way down

    # X-ray: see-through, once round.
    c.off()
    c.iso()
    w.act_xray.setChecked(True)
    c.video("xray", c.turn(8.0))

    # Wireframe: a picture is enough (thin lines make a video large and blurry).
    c.off()
    c.iso()
    w.act_wireframe.setChecked(True)
    c.render()
    c.frame().save(os.path.join(c.out, "wireframe.png"), optimize=True)
    print("   wireframe.png")
    c.off()


def make_stills(c: Capture, lang: str):
    w = c.w
    sfx = "" if lang == "en" else "." + lang
    print("stills", lang)
    c.off()
    c.iso()
    c.still(f"objects{sfx}.png")                    # Objects list with each object's size
    w.act_clip_face.setChecked(True)
    w.face_slider.setValue(int(w.CLIP_STEPS * 0.52))
    c.still(f"clip-facing{sfx}.png")                # the cut and its box in the side panel
    c.off()
    w.act_clip.setChecked(True)
    w.face_slider.setValue(int(w.CLIP_STEPS * 0.45))
    w.act_xray.setChecked(True)
    c.still(f"xray-clip{sfx}.png")                  # options work together
    c.off()
    # 0.28: Measure, the object colours.
    c.iso()
    c.measurements()
    c.still(f"measure{sfx}.png")                    # distance with ΔX ΔY ΔZ, angle, circle
    c.off()
    c.iso()
    w.act_xray.setChecked(True)                     # see-through, so the impeller shows too
    w.act_view.setChecked(False)
    w.scene.set_part_color(0, "#ef791b")            # Ember orange and teal
    w.scene.set_part_color(1, "#2cc1b2")
    c.show_colors()
    c.still(f"colors{sfx}.png")
    c.off()


def make_grid(c: Capture):
    """The numbers along the plate (3D view only, the same in every language)."""
    w = c.w
    c.off()
    w.grid_labels.set_step(0)
    w.grid_labels.set_enabled(True)
    w.scene.set_view("iso", render=False)
    cam = w.plotter.camera
    cam.Azimuth(-20)
    cam.Elevation(14)
    cam.Zoom(0.36)
    c.render()
    c.frame().save(os.path.join(c.out, "grid-numbers.png"), optimize=True)
    print("   grid-numbers.png")
    c.off()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", default=["en", "ar", "nl"])
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "assets", "inside"))
    ap.add_argument("--no-videos", action="store_true")
    a = ap.parse_args()
    if not os.path.isfile(DEMO):
        raise SystemExit("examples/demo_housing.3mf is missing: python tools/make_inside_demo.py")
    if shutil.which("ffmpeg") is None and not a.no_videos:
        raise SystemExit("ffmpeg is needed for the videos (or use --no-videos)")
    os.makedirs(a.out, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "i18n.py"), "compile"], check=True,
                   stdout=subprocess.DEVNULL)
    app = QApplication([])
    c = Capture(app, a.out)
    for i, lang in enumerate(a.lang):
        c.open(lang)
        if i == 0 and not a.no_videos:
            make_videos(c)
        if i == 0:
            make_grid(c)
        make_stills(c, lang)
    c.w.close()


if __name__ == "__main__":
    main()

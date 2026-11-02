"""Which part of the information panel decides its width? (Diagnostics for the panel tests.)

Run from the PrintView3D folder, after build_windows.bat / build_linux.sh made .venv:

    .venv\\Scripts\\python tools\\panel_width_probe.py          (Windows)
    .venv/bin/python tools/panel_width_probe.py                (Linux, macOS)

Optional: a language code and a font size in pixels, e.g. `... panel_width_probe.py nl 21`.
It opens tests/data/busy_project.3mf off screen, like the tests do, and follows the widest
part from the panel down to the single widget that can't get narrower.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontMetrics  # noqa: E402
from PySide6.QtWidgets import QApplication, QLayout, QWidget  # noqa: E402


def describe(w: QWidget) -> str:
    text = ""
    for attr in ("text", "title"):
        f = getattr(w, attr, None)
        if callable(f):
            try:
                text = f() or ""
            except TypeError:
                text = ""
            if text:
                break
    text = text.replace("\n", " ").replace("​", "")[:45]
    return f"{type(w).__name__}#{w.objectName() or '-'} {text!r}"


def widest_items(layout: QLayout):
    """The layout's items with their minimum widths, widest first."""
    out = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is None or item.isEmpty():
            continue
        out.append((item.minimumSize().width(), item))
    return sorted(out, key=lambda t: -t[0])


def follow(widget: QWidget, depth: int = 0):
    pad = "  " * depth
    lay = widget.layout()
    print(f"{pad}{widget.minimumSizeHint().width():4d}  {describe(widget)}"
          + (f"   [layout margins {lay.contentsMargins().left()}+{lay.contentsMargins().right()}]" if lay else ""))
    if lay is None:
        return
    items = widest_items(lay)
    for w_min, item in items[:3]:                       # the three widest, to compare
        tag = describe(item.widget()) if item.widget() else type(item.layout() or item).__name__
        print(f"{pad}    -> {w_min:4d}  {tag}")
    if not items:
        return
    top = items[0][1]
    nxt = top.widget()
    if nxt is None and top.layout() is not None:       # a nested layout: its widest widget
        for w_min, sub in widest_items(top.layout()):
            if sub.widget() is not None:
                nxt = sub.widget()
                break
    if nxt is not None and depth < 8:
        follow(nxt, depth + 1)


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "en"
    px = int(sys.argv[2]) if len(sys.argv) > 2 else 21
    app = QApplication([])
    f = app.font()
    f.setPixelSize(px)
    app.setFont(f)
    from printview3d import i18n
    import tempfile
    sys.path.insert(0, HERE)
    import i18n as tool                                  # tools/i18n.py
    tool.cmd_compile()
    i18n.apply_language(app, code)
    from printview3d.settings import Settings
    from printview3d.ui import main_window as mw
    w = mw.MainWindow(Settings(os.path.join(tempfile.mkdtemp(), "settings.json")))
    w.resize(1280, 760)
    w.show()
    w.load_sync(os.path.join(ROOT, "tests", "data", "busy_project.3mf"))
    for _ in range(30):
        app.processEvents()
    s = app.primaryScreen()
    print(f"\nPrintView3D panel width probe: language {code}, font {px} px "
          f"({app.font().family()}, {QFontMetrics(app.font()).height()} px high), style {app.style().name()}, "
          f"{s.logicalDotsPerInch():.0f} dpi, scale {s.devicePixelRatio():g}")
    print(f"panel {w.side.width()} px, needs {w.side.minimumSizeHint().width()} px, view {w.side.parentWidget().width()} px\n")
    follow(w.side)
    print("\nAll visible widgets that need more than 200 px:")
    rows = sorted(((c.minimumSizeHint().width(), describe(c)) for c in w.side.findChildren(QWidget)
                   if c.isVisible() and c.minimumSizeHint().width() > 200), reverse=True)
    for wd, d in rows[:15]:
        print(f"  {wd:4d}  {d}")
    w.close()


if __name__ == "__main__":
    main()

"""Tooltips that stay inside the window.

Qt keeps a tooltip on the screen, not in the window, and a plain-text tooltip is one long line:
a long one (e.g. Snap to corners and edges, at the right edge of the side panel) ran past the
window. Every tooltip shown is now wrapped to at most MAX_CHARS characters (or the window's
width, if that is less) and moved so it lies within the window under the mouse.

Done on Qt's own tooltip label (class QTipLabel) when it shows or changes size, so it covers
every tooltip: widgets, actions, list items and the ones the 3D view shows itself.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QLabel, QWidget

MAX_CHARS = 60                # a tooltip is at most about this many characters wide
MARGIN = 6                    # px kept free between a tooltip and the window's edge


def _window_rect(label: QWidget) -> QRect | None:
    """The window under the mouse (where the tooltip belongs), in screen coordinates."""
    under = QApplication.widgetAt(QCursor.pos())
    win = under.window() if under is not None and under is not label else QApplication.activeWindow()
    if win is None or win is label or not win.isVisible():
        return None
    return win.frameGeometry()


def fit(label: QLabel, area: QRect | None = None):
    """Wrap the tooltip to fit, and move it into the window (or the given area)."""
    area = area or _window_rect(label)
    if area is None:
        return
    fm = label.fontMetrics()
    most = min(fm.averageCharWidth() * MAX_CHARS, area.width() - 2 * MARGIN)
    if most <= 40:
        return
    w, h = label.width(), label.height()
    if label.sizeHint().width() > most or w > most:
        label.setWordWrap(True)
        w = most
        h = label.heightForWidth(w)
        if h <= 0:
            h = label.sizeHint().height()
        label.resize(w, h)
    x, y = label.x(), label.y()
    cursor = QCursor.pos()
    x = max(area.left() + MARGIN, min(x, area.right() - MARGIN - w))
    if y + h > area.bottom() - MARGIN:                 # no room below the mouse: above it
        y = cursor.y() - h - 4
    y = max(area.top() + MARGIN, y)
    if (x, y) != (label.x(), label.y()):
        label.move(x, y)


class _TipFitter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._busy = False

    def eventFilter(self, obj, ev):
        t = ev.type()
        if (t == QEvent.Show or t == QEvent.Resize) and not self._busy and isinstance(obj, QLabel) \
                and obj.metaObject().className() == "QTipLabel":
            self._busy = True
            try:
                fit(obj)
            finally:
                self._busy = False
        return False


_fitter: _TipFitter | None = None


def install(app: QApplication):
    """Once per application (calling it again does nothing)."""
    global _fitter
    if _fitter is None:
        _fitter = _TipFitter(app)
        app.installEventFilter(_fitter)

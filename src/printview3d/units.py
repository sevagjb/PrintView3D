"""Millimetres or inches (Settings -> Language and units).

Everything inside PrintView3D stays in millimetres: the files, the 3D view, the settings that
store lengths. Only what is shown changes: the numbers are converted on the way out and the
lengths typed into a field on the way in. Every place that shows a length goes through here.
"""

from __future__ import annotations

from .i18n import num, tr, tr_noop

MM_PER_IN = 25.4
UNITS = ("mm", "in")
UNIT_NAMES = {"mm": tr_noop("Millimetres (mm)"), "in": tr_noop("Inches (in)")}

_current = "mm"


def set_unit(unit: str) -> str:
    """Choose mm or in (anything else is mm). Returns the unit in use."""
    global _current
    _current = unit if unit in UNITS else "mm"
    return _current


def current() -> str:
    return _current


def imperial() -> bool:
    return _current == "in"


def name() -> str:
    """The unit as written after a number: "mm" or "in" (translated)."""
    return tr("in") if imperial() else tr("mm")


def to_display(mm: float) -> float:
    return mm / MM_PER_IN if imperial() else mm


def decimals(mm_decimals: int) -> int:
    """Decimals for a length shown with `mm_decimals` in millimetres: an inch is 25.4 mm, so
    inches need two more (at most three) to say as much: 0.1 mm ~ 0.004 in."""
    return min(3, mm_decimals + 2) if imperial() else mm_decimals


def number(mm: float, mm_decimals: int = 2) -> str:
    """A length as a number in the unit in use, in the user's number format (no unit)."""
    return num(to_display(mm), decimals(mm_decimals))


def length(mm: float, mm_decimals: int = 2) -> str:
    """A length with its unit: '12.50 mm' or '0.492 in'."""
    return f"{number(mm, mm_decimals)} {name()}"


def short(value: float) -> str:
    """A value in the unit in use without needless zeros: 50, 2.5, 0.125."""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return num(float(text), len(text.split(".")[1]) if "." in text else 0)


def volume(mm3: float) -> str:
    """A volume: cm³, or in³ in inches."""
    if imperial():
        return tr("{v} in³").format(v=num(mm3 / MM_PER_IN ** 3, 2))
    return tr("{v} cm³").format(v=num(mm3 / 1000))

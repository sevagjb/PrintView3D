"""A field for a length in mm or inches, always read and set in millimetres."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDoubleSpinBox

from .. import units
from ..i18n import tr


class LengthSpin(QDoubleSpinBox):
    """In millimetres: whole numbers in steps of `step_mm`. In inches: two decimals in steps of
    half an inch. mm() / set_mm() always speak millimetres, whatever is shown. The unit is the
    one in use, or the one given (Settings shows the unit chosen there before it is saved).

    The length set is kept exactly while the field shows it: switching to inches and back (or
    another language) does not round 0.4 mm to 0.41 mm."""

    def __init__(self, lo_mm: float, hi_mm: float, step_mm: float = 10, unit: str = "", parent=None,
                 mm_decimals: int = 0, in_step: float = 0.5, in_decimals: int = 2):
        super().__init__(parent)
        self._lo, self._hi, self._step = lo_mm, hi_mm, step_mm
        self._dec = (mm_decimals, in_step, in_decimals)
        self._mm: Optional[float] = None
        self.unit = ""
        self.set_unit(unit or units.current())

    def _factor(self) -> float:
        return units.MM_PER_IN if self.unit == "in" else 1.0

    def set_unit(self, unit: str):
        """Show the same length in another unit (or the same one again, with the unit's name in
        the language now in use)."""
        mm = self.mm() if self.unit else None
        self.unit = unit if unit in units.UNITS else "mm"
        f = self._factor()
        if self.unit == "in":
            self.setDecimals(self._dec[2])
            self.setSingleStep(self._dec[1])
        else:
            self.setDecimals(self._dec[0])
            self.setSingleStep(self._step)
        self.setRange(self._lo / f, self._hi / f)
        self.setSuffix(" " + (tr("in") if self.unit == "in" else tr("mm")))
        if mm is not None:
            self.set_mm(mm)

    def shows(self, mm: float) -> bool:
        """Whether the field shows this length (as rounded to its decimals)."""
        return abs(float(mm) / self._factor() - self.value()) <= 0.5 * 10 ** -self.decimals() + 1e-9

    def set_mm(self, mm: float):
        self._mm = float(mm)
        self.setValue(self._mm / self._factor())

    def mm(self) -> float:
        if self._mm is not None and self.shows(self._mm):
            return self._mm
        return self.value() * self._factor()

"""A field for a length in mm or inches, always read and set in millimetres."""

from __future__ import annotations

from PySide6.QtWidgets import QDoubleSpinBox

from .. import units
from ..i18n import tr


class LengthSpin(QDoubleSpinBox):
    """In millimetres: whole numbers in steps of `step_mm`. In inches: two decimals in steps of
    half an inch. mm() / set_mm() always speak millimetres, whatever is shown. The unit is the
    one in use, or the one given (Settings shows the unit chosen there before it is saved)."""

    def __init__(self, lo_mm: float, hi_mm: float, step_mm: float = 10, unit: str = "", parent=None,
                 mm_decimals: int = 0, in_step: float = 0.5, in_decimals: int = 2):
        super().__init__(parent)
        self._lo, self._hi, self._step = lo_mm, hi_mm, step_mm
        self._dec = (mm_decimals, in_step, in_decimals)
        self.unit = ""
        self.set_unit(unit or units.current())

    def _factor(self) -> float:
        return units.MM_PER_IN if self.unit == "in" else 1.0

    def set_unit(self, unit: str):
        """Show the same length in another unit."""
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

    def set_mm(self, mm: float):
        self.setValue(float(mm) / self._factor())

    def mm(self) -> float:
        return self.value() * self._factor()

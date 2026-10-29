"""Translations (languages of the user interface).

How it works
------------
* Every text shown to the user is written in English and wrapped in tr():
      label.setText(tr("Show only this layer"))
      tr("Layer {n} of {total}").format(n=5, total=120)
  Texts that are defined before the app runs (tables, constants) are marked
  with tr_noop() and passed through tr() when they are displayed.
* tools/i18n.py collects all of them into translations/printview3d_<lang>.ts
  (Qt's standard format, editable with Qt Linguist or any text editor) and compiles
  them to resources/translations/*.qm, which the app loads at runtime.
* Qt's own texts (OK / Cancel buttons, file dialogs) come from the
  qtbase_<lang>.qm files that ship with Qt.
* Arabic switches the whole layout to right-to-left automatically.

Changing the language takes effect immediately: Qt sends a LanguageChange
event to every window, and the windows re-set their texts.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, Qt, QTranslator

CONTEXT = "PrintView3D"

# Language code -> its own name (shown in Settings in that language).
LANGUAGES: dict[str, str] = {
    "en": "English",
    "ar": "العربية",
    "nl": "Nederlands",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "ro": "Română",
}
RIGHT_TO_LEFT = {"ar", "he", "fa", "ur"}
# Measurements are shown with Western digits in these languages (as slicers do).
WESTERN_DIGITS = {"ar", "fa", "ur"}

_TRANSLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "translations")
_installed: list[QTranslator] = []
_current = "en"


def tr(text: str) -> str:
    """Translate a user-visible text (English source text)."""
    return QCoreApplication.translate(CONTEXT, text)


def tr_noop(text: str) -> str:
    """Mark a text for translation without translating it yet (for tables/constants)."""
    return text


def current_language() -> str:
    return _current


def system_language() -> str:
    """The user's system language if we have it, else English."""
    for name in QLocale.system().uiLanguages():
        code = name.replace("_", "-").split("-")[0].lower()
        if code in LANGUAGES:
            return code
    return "en"


def resolve(setting: str) -> str:
    """'auto' / '' -> system language; unknown codes -> English."""
    if not setting or setting == "auto":
        return system_language()
    return setting if setting in LANGUAGES else "en"


def completion() -> dict[str, int]:
    """Percentage translated per language (written by tools/i18n.py compile)."""
    import json
    try:
        with open(os.path.join(_TRANSLATIONS_DIR, "status.json"), encoding="utf-8") as f:
            return {k: int(v) for k, v in json.load(f).items()}
    except (OSError, ValueError):
        return {}


def available_qm(code: str) -> Optional[str]:
    path = os.path.join(_TRANSLATIONS_DIR, f"printview3d_{code}.qm")
    return path if os.path.isfile(path) else None


def apply_language(app, setting: str = "auto") -> str:
    """Install translators for the chosen language. Returns the language code used."""
    global _current
    code = resolve(setting)

    for t in _installed:
        app.removeTranslator(t)
    _installed.clear()

    if code != "en":
        ours = QTranslator(app)
        qm = available_qm(code)
        if qm and ours.load(qm):
            app.installTranslator(ours)
            _installed.append(ours)
        # Qt's own texts: buttons, file dialogs, context menus
        qt_dir = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
        qt_tr = QTranslator(app)
        if qt_tr.load(f"qtbase_{code}", qt_dir):
            app.installTranslator(qt_tr)
            _installed.append(qt_tr)

    # Number format for all widgets (spin boxes too). Arabic keeps Western digits.
    if code in WESTERN_DIGITS:
        QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedStates))
    else:
        QLocale.setDefault(QLocale(code))
    if hasattr(app, "setLayoutDirection"):          # GUI apps only
        app.setLayoutDirection(Qt.RightToLeft if code in RIGHT_TO_LEFT else Qt.LeftToRight)
    _current = code
    return code


# --------------------------------------------------------------- numbers
def num(value: float, decimals: int = 2) -> str:
    """A decimal number in the user's format (e.g. 0,20 in Dutch)."""
    return QLocale().toString(float(value), "f", decimals)


def count(value: int) -> str:
    """A whole number with thousands separators (e.g. 12.345 in German)."""
    return QLocale().toString(int(value))


def localize_number_text(text: str) -> str:
    """'0.2' or '52.95' read from a file -> '0,2' / '52,95' where that is the custom."""
    t = text.strip()
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        decimals = len(t.split(".")[1]) if "." in t else 0
        return num(float(t), decimals) if decimals else count(int(t))
    return text


def ltr(text: str) -> str:
    """Keep a measurement like '69.3 × 69.5 × 70.00 mm' in reading order inside
    right-to-left text (Unicode left-to-right isolate)."""
    return "\u2066" + text + "\u2069" if _current in RIGHT_TO_LEFT else text

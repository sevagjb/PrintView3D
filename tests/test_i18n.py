"""Translation tests: files up to date, placeholders intact, every language loads."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import i18n as tool  # noqa: E402  (tools/i18n.py)


def test_translation_files_are_up_to_date_and_valid():
    """Fails when a new tr() text was added without running: python tools/i18n.py update."""
    assert tool.problems() == []


def test_every_language_has_a_file_and_is_listed():
    from printview3d.i18n import LANGUAGES
    files = set(tool.language_files())
    assert files == set(LANGUAGES) - {"en"}


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    tool.cmd_compile()
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("code,word", [("ar", "الإعدادات"), ("nl", "Instellingen"), ("de", "Einstellungen"),
                                       ("fr", "Paramètres"), ("es", "Ajustes"), ("ro", "Setări")])
def test_language_loads(app, code, word):
    from printview3d import i18n
    assert i18n.apply_language(app, code) == code
    assert i18n.tr("Settings") == word
    i18n.apply_language(app, "en")
    assert i18n.tr("Settings") == "Settings"


def test_numbers_and_direction(app):
    from PySide6.QtCore import Qt
    from printview3d import i18n
    i18n.apply_language(app, "de")
    assert i18n.num(0.2, 2) == "0,20" and i18n.localize_number_text("52.95") == "52,95"
    i18n.apply_language(app, "ar")
    assert i18n.num(0.2, 2) == "0.20"                    # Western digits in Arabic
    assert app.layoutDirection() == Qt.RightToLeft
    assert i18n.ltr("1 × 2 mm").startswith("⁦")
    i18n.apply_language(app, "en")
    assert app.layoutDirection() == Qt.LeftToRight
    assert i18n.ltr("1 mm") == "1 mm"


def test_unknown_language_falls_back_to_english(app):
    from printview3d import i18n
    assert i18n.resolve("xx") == "en"
    assert i18n.resolve("auto") in i18n.LANGUAGES

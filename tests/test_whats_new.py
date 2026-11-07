"""'What's new' once after an update: which versions, and when it is shown."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from printview3d import __version__  # noqa: E402
from printview3d import updates as up  # noqa: E402
from printview3d.settings import Settings  # noqa: E402

LOG = """# Changelog

## 0.20.0
- Twenty, see [the guide](docs/TRANSLATING.md) and [GitHub](https://github.com/x).

## 0.19.1
- Nineteen one.

## 0.19.0
- Nineteen.

## 0.18.0
- Eighteen.
"""


def test_only_versions_since_the_old_one_up_to_this_one():
    got = [n.version for n in up.whats_new("en", "0.18.0", "0.19.1", en_text=LOG)]
    assert got == ["0.19.1", "0.19.0"]


def test_repository_links_become_full_urls():
    notes, = up.whats_new("en", "0.19.1", "0.20.0", en_text=LOG)
    assert "](https://github.com/sevagjb/PrintView3D/blob/main/docs/TRANSLATING.md)" in notes.text
    assert "](https://github.com/x)" in notes.text


def test_bundled_changelog_has_this_version():
    assert __version__ in [v for v, _ in up.changelog_sections(up.changelog_text())]


def test_new_install_shows_nothing_but_records_the_version(tmp_path):
    s = Settings(str(tmp_path / "settings.json"))
    assert up.just_updated(s, "0.18.0") == ""
    assert s.get("last_run_version") == "0.18.0"


def test_update_shows_once(tmp_path):
    path = str(tmp_path / "settings.json")
    Settings(path).set("last_run_version", "0.18.0")
    s = Settings(path)
    assert up.just_updated(s, "0.19.0") == "0.18.0"
    assert up.just_updated(Settings(path), "0.19.0") == ""      # next start: nothing


def test_update_from_before_018_counts_as_017(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"language": "ar"}), encoding="utf-8")
    assert up.just_updated(Settings(str(path)), "0.18.0") == "0.17.0"


def test_going_back_to_an_older_version_shows_nothing(tmp_path):
    path = str(tmp_path / "settings.json")
    Settings(path).set("last_run_version", "0.19.0")
    assert up.just_updated(Settings(path), "0.18.0") == ""


# --- Translated changelogs (CHANGELOG.<lang>.md) and the "What's new" menu item ---------------

LOG_AR = """# سجل التغييرات

## 0.20.0
- عشرون، انظر [الدليل](docs/TRANSLATING.md).

## 0.19.0
- تسعة عشر.
"""


def test_current_version_only_in_the_users_language():
    (n,) = up.whats_new("ar", current="0.20.0", en_text=LOG, lang_text=LOG_AR)
    assert n.version == "0.20.0" and n.translated and n.text.startswith("- عشرون")
    assert "](https://github.com/sevagjb/PrintView3D/blob/main/docs/TRANSLATING.md)" in n.text


def test_untranslated_version_falls_back_to_english_per_version():
    notes = up.whats_new("ar", older="0.18.0", current="0.20.0", en_text=LOG, lang_text=LOG_AR)
    assert [(n.version, n.translated) for n in notes] == [
        ("0.20.0", True), ("0.19.1", False), ("0.19.0", True)]
    assert notes[1].text == "- Nineteen one."


def test_language_without_a_changelog_is_english():
    notes = up.whats_new("de", current="0.20.0", en_text=LOG, lang_text="")
    assert [(n.version, n.translated) for n in notes] == [("0.20.0", False)]
    assert up.whats_new("en", current="0.20.0", en_text=LOG)[0].translated   # English is the original


def test_unknown_version_gives_no_notes():
    assert up.whats_new("en", current="9.9.9", en_text=LOG) == []


def test_github_link_follows_the_language():
    assert up.changelog_url("ar").endswith("/CHANGELOG.ar.md")
    assert up.changelog_url("nl").endswith("/CHANGELOG.nl.md")
    assert up.changelog_url("de") == up.CHANGELOG_URL          # no German changelog: English
    assert up.changelog_url("en") == up.CHANGELOG_URL


def test_arabic_and_dutch_changelogs_have_this_version():
    for lang in ("ar", "nl"):
        (n,) = up.whats_new(lang)
        assert n.version == __version__ and n.translated, lang


def test_translated_changelog_headings_match_the_english_ones():
    sys.path.insert(0, os.path.join(HERE, "..", "tools"))
    import i18n as tool
    assert tool.changelog_problems() == []
    assert set(tool.changelog_files()) >= {"ar", "nl"}


def test_heading_typo_is_caught(tmp_path, monkeypatch):
    """Like "## 0.10" for 0.1.0: the program would see it as another version."""
    sys.path.insert(0, os.path.join(HERE, "..", "tools"))
    import i18n as tool
    (tmp_path / "CHANGELOG.md").write_text("## 0.2.0\n- b\n\n## 0.1.0 — first version\n- a\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.nl.md").write_text("## 0.2.0\n- b\n\n## 0.10 — eerste versie\n- a\n", encoding="utf-8")
    monkeypatch.setattr(tool, "ROOT", str(tmp_path))
    errs = tool.changelog_problems()
    assert len(errs) == 1 and "'## 0.10'" in errs[0]
    assert tool.changelog_missing() == {"nl": ["0.1.0"]}


# --- The window ------------------------------------------------------------------------------

def _qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_not_translated_note_once_when_nothing_is_translated():
    _qapp()
    from printview3d.ui.update_ui import _notes_markdown
    notes = [up.Notes("0.20.0", "- a", False), up.Notes("0.19.0", "- b", False)]
    md = _notes_markdown(notes, "de")
    assert md.count("Not translated yet") == 1 and md.index("Not translated") < md.index("## 0.20.0")


def test_not_translated_note_at_each_english_version_when_mixed():
    _qapp()
    from printview3d.ui.update_ui import _notes_markdown
    notes = [up.Notes("0.20.0", "- a", True), up.Notes("0.19.0", "- b", False)]
    md = _notes_markdown(notes, "ar")
    assert md.count("Not translated yet") == 1 and md.index("## 0.19.0") < md.index("Not translated")
    assert "Not translated" not in _notes_markdown([up.Notes("0.20.0", "- a", True)], "en")


def test_menu_item_opens_this_versions_notes(monkeypatch):
    app = _qapp()
    from PySide6.QtWidgets import QDialog, QDialogButtonBox

    from printview3d import i18n
    from printview3d.ui import update_ui
    seen = {}

    def fake_exec(dlg):
        seen["title"] = dlg.windowTitle()
        seen["notes"] = dlg._notes
        bb = dlg.findChild(QDialogButtonBox)
        seen["buttons"] = [b.text() for b in bb.buttons()]
        return 0
    monkeypatch.setattr(QDialog, "exec", fake_exec)
    try:
        i18n.apply_language(app, "nl")
        update_ui.show_current(None)
        assert seen["title"] == f"Wat is er nieuw in {__version__}"
        (n,) = seen["notes"]
        assert n.version == __version__ and n.translated
        assert "Alle wijzigingen op GitHub" in seen["buttons"]
    finally:
        i18n.apply_language(app, "en")


def test_menu_has_whats_new_between_updates_and_about(tmp_path, monkeypatch):
    if sys.platform == "darwin":
        import pytest
        pytest.skip("the VTK 3D view cannot be created offscreen on macOS")
    _qapp()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from printview3d.ui.main_window import MainWindow
    win = MainWindow(Settings(str(tmp_path / "settings.json")))
    try:
        acts = win.main_menu.actions()
        i = acts.index(win.act_whats_new)
        assert acts[i - 1] is win.act_updates and acts[i + 1] is win.act_about
        assert win.act_whats_new.text() == "What's new"
    finally:
        win.close()
        win.deleteLater()

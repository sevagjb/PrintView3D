"""The one-time GitHub star message: new installs see it once, people updating never do."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from printview3d.settings import Settings  # noqa: E402


def test_new_install_has_not_seen_it(tmp_path):
    s = Settings(str(tmp_path / "settings.json"))          # no settings file yet = new install
    assert s.get("star_prompt_shown") is False


def test_update_from_older_version_never_shows_it(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"language": "nl", "update_check": True}), encoding="utf-8")
    assert Settings(str(path)).get("star_prompt_shown") is True


def test_settings_saved_before_the_first_window_still_count_as_new(tmp_path):
    # e.g. "Send to slicer" from the Explorer menu right after installing, before ever opening PrintView3D
    path = str(tmp_path / "settings.json")
    Settings(path).set("slicer_id", "orca")
    assert Settings(path).get("star_prompt_shown") is False


def test_shown_once_is_remembered(tmp_path):
    path = str(tmp_path / "settings.json")
    s = Settings(path)
    s.set("star_prompt_shown", True)
    assert Settings(path).get("star_prompt_shown") is True


# --- 0.21.2: the first start shows only the main window --------------------------------------

def test_new_install_starts_at_zero(tmp_path):
    assert Settings(str(tmp_path / "settings.json")).get("start_count") == 0


def test_update_from_older_version_counts_as_started_before(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"language": "nl", "update_check": True}), encoding="utf-8")
    assert Settings(str(path)).get("start_count") == 2


def _start(settings, monkeypatch):
    """Run the start-up step of the main window once, recording what it does."""
    from types import SimpleNamespace

    from printview3d.ui import main_window as mw

    calls = []
    monkeypatch.setattr(mw.up, "just_updated", lambda s: "")
    win = SimpleNamespace(settings=settings,
                          _maybe_ask_for_star=lambda: calls.append("star"),
                          _maybe_check_updates=lambda: calls.append("check"))
    mw.MainWindow._first_update_step(win)
    return calls


def test_first_start_asks_nothing(tmp_path, monkeypatch):
    s = Settings(str(tmp_path / "settings.json"))
    assert _start(s, monkeypatch) == []                     # no star message, no update question
    assert s.get("start_count") == 1
    assert s.get("update_check") is None                    # still to be asked, on the next start


def test_star_message_comes_on_the_third_start(tmp_path, monkeypatch):
    s = Settings(str(tmp_path / "settings.json"))
    s.set("update_check", False)                            # answered on the second start
    assert _start(s, monkeypatch) == []                     # 1st
    assert _start(s, monkeypatch) == ["check"]              # 2nd
    assert _start(s, monkeypatch) == ["star", "check"]      # 3rd

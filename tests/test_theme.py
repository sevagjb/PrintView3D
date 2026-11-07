"""Colour themes: settings, migration for existing users, live switching."""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication  # noqa: E402

from printview3d.settings import Settings  # noqa: E402
from printview3d.ui import theme  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_new_install_follows_system(tmp_path):
    assert Settings(str(tmp_path / "settings.json")).get("theme") == "auto"


def test_existing_users_keep_dark(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"language": "en", "recent_files": []}))
    assert Settings(str(p)).get("theme") == "dark"


def test_saved_choice_is_kept(tmp_path):
    p = tmp_path / "settings.json"
    s = Settings(str(p))
    s.set("theme", "light")
    assert Settings(str(p)).get("theme") == "light"


def test_all_themes_have_the_same_colour_keys():
    keys = set(theme.THEMES["dark"])
    for name, colours in theme.THEMES.items():
        assert set(colours) == keys, name
        for value in colours.values():
            assert value.startswith("#") and len(value) == 7


@pytest.mark.parametrize("name", ["dark", "gray", "light", "ember", "ember_dark", "gray_light", "graphite_light"])
def test_apply_theme(app, name):
    assert theme.apply_theme(app, name) == name
    assert theme.current() == name
    assert app.palette().window().color().name() == theme.THEMES[name]["window"]


def test_auto_resolves_to_a_real_theme(app):
    assert theme.apply_theme(app, "auto") in ("dark", "light")
    assert theme.setting() == "auto"


def test_unknown_value_falls_back_to_auto(app):
    theme.apply_theme(app, "purple")
    assert theme.setting() == "auto"


def test_styles_and_modes():
    assert list(theme.STYLES) == ["default", "gray", "graphite", "ember"]
    assert theme.MODES == ("light", "dark", "system")
    # Every style has a light and a dark theme, and together they are all the themes.
    assert {k for pair in theme.STYLES.values() for k in pair} == set(theme.THEMES)
    for light, dark in theme.STYLES.values():
        assert not theme.is_dark(light) and theme.is_dark(dark)


@pytest.mark.parametrize("old,style,mode", [
    # Every value older versions saved keeps meaning the same thing.
    ("auto", "default", "system"), ("dark", "default", "dark"), ("light", "default", "light"),
    ("gray", "gray", "dark"), ("graphite", "graphite", "dark"),
    ("ember", "ember", "light"), ("ember_dark", "ember", "dark"),
    # New values.
    ("gray_light", "gray", "light"), ("graphite_light", "graphite", "light"), ("auto_ember", "ember", "system"),
])
def test_saved_values_map_to_style_and_mode(old, style, mode):
    assert theme.split_choice(old) == (style, mode)
    assert theme.make_choice(style, mode) == old
    assert theme.is_valid_choice(old)


def test_unknown_values_are_not_valid():
    for bad in ("purple", "auto_purple", "", "auto_default"):
        assert not theme.is_valid_choice(bad), bad
    assert theme.split_choice("purple") == ("default", "system")


def test_cli_lists_every_choice():
    from printview3d.app import THEME_CHOICES
    assert set(THEME_CHOICES) == set(theme.all_choices())


def test_system_mode_follows_the_computer(app, monkeypatch):
    monkeypatch.setattr(theme, "system_theme", lambda: "light")
    assert theme.resolve("auto_ember") == "ember" and theme.resolve("auto") == "light"
    monkeypatch.setattr(theme, "system_theme", lambda: "dark")
    assert theme.resolve("auto_ember") == "ember_dark" and theme.resolve("auto_gray") == "gray"
    assert theme.apply_theme(app, "auto_graphite") == "graphite"
    assert theme.setting() == "auto_graphite" and theme.follows_system()
    theme.apply_theme(app, "dark")


def test_next_theme_keeps_the_mode():
    seen, t = [], "light"
    for _ in range(4):
        t = theme.next_theme(t)
        seen.append(t)
    assert seen == ["gray_light", "graphite_light", "ember", "light"]
    assert theme.next_theme("ember_dark") == "dark"
    assert theme.next_theme("auto") == "auto_gray"
    assert theme.next_theme("auto_ember") == "auto"


def test_toggle_light_dark(monkeypatch):
    assert theme.toggle_light_dark("ember") == "ember_dark"
    assert theme.toggle_light_dark("gray") == "gray_light"
    monkeypatch.setattr(theme, "system_theme", lambda: "dark")
    assert theme.toggle_light_dark("auto_ember") == "ember"        # from System: the opposite of now


def test_theme_icon_draws(app):
    for name in theme.THEMES:
        assert not theme.theme_icon(name).isNull()


def test_segment_icons_draw(app):
    for kind in ("light", "dark", "system", "off", "mica", "acrylic"):
        assert not theme.segment_icon(kind).isNull()


@pytest.mark.parametrize("name", ["gray_light", "graphite_light"])
def test_new_light_themes_are_readable(name):
    t = theme.THEMES[name]
    for fg, bg in (("text", "window"), ("text", "bar"), ("text", "base"), ("muted", "window"),
                   ("link", "window"), ("group_title", "window")):
        assert _contrast(t[fg], t[bg]) >= 4.5, (fg, bg)


def test_selector_fill_is_readable_with_white_text():
    for name in theme.THEMES:
        assert _contrast(theme.segment_color(name), "#ffffff") >= 2.4, name


def test_mica_makes_only_the_main_window_transparent(app):
    from printview3d.ui import theme
    theme.apply_theme(app, "dark", mica=False)
    assert "transparent; }" not in app.styleSheet().split("QLabel#versionBadge:hover")[1]
    theme.apply_theme(app, "dark", mica=True)
    css = app.styleSheet()
    assert "QToolBar#mainToolbar" in css and "QStatusBar#mainStatusBar" in css and "#centralStack" in css
    assert "{ background: transparent; }" in css
    assert "{{" not in css                                    # the template was filled in
    theme.apply_theme(app, "dark")                            # back to normal for the other tests


def test_mica_leaves_dialogs_solid(app):
    """0.15.0: a dialog opened from the main window is its child, and the Mica rules made it
    transparent (black on Windows). Only the main window's own named parts may be transparent."""
    from PySide6.QtWidgets import (QDialog, QMainWindow, QScrollArea, QStackedWidget, QToolBar,
                                   QVBoxLayout, QWidget)
    from printview3d.ui import theme
    theme.apply_theme(app, "light", mica=True)
    try:
        win = QMainWindow()
        win.setObjectName("mainWindow")
        stack = QStackedWidget()
        stack.setObjectName("centralStack")
        side = QScrollArea()
        side.setWidget(QWidget())
        stack.addWidget(side)
        win.setCentralWidget(stack)
        tb = QToolBar()
        tb.setObjectName("mainToolbar")
        win.addToolBar(tb)
        dlg = QDialog(win)
        lay = QVBoxLayout(dlg)
        pages = QStackedWidget()
        scroll = QScrollArea()
        scroll.setWidget(QWidget())
        pages.addWidget(scroll)
        lay.addWidget(pages)

        def alpha(w):
            w.ensurePolished()
            return w.palette().color(w.backgroundRole()).alpha()

        assert alpha(win) == 0 and alpha(stack) == 0                       # main window: see-through
        assert 0 < alpha(tb) < 255                                          # toolbar: frosted layer
        for w in (dlg, pages, scroll, scroll.widget()):                     # dialog: solid
            assert alpha(w) == 255, type(w).__name__
    finally:
        theme.apply_theme(app, "dark")


def test_mica_not_offered_off_windows():
    import sys
    from printview3d import win_mica
    if sys.platform != "win32":
        assert not win_mica.supported()
        assert not win_mica.apply(0, True)


def test_backdrop_choice_and_old_mica_switch(tmp_path):
    from printview3d import win_mica
    s = Settings(str(tmp_path / "s.json"))
    assert win_mica.choice(s) == "off"                       # new install
    s.set("mica", True)
    assert win_mica.choice(s) == "mica"                      # 0.15's switch still counts
    s.set("backdrop", "acrylic")
    assert win_mica.choice(s) == "acrylic"
    s.set("backdrop", "nonsense")
    assert win_mica.choice(s) == "off"


def test_glass_layer_is_stronger_in_the_light_theme(app):
    import re
    def alpha(css, selector):
        block = css.split(selector, 1)[1].split("}", 1)[0]
        return float(re.search(r"rgba\(\d+, \d+, \d+, ([\d.]+)\)", block).group(1))
    theme.apply_theme(app, "light", mica=True)
    light = alpha(app.styleSheet(), "QStackedWidget#centralStack QScrollArea > QWidget > QWidget {")
    theme.apply_theme(app, "dark", mica=True)
    dark = alpha(app.styleSheet(), "QStackedWidget#centralStack QScrollArea > QWidget > QWidget {")
    assert light > dark >= 0.4
    theme.apply_theme(app, "dark")


def test_toolbar_icons_draw_in_every_theme(app):
    for name in theme.THEMES:
        theme.apply_theme(app, name)
        for kind in theme.TOOL_ICONS:
            assert not theme.tool_icon(kind).isNull(), (name, kind)
            assert not theme.tool_icon(kind, on_accent=True).isNull(), (name, kind)
    theme.apply_theme(app, "dark")


def test_toolbar_icons_fill_with_the_primary_colour_on_hover(app):
    """Under the mouse a toolbar icon's tile fills with the theme's primary colour (amber in
    Ember, teal elsewhere), like the view cube's hovered part; without hover=True it has no
    hover picture, so push buttons with a focus never show it."""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QColor, QIcon
    from printview3d.ui.view_cube import readable_text
    for name in theme.THEMES:
        theme.apply_theme(app, name)
        t = theme.colors()
        for kwargs in ({}, {"warm": True}, {"on_accent": True, "gap": True}):
            icon = theme.tool_icon("open", hover=True, **kwargs)
            normal = icon.pixmap(QSize(64, 64), QIcon.Normal).toImage()
            hover = icon.pixmap(QSize(64, 64), QIcon.Active).toImage()
            assert QColor(hover.pixel(3, 32)).name() == t["primary"], (name, kwargs)
            assert QColor(normal.pixel(3, 32)).name() != t["primary"] or normal.pixelColor(3, 32).alpha() < 255
            assert readable_text(t["primary"]) in ("#ffffff", "#1a1d21")
        slicer = theme.tool_icon("slicer", on_accent=True, gap=True, hover=True, on_primary=True)
        assert QColor(slicer.pixmap(QSize(80, 64), QIcon.Active).toImage().pixel(3, 32)).name() == "#ffffff", name
        plain = theme.tool_icon("open")
        a = plain.pixmap(QSize(64, 64), QIcon.Normal).toImage()
        b = plain.pixmap(QSize(64, 64), QIcon.Active).toImage()
        assert a == b, name
    theme.apply_theme(app, "dark")


def test_keys_page_lists_the_shortcuts(app, tmp_path):
    """The Settings window builds, and Keyboard and mouse shows every key of the main window."""
    from printview3d.ui import keys as k
    from printview3d.ui.settings_dialog import SettingsDialog, mouse_rows
    d = SettingsDialog(Settings(str(tmp_path / "settings.json")), page="keys")
    shown = {e.keySequence().toString() for e in d.key_edits.values()}
    for key in ("Ctrl+O", "Ctrl+P", "Ctrl+E", "Ctrl+T", "Ctrl+Shift+T", "1", "2", "3", "4"):
        assert key in shown, key
    assert set(d.key_edits) == set(k.IDS)
    assert len(mouse_rows()) >= 3
    d.deleteLater()


# ------------------------------------------------------------------ Ember themes, theme cards

EMBER_ORANGE, EMBER_TEAL, EMBER_CREAM = "#ef791b", "#2cc1b2", "#edebe4"


def test_ember_uses_the_exact_colours():
    """Orange, teal and cream exactly as chosen (sampled from the reference design)."""
    for name in ("ember", "ember_dark"):
        t = theme.THEMES[name]
        assert t["primary"] == EMBER_ORANGE and t["accent"] == EMBER_TEAL, name
    assert theme.THEMES["ember"]["window"] == EMBER_CREAM


def test_light_and_dark_themes():
    assert not theme.is_dark("light") and not theme.is_dark("ember")
    for name in ("dark", "gray", "graphite", "ember_dark"):
        assert theme.is_dark(name), name


def test_classic_themes_keep_their_teal():
    for name in ("dark", "gray", "graphite", "light"):
        assert theme.THEMES[name]["primary"] == theme.THEMES[name]["accent"] == theme.ACCENT


def _contrast(a: str, b: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", ["ember", "ember_dark"])
def test_ember_text_is_readable(name):
    t = theme.THEMES[name]
    for fg, bg in (("text", "window"), ("text", "bar"), ("text", "base"), ("muted", "window"), ("link", "window")):
        assert _contrast(t[fg], t[bg]) >= 4.5, (fg, bg)


def test_primary_colour_reaches_the_style_sheet(app):
    theme.apply_theme(app, "ember")
    css = app.styleSheet()
    assert f"QToolButton#slicerButton {{ background: {EMBER_ORANGE}" in css
    assert f"QSlider::sub-page:horizontal {{ background: {EMBER_TEAL}" in css
    assert app.palette().highlight().color().name() == EMBER_ORANGE
    theme.apply_theme(app, "dark")


def test_previews_and_swatches_draw(app):
    for name in list(theme.THEMES) + ["auto"]:
        pm = theme.theme_preview(name, 112, 70)
        assert not pm.isNull() and pm.deviceIndependentSize().width() == 112
        assert not theme.theme_swatch(name).isNull()
        assert not theme.tool_icon("theme", warm=True).isNull()


def test_theme_cards_preview_live_and_cancel_goes_back(app, tmp_path):
    from printview3d.ui.settings_dialog import SettingsDialog
    s = Settings(str(tmp_path / "settings.json"))
    s.set("theme", "dark")
    theme.apply_theme(app, "dark")
    d = SettingsDialog(s, page="appearance")
    assert list(d.theme_cards) == list(theme.STYLES)
    assert d.theme_cards["default"].isChecked() and d.mode_selector.value() == "dark"
    d.theme_cards["ember"].click()                      # Ember, still dark
    assert theme.current() == "ember_dark" and d.theme_choice() == "ember_dark"
    assert d.theme_cards["ember"].isChecked() and not d.theme_cards["default"].isChecked()
    d.mode_selector.buttons["light"].click()            # Ember, now light
    assert theme.current() == "ember" and d.theme_choice() == "ember"
    assert d.theme_cards["ember"].isChecked()
    d.reject()
    assert theme.current() == "dark" and s.get("theme") == "dark"


def test_theme_card_ok_saves(app, tmp_path):
    from printview3d.ui.settings_dialog import SettingsDialog
    s = Settings(str(tmp_path / "settings.json"))
    s.set("theme", "dark")
    theme.apply_theme(app, "dark")
    d = SettingsDialog(s, page="appearance")
    d.theme_cards["ember"].click()
    d._save()
    assert s.get("theme") == "ember_dark"
    theme.apply_theme(app, "dark")


def test_system_mode_ok_saves(app, tmp_path):
    from printview3d.ui.settings_dialog import SettingsDialog
    s = Settings(str(tmp_path / "settings.json"))
    s.set("theme", "gray")
    theme.apply_theme(app, "gray")
    d = SettingsDialog(s, page="appearance")
    assert d.theme_cards["gray"].isChecked() and d.mode_selector.value() == "dark"
    d.mode_selector.buttons["system"].click()
    d._save()
    assert s.get("theme") == "auto_gray"
    theme.apply_theme(app, "dark")


def test_transparency_selector(app, tmp_path):
    from printview3d import win_mica
    from printview3d.ui.settings_dialog import SettingsDialog
    d = SettingsDialog(Settings(str(tmp_path / "settings.json")), page="appearance")
    assert list(d.backdrop_selector.buttons) == ["off", "mica", "acrylic"]
    assert d.backdrop_selector.value() == "off"
    assert d.backdrop_selector.isEnabled() == win_mica.supported()      # Windows 11 only
    d.deleteLater()


# --- 0.21.2: Linux without a colour-scheme answer from Qt starts light ------------------------

def _no_gsettings(_key):
    return ""


def test_linux_nothing_known_is_light(tmp_path):
    assert theme._linux_prefers_dark(env={}, home=str(tmp_path), run=_no_gsettings) is False


def test_linux_gnome_prefer_dark(tmp_path):
    run = {"color-scheme": "prefer-dark"}.get
    assert theme._linux_prefers_dark(env={}, home=str(tmp_path), run=lambda k: run(k, "")) is True


def test_linux_gnome_default_is_light_even_with_dark_named_gtk_theme_unset(tmp_path):
    run = {"color-scheme": "default", "gtk-theme": "Adwaita"}.get
    assert theme._linux_prefers_dark(env={}, home=str(tmp_path), run=lambda k: run(k, "")) is False


def test_linux_gtk_theme_variable(tmp_path):
    assert theme._linux_prefers_dark(env={"GTK_THEME": "Adwaita:dark"}, home=str(tmp_path),
                                     run=_no_gsettings) is True


def test_linux_kde_breeze_dark(tmp_path):
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "kdeglobals").write_text("[General]\nColorScheme=BreezeDark\n")
    assert theme._linux_prefers_dark(env={}, home=str(tmp_path), run=_no_gsettings) is True


def test_linux_gtk3_prefer_dark(tmp_path):
    d = tmp_path / ".config" / "gtk-3.0"
    d.mkdir(parents=True)
    (d / "settings.ini").write_text("[Settings]\ngtk-application-prefer-dark-theme=1\n")
    assert theme._linux_prefers_dark(env={}, home=str(tmp_path), run=_no_gsettings) is True


def test_unknown_scheme_on_windows_and_macos_stays_dark(app, monkeypatch):
    from PySide6.QtCore import Qt
    hints = app.styleHints()
    monkeypatch.setattr(type(hints), "colorScheme", lambda self: Qt.ColorScheme.Unknown)
    for platform in ("win32", "darwin"):
        monkeypatch.setattr(theme.sys, "platform", platform)
        assert theme.system_theme() == "dark"


@pytest.mark.parametrize("name", ["dark", "light", "ember", "ember_dark"])
def test_slider_handle_is_round_and_not_cut_off(app, name):
    """The slider is tall enough for its round handle (issue #66: the top and bottom were cut)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider

    theme.apply_theme(app, name)
    s = QSlider(Qt.Horizontal)
    s.setRange(0, 100)
    s.resize(200, s.sizeHint().height())
    s.ensurePolished()
    opt = QStyleOptionSlider()
    s.initStyleOption(opt)
    handle = s.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, s)
    assert handle.width() == handle.height()                    # round, not a pill
    assert s.rect().contains(handle)                            # all of it inside the slider

"""Translation helper for PrintView3D.

    python tools/i18n.py update    collect all tr()/tr_noop() texts from the code into
                                   translations/*.ts (new texts are added as "needs
                                   translation", removed texts are marked obsolete)
    python tools/i18n.py compile   build the .qm files the app loads
                                   (src/printview3d/resources/translations/)
    python tools/i18n.py check     fail if the .ts files are out of date or a translation
                                   breaks a {placeholder}; used by the tests and CI
    python tools/i18n.py stats     show how complete each language is (program texts and
                                   the translated changelogs, CHANGELOG.<xx>.md)
    python tools/i18n.py new XX    start a new language (XX = code, e.g. it, pt_BR, tr)

Files
-----
translations/printview3d.ts        template: every English text, no translations
                                   (`new` starts a language from it)
translations/printview3d_<xx>.ts   one file per language (Qt Linguist format)

The .ts files can be edited with Qt Linguist (pyside6-linguist), in GitHub's
editor, or in any text editor. Guide for translators: docs/TRANSLATING.md
"""

from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "printview3d")
TS_DIR = os.path.join(ROOT, "translations")
QM_DIR = os.path.join(SRC, "resources", "translations")
TEMPLATE = os.path.join(TS_DIR, "printview3d.ts")
CONTEXT = "PrintView3D"
PLACEHOLDER = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")

# Notes shown to translators (in Qt Linguist and the .ts files) for texts that are
# ambiguous on their own.
NOTES = {
    "Fit": "Toolbar button: zoom the 3D view so the whole model fits.",
    "Iso": "Toolbar button: isometric camera view (seen from a corner, slightly above).",
    "Top": "Toolbar button: camera view from above.",
    "Front": "Toolbar button: camera view from the front.",
    "Back": "Label on the view cube: camera view from behind.",
    "Left": "Label on the view cube: camera view from the left.",
    "Bottom": "Label on the view cube: camera view from below.",
    "Right": "Toolbar button: camera view from the right side (not 'correct').",
    "Plate": "Toolbar toggle: show or hide the printer's build plate / bed grid.",
    "View": "Toolbar menu: how the model is drawn (wireframe, X-ray, clip from the top).",
    "Clip from the top": "Hide everything above a chosen height, to look inside the model (a cut).",
    "Height {z} of {top} mm": "Clip slider: {z} is the height of the cut above the model's bottom, {top} its full height.",
    "Recent": "Toolbar menu with recently opened files.",
    "All": "Button: show all print feature types.",
    "None": "Button: hide all print feature types.",
    "Found": "Status: the chosen slicer program file exists.",
    "{view} view ({key})": "Tooltip. {view} is a translated view name (Top, Front...), {key} a keyboard key.",
    "{kind} · {size} MB": "Under the file name. {kind} is STL, 3MF or G-code; {size} the file size.",
    "Register && choose as default…": "'&&' shows a single '&' on the button; keep it as '&&' or use a word.",
    "Register && make default": "'&&' shows a single '&' on the button; keep it as '&&' or use a word.",
    "Slicer": "A slicer is the program that turns a 3D model into G-code (e.g. Creality Print, OrcaSlicer).",
    "Sparse infill": "3D printing term: the partially filled inside of a print.",
    "Skirt / brim": "3D printing terms: lines printed around the model on the first layer.",
    "Prime tower": "3D printing term: tower printed to prime the nozzle after a color/material change.",
    "Ironing": "3D printing term: smoothing the top surface with the hot nozzle.",
    "Travel moves": "3D printing term: nozzle movements without printing.",
    "<b>Layer {n}</b> of {total}  ·  Z = {z} mm": "Keep <b>...</b> around the layer number.",
    "Theme": "Settings: the colour theme of the program (dark, gray, light).",
    "Dark": "Colour theme name.",
    "Gray": "Colour theme name.",
    "Light": "Colour theme name: light colours (not 'not heavy').",
    "Graphite": "Colour theme name: a warm, dark brownish charcoal.",
    "Theme: {name} (Ctrl+T: next theme)": "Tooltip of the theme icon. {name} is the current theme (Dark, Gray...).",
    "Files": "Settings page: which file types open with PrintView3D (default program).",
    "today {time}": "When the last update check was. {time} is e.g. 14:02.",
    "Skip this version": "Update button: do not show this new version again (the next one is shown).",
    "Plate {n}": "A build plate inside a slicer project; {n} is its number.",
    "Missing or wrong translation? Anyone can correct it on GitHub: {guide}":
        "Settings → Language. {guide} becomes the link 'How to translate on GitHub'.",
    "Home": "Toolbar button with a house icon: closes the open file and goes back to the start page.",
    "Close the file and go back to the start page ({key})": "Tooltip of the Home button. {key} is its "
        "keyboard shortcut (Ctrl+W).",
    "Change what a click does…": "Last item in the menu of the Export STL button: opens the setting "
        "that decides what clicking the button itself does.",
    "{key} does the same. The arrow next to the button always offers all three ways. A file with only one "
    "object is always saved straight away.": "Settings → Files → Export STL. {key} is the keyboard shortcut (Ctrl+E).",
    "Star on GitHub": "Button: opens the project page on GitHub, where people can 'star' (like) it.",
    "Like PrintView3D? {star} It helps other people find it.":
        "Settings → About. {star} becomes the link 'Give it a star on GitHub.'",
    "Give it a star on GitHub.": "Link text. A 'star' on GitHub is like a 'like' or bookmark.",
}


@dataclass
class Message:
    source: str
    locations: list[tuple[str, int]] = field(default_factory=list)
    translation: str = ""
    status: str = "unfinished"       # "", "unfinished", "vanished"
    comment: str = ""
    note: str = ""                   # explanation for translators (from NOTES)


# ------------------------------------------------------------------ extract
def extract() -> dict[str, Message]:
    """All texts passed to tr() / tr_noop() in the source code, in order of appearance."""
    found: dict[str, Message] = {}
    for dirpath, _dirs, files in sorted(os.walk(SRC)):
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, TS_DIR).replace(os.sep, "/")
            tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                fn = node.func
                fname = fn.id if isinstance(fn, ast.Name) else None
                if fname not in ("tr", "tr_noop"):
                    continue
                arg = node.args[0]
                if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
                    if fname == "tr_noop":
                        raise SystemExit(f"{path}:{node.lineno}: tr_noop() needs a plain text")
                    continue        # tr(variable): the text was marked with tr_noop() elsewhere
                msg = found.setdefault(arg.value, Message(arg.value, note=NOTES.get(arg.value, "")))
                msg.locations.append((rel, node.lineno))
    # Keep the order stable: by file, then line.
    return dict(sorted(found.items(), key=lambda kv: kv[1].locations[0]))


# ------------------------------------------------------------------- .ts io
def read_ts(path: str) -> tuple[str, dict[str, Message]]:
    root = ET.parse(path).getroot()
    lang = root.get("language", "")
    out: dict[str, Message] = {}
    for msg in root.iter("message"):
        src = msg.findtext("source") or ""
        t = msg.find("translation")
        m = Message(src)
        if t is not None:
            m.translation = t.text or ""
            m.status = t.get("type", "")
        m.comment = msg.findtext("translatorcomment") or ""
        out[src] = m
    return lang, out


def _esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))


def write_ts(path: str, lang: str, messages: list[Message]) -> None:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<!DOCTYPE TS>",
             '<TS version="2.1"' + (f' language="{lang}"' if lang else "") + ">",
             "<context>", f"    <name>{CONTEXT}</name>"]
    for m in messages:
        lines.append("    <message>")
        # File names only, no line numbers: line numbers change with almost every code edit,
        # and then clash with translation pull requests made at the same time (merge conflicts).
        for f in dict.fromkeys(f for f, _line in m.locations):
            # Written the way Qt Linguist writes it, so saving there doesn't rewrite every line.
            lines.append(f'        <location filename="{f}"></location>')
        lines.append(f"        <source>{_esc(m.source)}</source>")
        if m.note:
            lines.append(f"        <extracomment>{_esc(m.note)}</extracomment>")
        if m.comment:
            lines.append(f"        <translatorcomment>{_esc(m.comment)}</translatorcomment>")
        typ = f' type="{m.status}"' if m.status else ""
        lines.append(f"        <translation{typ}>{_esc(m.translation)}</translation>")
        lines.append("    </message>")
    lines += ["</context>", "</TS>", ""]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


def language_files() -> dict[str, str]:
    out = {}
    if os.path.isdir(TS_DIR):
        for name in sorted(os.listdir(TS_DIR)):
            m = re.fullmatch(r"printview3d_([A-Za-z_]+)\.ts", name)
            if m:
                out[m.group(1)] = os.path.join(TS_DIR, name)
    return out


# ------------------------------------------------------------------ commands
def merged(path: str, lang: str, source: dict[str, Message]) -> list[Message]:
    _, existing = read_ts(path) if os.path.exists(path) else ("", {})
    out = []
    for src, m in source.items():
        new = Message(src, list(m.locations), note=m.note)
        old = existing.get(src)
        if old is not None and old.status != "vanished":
            new.translation, new.status, new.comment = old.translation, old.status, old.comment
        out.append(new)
    # Texts no longer in the code are kept as "vanished" so work isn't lost.
    for src, old in existing.items():
        if src not in source and old.translation:
            out.append(Message(src, [], old.translation, "vanished", old.comment))
    return out


def cmd_update() -> None:
    source = extract()
    os.makedirs(TS_DIR, exist_ok=True)
    write_ts(TEMPLATE, "", [Message(s, list(m.locations), note=m.note) for s, m in source.items()])
    for lang, path in language_files().items():
        write_ts(path, lang, merged(path, lang, source))
    print(f"{len(source)} texts; updated {len(language_files())} language file(s) and the template.")


def cmd_new(lang: str) -> None:
    path = os.path.join(TS_DIR, f"printview3d_{lang}.ts")
    if os.path.exists(path):
        raise SystemExit(f"{path} already exists")
    write_ts(path, lang, merged(path, lang, extract()))
    print(f"Created {os.path.relpath(path, ROOT)}. Add the language to LANGUAGES in "
          "src/printview3d/i18n.py so it appears in Settings.")


def _lrelease() -> list[str]:
    exe = "pyside6-lrelease.exe" if sys.platform == "win32" else "pyside6-lrelease"
    here = os.path.join(os.path.dirname(sys.executable), exe)
    if os.path.isfile(here):
        return [here]
    found = shutil.which("pyside6-lrelease") or shutil.which("lrelease")
    if found:
        return [found]
    raise SystemExit("pyside6-lrelease not found (it comes with PySide6: pip install PySide6-Essentials)")


def cmd_compile() -> None:
    os.makedirs(QM_DIR, exist_ok=True)
    tool = _lrelease()
    for lang, path in language_files().items():
        out = os.path.join(QM_DIR, f"printview3d_{lang}.qm")
        subprocess.run(tool + ["-silent", path, "-qm", out], check=True)
    import json
    status = {lang: done * 100 // max(1, total) for lang, (total, done, _rev) in stats().items()}
    with open(os.path.join(QM_DIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, indent=1, sort_keys=True)
    print(f"Compiled {len(language_files())} language(s) into {os.path.relpath(QM_DIR, ROOT)}")


def problems() -> list[str]:
    errors = []
    source = extract()
    if not os.path.exists(TEMPLATE):
        return ["translations/printview3d.ts is missing - run: python tools/i18n.py update"]
    _, tmpl = read_ts(TEMPLATE)
    missing = [s for s in source if s not in tmpl]
    if missing:
        errors.append(f"{len(missing)} new text(s) not in the translation files, e.g. {missing[0]!r} "
                      "- run: python tools/i18n.py update")
    for lang, path in language_files().items():
        _, msgs = read_ts(path)
        if [s for s in source if s not in msgs]:
            errors.append(f"{lang}: out of date - run: python tools/i18n.py update")
        for src, m in msgs.items():
            if not m.translation or m.status == "vanished":
                continue
            want, got = sorted(PLACEHOLDER.findall(src)), sorted(PLACEHOLDER.findall(m.translation))
            if want != got:
                errors.append(f"{lang}: placeholders differ in {src!r}: expected {want}, found {got}")
            if src.count("<b>") != m.translation.count("<b>"):
                errors.append(f"{lang}: <b> tags differ in {src!r}")
    return errors


def stats() -> dict[str, tuple[int, int, int]]:
    """lang -> (total, translated, reviewed)."""
    total = len(extract())
    out = {}
    for lang, path in language_files().items():
        _, msgs = read_ts(path)
        live = [m for m in msgs.values() if m.status != "vanished"]
        translated = sum(1 for m in live if m.translation)
        reviewed = sum(1 for m in live if m.translation and m.status == "")
        out[lang] = (total, translated, reviewed)
    return out


# ---------------------------------------------------------------- translated changelogs
# CHANGELOG.md is the English original; CHANGELOG.<code>.md a translation with the same
# "## 0.22.0" headings. The program shows a version that isn't translated yet in English.
CHANGELOG_HEADING = re.compile(r"^## +(\S+)", re.MULTILINE)


def changelog_versions(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return CHANGELOG_HEADING.findall(f.read())


def changelog_files() -> dict[str, str]:
    """lang -> path of every translated changelog (CHANGELOG.<lang>.md)."""
    out = {}
    for name in sorted(os.listdir(ROOT)):
        m = re.fullmatch(r"CHANGELOG\.([A-Za-z_]+)\.md", name)
        if m:
            out[m.group(1)] = os.path.join(ROOT, name)
    return out


def changelog_problems() -> list[str]:
    """Headings a program can't match: versions the English changelog doesn't have (a typo such
    as "## 0.10" for 0.1.0, or a version that isn't released yet), or versions out of order."""
    english = changelog_versions(os.path.join(ROOT, "CHANGELOG.md"))
    errs = []
    for path in changelog_files().values():
        got = changelog_versions(path)
        for v in got:
            if v not in english:
                errs.append(f"{os.path.basename(path)}: '## {v}' is not a version in CHANGELOG.md")
        known = [v for v in got if v in english]
        if known != [v for v in english if v in known]:
            errs.append(f"{os.path.basename(path)}: versions are not in the same order as CHANGELOG.md")
        if len(set(got)) != len(got):
            errs.append(f"{os.path.basename(path)}: a version appears twice")
    return errs


def changelog_missing() -> dict[str, list[str]]:
    """lang -> English versions its changelog doesn't have yet (shown in English)."""
    english = changelog_versions(os.path.join(ROOT, "CHANGELOG.md"))
    return {lang: [v for v in english if v not in changelog_versions(path)]
            for lang, path in changelog_files().items()}


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[0]
    if cmd == "update":
        cmd_update()
    elif cmd == "compile":
        cmd_compile()
    elif cmd == "new" and len(argv) == 2:
        cmd_new(argv[1])
    elif cmd == "check":
        errs = problems() + changelog_problems()
        for e in errs:
            print("ERROR:", e)
        if errs:
            return 1
        print("Translations OK.")
    elif cmd == "stats":
        for lang, (total, done, reviewed) in stats().items():
            print(f"{lang:6} {done * 100 // max(1, total):3}% translated, "
                  f"{reviewed * 100 // max(1, total):3}% reviewed  ({done}/{total})")
        print()
        print("What's new (CHANGELOG.<lang>.md; missing versions are shown in English):")
        missing = changelog_missing()
        for lang in stats():
            if lang not in missing:
                print(f"{lang:6} not translated (English)")
            elif missing[lang]:
                shown = ", ".join(missing[lang][:5]) + (" ..." if len(missing[lang]) > 5 else "")
                print(f"{lang:6} missing {len(missing[lang])}: {shown}")
            else:
                print(f"{lang:6} complete")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

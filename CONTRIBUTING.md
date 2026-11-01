# Contributing to PrintView3D

Thanks for helping! Issues and pull requests are welcome.

## Reporting a problem

Open an [issue](../../issues) and include:
- what you did, what you expected and what happened
- your Windows version and the PrintView3D version (**About** button)
- if a file does not open: the error message, and if possible the file (or a small file that
  fails the same way)

## Adding a slicer

Slicers are listed in `SLICERS` in `src/printview3d/slicer.py`. A new entry needs:

```python
Slicer("my_slicer", "My Slicer",
       ("MySlicer.exe",),            # exact program file name(s)
       ("myslicer",),                # fallback: part of the program file name
       r"my\s*slicer",               # regex for its name in "Installed apps"
       (r"MySlicer*", r"Programs\MySlicer*")),  # install folders (Program Files / LocalAppData)
```

`linux_bins` are command names on the PATH; `linux_match` is the text that identifies the slicer
in AppImage / Flatpak / Snap names, compared lowercase without spaces, `-` and `_`
(e.g. `"myslicer"` matches `My_Slicer-1.2.AppImage` and `com.example.MySlicer`):

```python
       linux_bins=("my-slicer",), linux_match=("myslicer",)),
```

Then add a test in `tests/test_slicer.py` if the detection has anything special.

## Translations

PrintView3D uses Qt's standard translation files: one file per language in
[`translations/`](translations) (`printview3d_ar.ts`, `printview3d_de.ts`, …). The release notes
in the program's *What's new* window come from [`CHANGELOG.md`](CHANGELOG.md) and its translations
`CHANGELOG.<code>.md` (`CHANGELOG.ar.md`, `CHANGELOG.nl.md`); versions a translation doesn't have
yet are shown in English. A translation update covers both: the new program texts and the newest
changelog section(s). See [docs/TRANSLATING.md](docs/TRANSLATING.md#whats-new-translating-the-changelog).

**Translating or correcting a translation**
- Translations are made on GitHub only. The step-by-step guide, including editing in the browser
  without installing anything, is in [docs/TRANSLATING.md](docs/TRANSLATING.md).
- Open the file in **Qt Linguist** (`pyside6-linguist`, comes with PySide6), in GitHub's editor
  or in any text editor, change the `<translation>` texts, and open a pull request.
- Keep `{placeholders}` such as `{slicer}` or `{n}` exactly as they are; they are filled in by the
  program. Keep `<b>…</b>` tags. The tests check both.
- Texts marked `type="unfinished"` are drafts that still need a native speaker's review. When a
  translation is correct, remove `type="unfinished"` (in Qt Linguist: mark it as done ✓).
- Notes for ambiguous texts (e.g. "Right" means the *right side view*) are shown next to the text.

**A new language**
```
python tools/i18n.py new it          # creates translations/printview3d_it.ts
```
Translate it, add the language to `LANGUAGES` in `src/printview3d/i18n.py`, and open a pull request.
Partly translated languages are fine: missing texts show in English.

**For developers: adding texts to the program**
- Wrap every user-visible text in `tr()`: `label.setText(tr("Show only this layer"))`.
- Use placeholders, not string concatenation: `tr("Open in {slicer}").format(slicer=name)`, so
  translators can change the word order.
- Texts defined in tables/constants: mark them with `tr_noop()` and call `tr()` when displaying them
  (see `ui/labels.py`).
- Numbers: use `num()` / `count()` from `printview3d.i18n` (decimal comma in many languages).
- Afterwards run `python tools/i18n.py update`. The tests fail if you forget, so no text can slip
  through untranslatable.

Useful commands: `python tools/i18n.py stats` (completion per language), `check`, `compile`.

## Development setup

1. Install Python 3.12 (see the README: newer versions may not be supported by VTK yet).
2. Run the build script once; it creates `.venv` with everything installed:
   `build_windows.bat` on Windows, `./build_linux.sh --no-appimage` on Linux.
3. Start the app from the source code: `run_from_source.bat` / `./run_from_source.sh`.
4. Run the tests: `.venv\Scripts\python -m pytest -q` (Windows) or `.venv/bin/python -m pytest -q`
   (Linux). Please keep them passing; GitHub runs them on both systems for every pull request.

Platform-specific code lives in a few small modules: `assoc_windows.py` / `assoc_linux.py`
(file associations), `gpu.py` (Windows GPU preference) and the detection functions in `slicer.py`.
Everything else is shared.

Keep code readable: small functions, comments that explain *why*, no new heavy dependencies
without discussion.

## Releasing (maintainers)

1. Update the version in `src/printview3d/__init__.py` and `pyproject.toml` (a test checks they
   match; the Windows file version is generated from it) and add an entry to `CHANGELOG.md`.
2. Commit and push to `main`.
3. GitHub Actions builds the Windows and Linux programs and, because the version is new, publishes
   the release with `PrintView3D-Setup.exe`, `PrintView3D-windows.zip`,
   `PrintView3D-x86_64.AppImage` and the changelog entry. The installer is test-installed and
   uninstalled on the build machine first. (Pushing a `v*` tag works too.)

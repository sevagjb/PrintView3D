# Translating PrintView3D on GitHub

All translations live in this repository. A language has two parts:

- **the program's texts**: one file per language in the [`translations/`](https://github.com/sevagjb/PrintView3D/tree/main/translations) folder;
- **What's new** (the release notes shown in the program's *What's new* window): a translated copy
  of [`CHANGELOG.md`](https://github.com/sevagjb/PrintView3D/blob/main/CHANGELOG.md), named `CHANGELOG.<code>.md`.

You change a file and send the change as a pull request; it is reviewed and merged into the next
release. No other website or account is needed, only a free GitHub account.

| Language | Program texts | What's new |
|---|---|---|
| العربية Arabic | [`printview3d_ar.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_ar.ts) | [`CHANGELOG.ar.md`](https://github.com/sevagjb/PrintView3D/blob/main/CHANGELOG.ar.md) |
| Deutsch | [`printview3d_de.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_de.ts) | not yet: shown in English |
| Español | [`printview3d_es.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_es.ts) | not yet: shown in English |
| Română | [`printview3d_ro.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_ro.ts) | not yet: shown in English |
| Français | [`printview3d_fr.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_fr.ts) | not yet: shown in English |
| Nederlands | [`printview3d_nl.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_nl.ts) | [`CHANGELOG.nl.md`](https://github.com/sevagjb/PrintView3D/blob/main/CHANGELOG.nl.md) |

> **Translating means both parts.** Every release adds new program texts *and* a new section at the
> top of `CHANGELOG.md`. When you update your language, translate the new texts in your `.ts` file
> **and** the newest section(s) of the changelog, so people using your language see what's new in
> their own language too.

## Fix a word or a sentence (in the browser, about 5 minutes)

1. Open the file for your language from the table above.
2. Click the **pencil icon** (*Edit this file*). GitHub makes a copy for you (a *fork*) if needed.
3. Press `Ctrl+F` and search for the English text you saw in the program. Each text looks like this:

   ```xml
   <message>
       <source>Show only this layer</source>
       <translation type="unfinished">Nur diese Schicht anzeigen</translation>
   </message>
   ```

   Change only the text between `<translation…>` and `</translation>`. Leave `<source>` as it is.
4. If the translation is now correct, also remove ` type="unfinished"` (see below).
5. Click **Commit changes…**, write a short note (for example *German: better word for "layer"*)
   and click **Propose changes**, then **Create pull request**.

That's it. You can fix many texts in one pull request.

## Rules that keep the program working

- **`{placeholders}`** such as `{slicer}`, `{n}` or `{version}` are filled in by the program. Keep
  them exactly as written (you may move them inside the sentence).
- **Tags** such as `<b>…</b>` stay. In the file they appear as `&lt;b&gt;…&lt;/b&gt;`; leave
  those as they are too.
- **`&amp;&amp;`** shows a single `&` on a button. Keep it, or use a word instead.
- **Notes for translators** (`<extracomment>`) explain texts that are unclear on their own, for
  example that *Right* means the right-side view, not *correct*.
- The tests check placeholders and tags on every pull request, so a mistake is caught before it
  reaches anyone.

## "unfinished" means: still needs a native speaker

`type="unfinished"` marks a translation that nobody has checked yet. When you have checked a text
and it is correct, remove ` type="unfinished"` from that line. That's how the README table knows
which languages are reviewed.

## Bigger work: Qt Linguist

For a whole language, a desktop editor is more comfortable. **Qt Linguist** comes with PySide6
(`pip install PySide6-Essentials`, then run `pyside6-linguist`). Open the `.ts` file, translate, mark each
finished text with ✓, save, and open a pull request with the file. Any text editor works too.

## What's new: translating the changelog

[`CHANGELOG.md`](https://github.com/sevagjb/PrintView3D/blob/main/CHANGELOG.md) is the English original. Its translation for your language is
`CHANGELOG.<code>.md` next to it, for example `CHANGELOG.ar.md` (Arabic) or `CHANGELOG.nl.md` (Dutch).

**Keeping it up to date (each release):** open `CHANGELOG.md`, copy the newest section (from its
`## 0.23.0` line down to the next `##` line) to the top of your language's file, below the title,
and translate the text under the heading. Then open a pull request, as above.

**Starting it for your language:** create `CHANGELOG.<code>.md` (the same code as your `.ts` file)
with a title and the newest version's section. You don't have to translate the whole history:
versions that aren't in your file are shown in English, with a short note.

Rules that keep it working:

- **Keep every `## 0.23.0` heading exactly as it is** (you may translate words after the number,
  such as *first version*). The program finds each version by its number; a typo such as `## 0.10`
  for `0.1.0` makes it a different version, and the tests stop the pull request.
- **Same order as `CHANGELOG.md`**, newest first, and only versions that `CHANGELOG.md` has.
- Keep **file names, keys and code** such as `` `Ctrl+T` ``, `` `.stl` `` or `--theme` as they are, and the
  **links** `(README.md#themes)`: the program turns them into full links.
- Names of buttons and settings: use the words your language's `.ts` file uses in the program, so
  the notes match what people see.

`python tools/i18n.py stats` shows for each language which versions its changelog is missing.

## A new language

Open an [issue](https://github.com/sevagjb/PrintView3D/issues) saying which language you'd like to translate, or do it yourself:

```
python tools/i18n.py new it          # creates translations/printview3d_it.ts
```

Translate it, add the language to `LANGUAGES` in `src/printview3d/i18n.py`, and open a pull
request. Partly translated is fine: texts not translated yet simply show in English. If you can,
also start `CHANGELOG.<code>.md` with the newest version (see *What's new* above).

## For developers

When the code gets new or changed texts, `python tools/i18n.py update` adds them to every language
file as `unfinished`. The tests fail if this was forgotten.

For a release, write the new section in `CHANGELOG.md` and add it to the translated changelogs
that are kept complete (Arabic and Dutch). `python tools/i18n.py check` (run by the tests) fails
on a translated changelog with a version heading `CHANGELOG.md` doesn't have; `stats` lists the
versions each one is missing. The build bundles every `CHANGELOG*.md`. Details:
[CONTRIBUTING.md → Translations](https://github.com/sevagjb/PrintView3D/blob/main/CONTRIBUTING.md#translations).

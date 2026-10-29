# Translating PrintView3D on GitHub

All translations live in this repository, in the [`translations/`](https://github.com/sevagjb/PrintView3D/tree/main/translations) folder, one file
per language. You change a file and send the change as a pull request; it is reviewed and merged
into the next release. No other website or account is needed, only a free GitHub account.

| Language | File |
|---|---|
| العربية Arabic | [`printview3d_ar.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_ar.ts) |
| Deutsch | [`printview3d_de.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_de.ts) |
| Español | [`printview3d_es.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_es.ts) |
| Français | [`printview3d_fr.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_fr.ts) |
| Nederlands | [`printview3d_nl.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_nl.ts) |
| Română | [`printview3d_ro.ts`](https://github.com/sevagjb/PrintView3D/blob/main/translations/printview3d_ro.ts) |

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
(`pip install PySide6`, then run `pyside6-linguist`). Open the `.ts` file, translate, mark each
finished text with ✓, save, and open a pull request with the file. Any text editor works too.

## A new language

Open an [issue](https://github.com/sevagjb/PrintView3D/issues) saying which language you'd like to translate, or do it yourself:

```
python tools/i18n.py new it          # creates translations/printview3d_it.ts
```

Translate it, add the language to `LANGUAGES` in `src/printview3d/i18n.py`, and open a pull
request. Partly translated is fine: texts not translated yet simply show in English.

## For developers

When the code gets new or changed texts, `python tools/i18n.py update` adds them to every language
file as `unfinished`. The tests fail if this was forgotten. Details:
[CONTRIBUTING.md → Translations](https://github.com/sevagjb/PrintView3D/blob/main/CONTRIBUTING.md#translations).

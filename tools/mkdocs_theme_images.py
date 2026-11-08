"""MkDocs hook: pictures that match the website's theme.

The app's screenshots are made in Dark (docs/screenshot-*.png, also used by the README on GitHub)
and, for the website, in Light and Ember too: name--light.webp and name--ember.webp next to them
(tools/make_screenshots.py --theme, tools/make_clips.py --theme). For every picture on a page that
has both, this hook adds the two versions beside it; docs/assets/extra.css shows only the one that
matches the theme chosen in the header (Light, Dark or Ember). Pictures without them stay as they are.

    mkdocs.yml:  hooks: [tools/mkdocs_theme_images.py]
"""

from __future__ import annotations

import os
import posixpath
import re

IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
SRC = re.compile(r'\bsrc="([^"]+)"', re.IGNORECASE)
THEMES = ("light", "ember")


def variant_name(name: str, theme: str) -> str:
    """screenshot-model.png -> screenshot-model--light.webp; check.ar.png -> check-ar--light.webp."""
    stem = os.path.splitext(name)[0].replace(".", "-")
    return f"{stem}--{theme}.webp"


def _docs_file(docs_dir: str, page_url: str, src: str, languages: set[str]) -> str | None:
    """The file in docs/ that an img src on a page points to (None for links elsewhere). On an
    Arabic or Dutch page the language plugin has renamed check.ar.png to ar/.../check.png: then
    this is the language's own file (assets/inside/check.ar.png)."""
    if "://" in src or src.startswith(("data:", "/", "#")):
        return None
    path = posixpath.normpath(posixpath.join(posixpath.dirname(page_url), src.split("#")[0]))
    parts = path.split("/")
    lang = ""
    if parts and parts[0] in languages:           # ar/..., nl/...: a picture in that language
        lang, parts = parts[0], parts[1:]
    if lang:
        stem, ext = os.path.splitext(parts[-1])
        localized = parts[:-1] + [f"{stem}.{lang}{ext}"]
        if os.path.isfile(os.path.join(docs_dir, *localized)):
            return "/".join(localized)
    full = os.path.join(docs_dir, *parts)
    return "/".join(parts) if os.path.isfile(full) else None


def _with_class(tag: str, cls: str) -> str:
    if re.search(r'\bclass="', tag):
        return re.sub(r'\bclass="', f'class="{cls} ', tag, count=1)
    return tag[:-1].rstrip("/").rstrip() + f' class="{cls}">'


def on_page_content(html, page, config, files, **kwargs):
    docs_dir = config["docs_dir"]
    languages = set()
    for plugin in config["plugins"].values():          # mkdocs-static-i18n's other languages
        for lang in getattr(getattr(plugin, "config", None), "languages", None) or []:
            loc = getattr(lang, "locale", None)
            if loc:
                languages.add(loc)

    def swap(m):
        tag = m.group(0)
        s = SRC.search(tag)
        if not s or "pv-theme-" in tag:
            return tag
        src = s.group(1)
        rel = _docs_file(docs_dir, page.url, src, languages)
        if rel is None:
            return tag
        folder, name = posixpath.split(rel)
        variants = {t: posixpath.join(folder, variant_name(name, t)) for t in THEMES}
        if not all(os.path.isfile(os.path.join(docs_dir, *v.split("/"))) for v in variants.values()):
            return tag
        # The theme versions are no language's own file, so they sit at the site's root: link
        # them from this page's folder (ar/use.html -> ../assets/inside/check-ar--light.webp).
        here = posixpath.dirname(page.url) or "."
        out = [_with_class(tag, "pv-theme-dark")]
        for t in THEMES:
            vsrc = posixpath.relpath(variants[t], here)
            v = tag.replace(f'src="{src}"', f'src="{vsrc}"', 1)
            v = re.sub(r'\bloading="[^"]*"', "", v)
            out.append(_with_class(v.replace("<img", '<img loading="lazy"', 1), f"pv-theme-{t}"))
        return "".join(out)

    return IMG.sub(swap, html)

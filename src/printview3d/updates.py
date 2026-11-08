"""Checking GitHub for a newer PrintView3D, and installing it on Windows.

What is contacted, and when (also explained in the README, "Updates and privacy"):
  * https://api.github.com/repos/sevagjb/PrintView3D/releases/latest
    only when the user clicks "Check for updates now", or at most once a day if
    the user switched on "Check automatically". The request contains nothing
    about the user or their files; like every web request, GitHub sees the IP
    address.
  * the release download (github.com), only after the user clicks
    "Install update" (Windows installer) - otherwise the release page opens in
    the browser.

No Qt in here: the UI runs these functions in a worker thread.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass
from typing import Callable, Optional

from . import __version__

REPO = "sevagjb/PrintView3D"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
PRIVACY_URL = f"https://github.com/{REPO}#updates-and-privacy"
PROJECT_URL = f"https://github.com/{REPO}"
TRANSLATING_URL = f"https://github.com/{REPO}/blob/main/docs/TRANSLATING.md"
CHANGELOG_URL = f"https://github.com/{REPO}/blob/main/CHANGELOG.md"
MAX_NOTES_SHOWN = 5                 # "What's new" after an update: at most this many versions
SETUP_ASSET = "PrintView3D-Setup.exe"
CHECK_INTERVAL = 24 * 3600          # automatic check: at most once a day
TIMEOUT = 15


class UpdateError(RuntimeError):
    pass


@dataclass
class Release:
    version: str                     # "0.10.0"
    notes: str = ""                  # release notes (Markdown)
    page_url: str = RELEASES_PAGE
    setup_url: str = ""              # PrintView3D-Setup.exe download
    setup_sha256: str = ""
    setup_size: int = 0
    published: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Optional["Release"]:
        if not isinstance(d, dict) or not d.get("version"):
            return None
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**known)


# ---------------------------------------------------------------- versions
def parse_version(text: str) -> tuple[int, ...]:
    """'v0.10.0' -> (0, 10, 0). Anything after the numbers is ignored."""
    m = re.match(r"\s*v?(\d+(?:\.\d+)*)", text or "")
    if not m:
        return ()
    return tuple(int(x) for x in m.group(1).split("."))


def is_newer(remote: str, local: str = __version__) -> bool:
    r, l_ = parse_version(remote), parse_version(local)
    n = max(len(r), len(l_))
    return bool(r) and r + (0,) * (n - len(r)) > l_ + (0,) * (n - len(l_))


# ------------------------------------------------------------------ "What's new"
# CHANGELOG.md is the English original. A translation is CHANGELOG.<code>.md (CHANGELOG.ar.md,
# CHANGELOG.nl.md, ...): the same "## 0.22.0" headings, translated text under them. A version a
# translation doesn't have (yet) is shown in English, so a missing translation never blocks a
# release and the window is never empty.

def changelog_file(lang: str = "en") -> str:
    """The changelog's file name for a language: CHANGELOG.md, or CHANGELOG.<lang>.md."""
    return "CHANGELOG.md" if lang in ("", "en") else f"CHANGELOG.{lang}.md"


def _changelog_path(lang: str = "en") -> str:
    """Where the changelog for `lang` is: bundled with the program (resources/), or in the source
    checkout. "" if there is none for that language."""
    here = os.path.dirname(os.path.abspath(__file__))
    name = changelog_file(lang)
    for path in (os.path.join(here, "resources", name), os.path.join(here, "..", "..", name)):
        if os.path.isfile(path):
            return path
    return ""


def changelog_text(lang: str = "en") -> str:
    """The changelog in `lang` ("" if there is no file for it)."""
    path = _changelog_path(lang)
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def changelog_url(lang: str = "en") -> str:
    """The changelog on GitHub: in `lang` when it has been translated, otherwise English."""
    if lang not in ("", "en") and _changelog_path(lang):
        return f"https://github.com/{REPO}/blob/main/{changelog_file(lang)}"
    return CHANGELOG_URL


def changelog_sections(text: str) -> list[tuple[str, str]]:
    """[(version, notes), ...] from the "## 0.18.0" headings, in file order (newest first)."""
    parts = re.split(r"^## +(\S+)[^\n]*\n", text, flags=re.M)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def _absolute_links(md: str) -> str:
    """Links like (docs/TRANSLATING.md) point into the repository; outside GitHub they need the full URL."""
    return re.sub(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)",
                  lambda m: f"](https://github.com/{REPO}/blob/main/{m.group(1)})", md)


@dataclass
class Notes:
    """One version's notes as shown: in the user's language, or in English when that version
    hasn't been translated (translated=False)."""
    version: str
    text: str
    translated: bool


def whats_new(lang: str = "en", older: str | None = None, current: str = __version__,
              en_text: str | None = None, lang_text: str | None = None) -> list[Notes]:
    """The notes for "What's new", newest first, in `lang` with English per version as fallback.

    older=None: only the `current` version (the "What's new" menu item). Otherwise every version
    newer than `older` up to `current` (the window shown once after an update)."""
    en_text = changelog_text() if en_text is None else en_text
    if older is None:
        wanted = [(v, n) for v, n in changelog_sections(en_text) if v == current]
    else:
        wanted = [(v, n) for v, n in changelog_sections(en_text)
                  if is_newer(v, older) and not is_newer(v, current)]
    local: dict[str, str] = {}
    if lang not in ("", "en"):
        local = dict(changelog_sections(changelog_text(lang) if lang_text is None else lang_text))
    out = []
    for version, english in wanted:
        text = local.get(version, "").strip()
        out.append(Notes(version, _absolute_links(text or english), bool(text) or lang in ("", "en")))
    return out


def just_updated(settings, current: str = __version__) -> str:
    """The version used before this start if PrintView3D was updated since, else "".

    Records this version either way. Works however the update was made (one-click installer,
    winget, a downloaded zip or AppImage). A new install has no previous version: nothing to show.
    """
    last = settings.get("last_run_version", "")
    if last != current:
        settings.set("last_run_version", current)
    return last if last and is_newer(current, last) else ""


# ------------------------------------------------------------------ GitHub
def parse_release(data: dict) -> Optional[Release]:
    """A release from GitHub's JSON, or None for drafts and test versions."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    version = ".".join(str(x) for x in parse_version(data.get("tag_name", "")))
    if not version:
        return None
    rel = Release(version=version, notes=data.get("body") or "",
                  page_url=data.get("html_url") or RELEASES_PAGE,
                  published=data.get("published_at") or "")
    for a in data.get("assets") or []:
        if a.get("name") == SETUP_ASSET:
            rel.setup_url = a.get("browser_download_url", "")
            rel.setup_size = int(a.get("size") or 0)
            digest = a.get("digest") or ""
            if digest.startswith("sha256:"):
                rel.setup_sha256 = digest.split(":", 1)[1].lower()
    return rel


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:                 # the packaged app may not find the system's certificates (Linux)
        import certifi
        ctx.load_verify_locations(certifi.where())
    except (ImportError, OSError, ssl.SSLError):
        pass
    return ctx


def _request(url: str, accept: str = "application/vnd.github+json"):
    req = urllib.request.Request(url, headers={
        "Accept": accept,
        "User-Agent": f"PrintView3D/{__version__}",     # GitHub requires a User-Agent
        "X-GitHub-Api-Version": "2022-11-28",
    })
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_ssl_context()), _GitHubOnly())
    return opener.open(req, timeout=TIMEOUT)


def fetch_latest() -> Release:
    """Ask GitHub for the newest release. Raises UpdateError when offline etc."""
    try:
        with _request(API_LATEST) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 - network, TLS, JSON: all mean "could not check"
        raise UpdateError(f"Could not reach GitHub ({type(e).__name__})") from None
    rel = parse_release(data)
    if rel is None:
        raise UpdateError("GitHub did not return a release")
    return rel


# ---------------------------------------------------- settings / schedule
def auto_check_enabled(settings) -> bool:
    return settings.get("update_check") is True


def check_is_due(settings, now: Optional[float] = None) -> bool:
    now = time.time() if now is None else now
    last = float(settings.get("update_last_check") or 0)
    return auto_check_enabled(settings) and (now - last >= CHECK_INTERVAL or now < last)


def remember(settings, rel: Optional[Release], now: Optional[float] = None) -> None:
    """After a check: rel is the latest release, or None when the check failed."""
    now = time.time() if now is None else now
    settings.set("update_last_check", now)
    if rel is not None:
        settings.set("update_latest", rel.to_dict())
        settings.set("update_last_ok", now)          # the last check that really reached GitHub


UP_TO_DATE_FOR = 14 * 24 * 3600     # how long a successful check counts as "up to date"


def up_to_date(settings, now: Optional[float] = None) -> bool:
    """True when a recent check that reached GitHub found nothing newer than this version
    (the green dot). False when there is an update, when it was skipped, or when nobody
    checked in the last two weeks: then PrintView3D simply doesn't know."""
    now = time.time() if now is None else now
    ok = float(settings.get("update_last_ok") or 0)
    rel = Release.from_dict(settings.get("update_latest") or {})
    if rel is None or not ok or now - ok > UP_TO_DATE_FOR or now < ok:
        return False
    return not is_newer(rel.version)


def available(settings) -> Optional[Release]:
    """The newer release found by the last check (unless the user skipped it)."""
    rel = Release.from_dict(settings.get("update_latest") or {})
    if rel is None or not is_newer(rel.version):
        return None
    if settings.get("update_skip") == rel.version:
        return None
    return rel


# ---------------------------------------------------------------- install
def install_kind() -> str:
    """'installer': installed with Setup.exe on Windows -> one-click update.
    'page': Linux AppImage, portable zip, running from source -> open the release page."""
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        if os.path.isfile(os.path.join(os.path.dirname(sys.executable), "unins000.exe")):
            return "installer"
    return "page"


# Where GitHub serves release files: the download link, and the storage it redirects to.
TRUSTED_HOSTS = ("github.com", "api.github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")


def trusted_download(url: str) -> bool:
    """True for an https link to this project's releases on GitHub."""
    from urllib.parse import urlsplit
    u = urlsplit(url or "")
    return (u.scheme == "https" and u.hostname == "github.com"
            and u.path.startswith(f"/{REPO}/releases/download/"))


class _GitHubOnly(urllib.request.HTTPRedirectHandler):
    """Follow a download's redirects only to GitHub's own servers, and only over https."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from urllib.parse import urlsplit
        u = urlsplit(newurl)
        if u.scheme != "https" or u.hostname not in TRUSTED_HOSTS:
            raise UpdateError("The download was redirected away from GitHub")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "PrintView3D", "cache", "update")


def download_installer(rel: Release, progress: Optional[Callable[[float], None]] = None,
                       cancelled: Callable[[], bool] = lambda: False) -> str:
    """Download Setup.exe and check its SHA-256 fingerprint. Returns the file path."""
    if not rel.setup_url:
        raise UpdateError("This release has no Windows installer")
    if not trusted_download(rel.setup_url):
        raise UpdateError("The installer is not on GitHub, so it was not downloaded")
    if not re.fullmatch(r"[0-9a-f]{64}", rel.setup_sha256 or ""):
        # Without GitHub's fingerprint a damaged or replaced download could not be noticed.
        raise UpdateError("GitHub did not give the installer's fingerprint, so it was not downloaded")
    os.makedirs(download_dir(), exist_ok=True)
    path = os.path.join(download_dir(), f"PrintView3D-Setup-{rel.version}.exe")
    part = path + ".part"
    h = hashlib.sha256()
    try:
        with _request(rel.setup_url, accept="application/octet-stream") as r, open(part, "wb") as f:
            total = int(r.headers.get("Content-Length") or rel.setup_size or 0)
            done = 0
            while True:
                if cancelled():
                    raise UpdateError("cancelled")
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done / total)
    except UpdateError:
        _remove(part)
        raise
    except Exception as e:  # noqa: BLE001
        _remove(part)
        raise UpdateError(f"Download failed ({type(e).__name__})") from None
    if h.hexdigest() != rel.setup_sha256:
        _remove(part)
        raise UpdateError("The download is damaged (fingerprint does not match). Please try again.")
    os.replace(part, path)
    return path


def run_installer(path: str) -> None:
    """Start the installer for an update: it shows its progress, needs no clicks,
    closes PrintView3D, keeps the settings and starts the new version."""
    subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/UPDATE=1"],
                     close_fds=True)


def _remove(p: str) -> None:
    try:
        os.remove(p)
    except OSError:
        pass


__all__ = ["Release", "UpdateError", "available", "auto_check_enabled", "check_is_due",
           "download_installer", "fetch_latest", "install_kind", "is_newer", "parse_release",
           "parse_version", "remember", "run_installer"]

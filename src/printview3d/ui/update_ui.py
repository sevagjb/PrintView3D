"""Update check in the background, "What's new", and one-click install (Windows)."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QLabel, QMessageBox, QProgressDialog, QTextBrowser,
    QVBoxLayout,
)

from .. import __version__
from .. import updates as up
from ..i18n import RIGHT_TO_LEFT, current_language, tr


class UpdateChecker(QObject):
    """Runs updates.fetch_latest() in a thread; `finished` gets (Release or None, error text)."""

    finished = Signal(object, str)
    _done = Signal(object, str)          # from the worker thread

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.running = False
        self._done.connect(self._on_done, Qt.QueuedConnection)

    def start(self):
        if self.running:
            return
        self.running = True

        def work():
            try:
                rel, err = up.fetch_latest(), ""
            except up.UpdateError as e:
                rel, err = None, str(e)
            self._done.emit(rel, err)

        threading.Thread(target=work, daemon=True).start()

    def _on_done(self, rel, err):
        self.running = False
        up.remember(self.settings, rel)
        self.finished.emit(rel, err)


def make_checker(settings, parent) -> UpdateChecker:
    return UpdateChecker(settings, parent)


def show_whats_new(parent, rel: up.Release):
    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("What's new in {version}").format(version=rel.version))
    v = QVBoxLayout(dlg)
    head = QLabel(tr("PrintView3D {new} is available. You have {current}.").format(
        new=f"<b>{rel.version}</b>", current=__version__))
    v.addWidget(head)
    text = QTextBrowser()
    text.setOpenExternalLinks(True)
    text.setMarkdown(rel.notes or tr("No release notes."))
    v.addWidget(text, 1)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    bb.rejected.connect(dlg.reject)
    v.addWidget(bb)
    dlg.resize(620, 520)
    dlg.exec()


def _notes_markdown(notes: list[up.Notes], lang: str) -> str:
    """The notes as Markdown. Versions shown in English because they aren't translated yet get a
    short note: once at the top when none is translated, otherwise at each of them."""
    untranslated = [n for n in notes if not n.translated]
    note = "*" + tr("Not translated yet, shown in English.") + "*"
    every = bool(untranslated) and len(untranslated) == len(notes)
    parts = [note] if every else []
    for n in notes:
        parts.append(f"## {n.version}")
        if not n.translated and not every:
            parts.append(note)
        parts.append(n.text)
    return "\n\n".join(parts)


def _notes_window(parent, title: str, head: str, notes: list[up.Notes], lang: str) -> None:
    """The "What's new" window: an optional line on top, the notes, and at the bottom a button to
    every change on GitHub (in this language when the changelog is translated) and Close."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    v = QVBoxLayout(dlg)
    if head:
        v.addWidget(QLabel(head))
    text = QTextBrowser()
    text.setOpenExternalLinks(True)
    if lang in RIGHT_TO_LEFT:
        # Whole document right-to-left, so also a heading that is only a version number ("## 0.22.0")
        # sits on the right instead of following its digits to the left.
        opt = text.document().defaultTextOption()
        opt.setTextDirection(Qt.RightToLeft)
        text.document().setDefaultTextOption(opt)
    text.setMarkdown(_notes_markdown(notes, lang) if notes else
                     tr("The notes for this version are not included in this build."))
    v.addWidget(text, 1)
    bb = QDialogButtonBox(QDialogButtonBox.Close)          # Qt translates Close itself
    all_btn = bb.addButton(tr("All changes on GitHub"), QDialogButtonBox.ActionRole)
    all_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(up.changelog_url(lang))))
    bb.rejected.connect(dlg.reject)
    v.addWidget(bb)
    dlg.resize(620, 520)
    dlg._notes = notes              # for the tests
    dlg.exec()


def show_updated(parent, previous: str) -> None:
    """Once after an update: what changed since `previous`, from the bundled changelog."""
    lang = current_language()
    notes = up.whats_new(lang, older=previous)
    if not notes:
        return
    _notes_window(parent, tr("What's new in {version}").format(version=__version__),
                  tr("PrintView3D was updated to {version}.").format(version=f"<b>{__version__}</b>"),
                  notes[: up.MAX_NOTES_SHOWN], lang)


def show_current(parent) -> None:
    """The "What's new" menu item: this version's notes, any time."""
    lang = current_language()
    _notes_window(parent, tr("What's new in {version}").format(version=__version__), "",
                  up.whats_new(lang), lang)


class _Download(QObject):
    progress = Signal(float)
    done = Signal(str, str)          # path, error


def install(parent, rel: up.Release) -> None:
    """Windows installed version: download, check, install, restart. Otherwise: the release page."""
    if up.install_kind() != "installer" or not rel.setup_url:
        QDesktopServices.openUrl(QUrl(rel.page_url))
        return
    dlg = QProgressDialog(tr("Downloading PrintView3D {version}…").format(version=rel.version),
                          tr("Cancel"), 0, 100, parent)
    dlg.setWindowTitle(tr("Updating PrintView3D"))
    dlg.setWindowModality(Qt.WindowModal)
    dlg.setMinimumDuration(0)
    dlg.setAutoClose(False)
    dlg.setValue(0)
    sig = _Download()
    sig.progress.connect(lambda f: dlg.setValue(int(f * 100)), Qt.QueuedConnection)
    cancelled = {"v": False}
    dlg.canceled.connect(lambda: cancelled.update(v=True))

    def finished(path, err):
        dlg.close()
        if err:
            if err != "cancelled":
                QMessageBox.warning(parent, tr("Update failed"),
                                    tr("The update could not be downloaded: {error}").format(error=err))
            return
        try:
            up.run_installer(path)
        except OSError as e:
            QMessageBox.warning(parent, tr("Update failed"), str(e))
            return
        QApplication.instance().quit()     # the installer replaces the program and starts it again

    sig.done.connect(finished, Qt.QueuedConnection)

    def work():
        try:
            sig.done.emit(up.download_installer(rel, sig.progress.emit, lambda: cancelled["v"]), "")
        except up.UpdateError as e:
            sig.done.emit("", str(e))

    threading.Thread(target=work, daemon=True).start()
    dlg.exec()


def install_button_text() -> str:
    return tr("Install update") if up.install_kind() == "installer" else tr("Download update")

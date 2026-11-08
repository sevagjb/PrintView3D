"""Settings -> Toolbar: which toolbar buttons are shown and how the view buttons look.

The toolbar's order never changes: hiding a button only takes it out, the rest keep their places
(Plate always first of the view buttons, Fit always last). The menu, Open in slicer, Export STL,
Plate and Fit are always shown; everything stays in the menu and keeps its key while hidden.
"""

from __future__ import annotations

# Every toolbar button, left to right: (id, can be hidden).
BUTTONS: tuple[tuple[str, bool], ...] = (
    ("menu", False), ("home", True), ("open", True), ("slicer", False), ("export", False),
    ("plate", False), ("check", True), ("view", True), ("measure", True), ("fit", False),
    ("screenshot", True), ("theme", True), ("settings", True),
)
HIDEABLE: tuple[str, ...] = tuple(b for b, can in BUTTONS if can)

# The view buttons with an icon (Plate ... Fit), as they are labelled.
VIEW_BUTTONS: tuple[str, ...] = ("plate", "check", "view", "measure", "fit")
# How those buttons are labelled: "Plate (P)", "Plate", "P" or the icon alone.
LABEL_STYLES: tuple[str, ...] = ("full", "name", "key", "icon")


def hidden(settings) -> set[str]:
    """The buttons the user switched off (unknown names and always-shown buttons ignored)."""
    value = settings.get("toolbar_hidden", []) or []
    if not isinstance(value, (list, tuple)):
        return set()
    return {b for b in value if b in HIDEABLE}


def label_style(settings) -> str:
    value = settings.get("toolbar_labels", "full")
    return value if value in LABEL_STYLES else "full"


def joined(settings) -> bool:
    return bool(settings.get("toolbar_joined", False))


def save(settings, hide: set[str], labels: str, join: bool) -> None:
    """Store the choice; hidden buttons in toolbar order, so the file reads naturally."""
    settings.set("toolbar_hidden", [b for b in HIDEABLE if b in hide])
    settings.set("toolbar_labels", labels if labels in LABEL_STYLES else "full")
    settings.set("toolbar_joined", bool(join))


def button_label(style: str, name: str, with_key: str, key: str) -> str:
    """The text on a view button: with_key is 'Plate (P)', key is 'P' ('' when it has none)."""
    if style == "name" or style == "icon":
        return name
    if style == "key":
        return key or name                      # a button without a key keeps its name
    return with_key


def join_positions(visible: list[str]) -> dict[str, str]:
    """Where each visible button sits in the joined group: 'first', 'middle', 'last' or 'only'."""
    if len(visible) == 1:
        return {visible[0]: "only"}
    out = {b: "middle" for b in visible}
    if visible:
        out[visible[0]] = "first"
        out[visible[-1]] = "last"
    return out

"""Translatable names for fixed values that come from non-UI code.

The loaders and helper modules work with plain English keys (they must not
depend on Qt). The UI shows them through these tables: tr(FEATURE_LABELS[key]).
"""

from ..i18n import localize_number_text, tr, tr_noop

# G-code feature types (keys from loaders.gcode.FEATURES)
FEATURE_LABELS = {
    "outer_wall": tr_noop("Outer wall"),
    "inner_wall": tr_noop("Inner wall"),
    "overhang": tr_noop("Overhang wall"),
    "infill": tr_noop("Sparse infill"),
    "solid_infill": tr_noop("Solid infill"),
    "top_bottom": tr_noop("Top / bottom"),
    "bridge": tr_noop("Bridge"),
    "gap_fill": tr_noop("Gap fill"),
    "ironing": tr_noop("Ironing"),
    "support": tr_noop("Support"),
    "support_interface": tr_noop("Support interface"),
    "skirt_brim": tr_noop("Skirt / brim"),
    "prime_tower": tr_noop("Prime tower"),
    "other": tr_noop("Other / custom"),
    "travel": tr_noop("Travel moves"),
}

# Plate menu and Settings -> Viewer (keys from ui.scene.PLATE_MODES)
PLATE_MODE_LABELS = {
    "printer": tr_noop("Printer's plate (from the file)"),
    "fit": tr_noop("Grow to fit the model"),
    "custom": tr_noop("Custom size…"),
    "infinite": tr_noop("Infinite grid"),
}

# Detail names read from files (keys used by the loaders' meta dictionaries)
META_LABELS = {
    "Print time": tr_noop("Print time"),
    "Filament (g)": tr_noop("Filament (g)"),
    "Filament (mm)": tr_noop("Filament (mm)"),
    "Filament type": tr_noop("Filament type"),
    "Filament profile": tr_noop("Filament profile"),
    "Layer height": tr_noop("Layer height"),
    "Nozzle": tr_noop("Nozzle"),
    "Printer": tr_noop("Printer"),
    "Printer profile": tr_noop("Printer profile"),
    "Process profile": tr_noop("Process profile"),
    "Slicer": tr_noop("Slicer"),
    "Created with": tr_noop("Created with"),
    "Title": tr_noop("Title"),
    "Designer": tr_noop("Designer"),
    "Description": tr_noop("Description"),
    "Format": tr_noop("Format"),
    "Organization": tr_noop("Organization"),
    "Date": tr_noop("Date"),
}

# File-association status texts (from file_assoc.status())
ASSOC_STATUS = {
    "Default app": tr_noop("Default app"),
    'In "Open with" (not default)': tr_noop('In "Open with" (not default)'),
    'In "Open With" (not default)': tr_noop('In "Open with" (not default)'),
    "Not registered": tr_noop("Not registered"),
    "Not available on this system": tr_noop("Not available on this system"),
}

# Text that values like "(calculated)" carry inside a value read from a file
VALUE_WORDS = {
    "(calculated)": tr_noop("(calculated)"),
}


def feature_label(key: str) -> str:
    return tr(FEATURE_LABELS.get(key, key))


def plate_mode_label(key: str) -> str:
    return tr(PLATE_MODE_LABELS.get(key, key))


def meta_label(key: str) -> str:
    return tr(META_LABELS.get(key, key))


def meta_value(value: str) -> str:
    value = localize_number_text(value)
    for word, src in VALUE_WORDS.items():
        if word in value:
            value = value.replace(word, tr(src))
    return value


def assoc_status(text: str) -> str:
    return tr(ASSOC_STATUS.get(text, text))

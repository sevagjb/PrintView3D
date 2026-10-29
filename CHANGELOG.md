# Changelog

## 0.21.2
- **The first start shows PrintView3D itself**, with no questions on top of it. *Check for updates?*
  is asked on the second start and the GitHub star message comes on the third, once. Nothing changes
  for people updating from an older version.
- **Linux: light theme when the desktop has no dark setting.** With *Automatic* (the default for new
  installs), PrintView3D now also reads the GNOME, GTK and KDE settings when Qt can't tell; if none
  of them says dark, it starts light. Windows and macOS are unchanged.
- **Linux: the AppImage can update itself** with [AppImageUpdate](https://github.com/AppImageCommunity/AppImageUpdate)
  and similar tools: it carries update information, and every release has a
  `PrintView3D-x86_64.AppImage.zsync` next to the AppImage, so only the changed parts are downloaded.

## 0.21.1
- **New language: Română (Romanian)**, choose it in **Settings → Language**. Translated and reviewed
  by a native speaker. Thanks to [@munteancd](https://github.com/munteancd)!

## 0.21.0
- **Home button**: the house icon next to *Open* (also in the menu, `Ctrl+W`) closes the file and
  goes back to the start page with your recent files. The memory the file used is given back.
- **New themes: Ember Light and Ember Dark**, in cream, orange and teal.
- **Choose a theme by picture**: **Settings → Appearance** shows a card with a small picture of
  PrintView3D in every theme. Click one to see it right away; *OK* keeps it, *Cancel* goes back.
  The theme menu in the toolbar shows a colour next to each theme, and `Ctrl+T` goes through all six.
  [Details](README.md#themes).

## 0.20.0
- **Export STL from FreeCAD and STEP files**: once FreeCAD has shown the file in 3D, **Export STL**
  (`Ctrl+E`) saves its solids as plain STL files, like it does for 3MF projects: all in one file,
  or one file per solid.
- **The Export STL button has an arrow** (like *Open in slicer*) with every way at once:
  *All objects as one STL*, *One STL per object* and *Choose objects…*.
  [Details](README.md#export-stl-from-3mf).
- **Choose what a click does** in **Settings → Files → Export STL**: show the list of objects
  (as before), save everything as one STL, or save one STL per object. `Ctrl+E` does the same.
- **macOS**: pressing **OK** in Settings saved nothing and showed an error; fixed.

## 0.19.2
- **macOS for Intel Macs** (beta): `PrintView3D-macOS-Intel.dmg`, next to the Apple silicon version.
  Both need **macOS 14.4 (Sonoma) or newer**; the build now checks this for every file in the app,
  and starts the app on a real macOS 14 Mac
  (earlier notes said macOS 12, which the current Qt version no longer supports).
- **Dutch** translation fully reviewed.
- **Website** in Dutch too: [sevagjb.github.io/PrintView3D](https://sevagjb.github.io/PrintView3D/nl/).
- Uses Qt for Python (PySide6) 6.12 again; 0.19.1 was built with the older 6.9 by mistake.

## 0.19.1
Safety update. Thanks to a review of how PrintView3D handles files from the internet:
- **glTF files** can no longer make PrintView3D read files outside the model's own folder. A
  crafted file could name any file on the computer, or on Windows a network share, which would
  make Windows contact a stranger's server just by opening the file.
- **Updates** are only installed when GitHub gives the installer's SHA-256 fingerprint and it
  matches, and the installer is only downloaded from this project's releases on GitHub.
- **3MF and FreeCAD files** get the same protection as ZIP files: a part that would unpack to far
  more data than a 3D file needs is refused, instead of filling the memory.
- **ZIP files**: names that Windows can't use (with `:`, `CON`, …) are made safe when unpacking,
  and a half-unpacked file is removed when unpacking fails.
- **File Explorer thumbnails**: STL files with absurd coordinates, or millions of huge triangles,
  can no longer keep Explorer busy.
- **Linux**: the menu entry also works when the program's folder has `$`, `%` or `\` in its name.
- New: [SECURITY.md](SECURITY.md) explains how to report a security problem privately.

## 0.19.0
- **Open ZIP files**: open a downloaded model package (Printables, Thingiverse, …) like any other
  file, without unpacking it first. Only the 3D files are used (STL, 3MF, OBJ, PLY, OFF, glTF,
  STEP, FreeCAD and G-code); pictures, documents, links and other files are skipped. A ZIP with one
  3D file opens just like that file. [Details](README.md#zip-files).
- **The files in a ZIP** are listed in the side panel with a coloured label for their type and a
  short explanation of each type. Click a file, or use **↑ / ↓**, to switch.
- **Show all side by side** places the models of a ZIP next to each other: up to three in one row,
  then a grid (four as 2 × 2, six as 3 × 2, …), spaced by their real size. Untick a model to hide it.
  G-code, STEP and FreeCAD files open one at a time.
- **Sending several models**: Open in slicer sends the ticked models, and the arrow next to it has
  **Send all models in the ZIP**. A slicer opens a 3MF as a project on its own, so when a 3MF is
  among them PrintView3D asks what to send: the 3MF project, the other models, or everything as STL
  on one plate.
- **New toolbar**: Menu, Open and Recent as icons on the left; Screenshot and Theme on the right.
  The menu holds Open, Recent, Screenshot, Settings, Updates and About. **Open in slicer** shows a 3D
  printer icon and **Export STL** an export icon. The icons follow the theme.
- **Settings → About → Keyboard and mouse** lists every shortcut and mouse control.
- Long file and object names no longer make the side panel wider than the window.
- macOS: shortcuts are shown as ⌘ (for example ⌘O) in tooltips and on the About page.

## 0.18.0
- **Translations are made on GitHub only.** Hosted Weblate is no longer used: the README badge
  and the Weblate setup guide are gone. New step-by-step guide for translators,
  [docs/TRANSLATING.md](docs/TRANSLATING.md): fix a word right in the browser and send it as a
  pull request, or use Qt Linguist for bigger work.
- **Settings → Language** now links directly to that guide.
- **Thanks for installing**: on the very first start of a new installation, a short message
  invites you to star PrintView3D on GitHub. It appears once and never again, whatever you click;
  people updating from an older version don't see it. **Settings → About** keeps the link.
- **What's new after an update**: the first start after updating shows what changed since the
  version you had, once. It works however you updated (one-click installer, winget, zip or
  AppImage) and offline, from the changelog included in the program. A fresh install skips it.

## 0.17.0
- **Export STL from 3MF** (toolbar button **Export STL**, `Ctrl+E`, shown for 3MF files): a dialog
  lists every object with its name and triangle count, all ticked. Save them as **one combined STL**
  or **one STL per object**, each file named after its object, in a folder you pick (PrintView3D asks
  before replacing existing files). A 3MF with a single object goes straight to the Save dialog.
  The STL holds raw geometry only: no modifiers, negative parts, or support blockers and enforcers
  (as recorded by Creality Print, OrcaSlicer, Bambu Studio and PrusaSlicer), and no colours,
  materials or print settings. Sizes in millimetres, saved as binary STL.
- 3MF objects that have no name in the model itself now take their name from the slicer's object
  settings (Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer) instead of "Object 1", "Object 2".
- **Restart now / Later**: changing **Window transparency** (Settings → Appearance) or **Use the
  high-performance graphics card** (Settings → Viewer) only takes effect after a restart, so OK now
  asks **Restart now** or **Later**. Restart now closes PrintView3D and opens it again with the same
  file; Later keeps it for the next start. Changing it back to what is running asks nothing.
- **One window**: a file you double-click (or open with "Open with") while PrintView3D is open is
  shown in that window, which comes to the front, instead of in a second window. New option
  **Settings → Files → Open each file in a new window** for the old behaviour. Starting
  PrintView3D without a file still opens a new window; `--new-window` on the command line opens
  a file in a new window once. (macOS already did this.)
- Project description: a file opened from FreeCAD can be sent as a model directly to your slicer.

## 0.16.1
- **The title bar follows the theme** (Windows): PrintView3D now tells Qt whether its theme is light
  or dark. Before, Qt followed Windows' own dark mode and overrode ours, so with Windows in dark mode
  the light theme kept a dark title bar, and with transparency on a dark backdrop behind dark text.

## 0.16.0
- **Window transparency: Off, Mica or Acrylic** (Settings → Appearance, Windows 11). New: **Acrylic**,
  frosted glass that blurs whatever lies behind the window (desktop, other windows). Mica stays the
  calm option, a soft tint of the wallpaper. The 0.15 Mica switch carries over.
- **Readable on any wallpaper**: with Mica or Acrylic the toolbar, side panel and status bar get a
  frosted layer in the theme's colour, strongest in the light theme, and the grey labels and box
  headings are a little darker there.
- With transparency on, switching to the light theme (or back to dark) could leave the switching to the light theme (or back to dark) could leave the
  title bar and the Mica backdrop dark until the window was clicked away or resized, so the side
  panel showed dark text on a dark background. The window now redraws its frame and backdrop at once.

## 0.15.1
- **Fixed: Settings turned black with Windows transparency (Mica) on.** The Mica style rules reached
  every window that belongs to the main window, dialogs included; they now name only the main
  window's own toolbar, side panel and status bar, so Settings and the other dialogs stay solid.
- **The theme changes live in Settings**: choosing Light, Dark, Gray or Graphite switches the whole
  program at once, as the toolbar button does. OK keeps it; Cancel, Esc or the cross puts back the
  theme from when Settings was opened.
- About Mica itself: Windows draws it as a soft, nearly solid tint of the wallpaper, not as see-through
  glass, so in many setups it looks almost like the normal theme. For testing other Windows 11
  backdrops there is a hidden start option `--backdrop mica-alt` (stronger tint) or `--backdrop acrylic`
  (blur of what lies behind the window).

## 0.15.0
- **Windows 11 transparency (Mica)**: new switch in Settings → Appearance. The toolbar, side panel
  and status bar take a soft tint of the desktop wallpaper, in the dark or light variant that matches
  the theme; the 3D view stays solid. Windows 11 only (off by default, takes effect after a restart);
  Windows turns it off by itself with "Transparency effects" off, in battery saver, and shows a plain
  colour while the window is not active.

## 0.14.3
- The "v" of the version in the bottom-right corner is bold.
- Note on the green dot: right after an update it now appears at once, from the check that found the
  update (0.14.1 did not yet record that its check reached GitHub, so 0.14.2 showed no dot until the
  next check). Updates are still checked at most once a day, as promised.

## 0.14.2
- **Version badge** (bottom right): a **green dot** when a check in the last two weeks found that
  PrintView3D is up to date, the red dot when an update is available, no dot when it hasn't been
  checked. The badge now has a button-style border that fits every theme.
- Settings → Updates says so when the last check could not reach GitHub, instead of "up to date".
- Windows: after a one-click update, the new version starts at the very end of the installation and
  refreshes its taskbar icon, so the taskbar should no longer show a generic icon right after updating.

## 0.14.1
- Fixed: on Windows the taskbar showed a generic icon for PrintView3D (also when pinned). PrintView3D
  gives itself a Windows app ID, and the taskbar takes the icon from a shortcut with that same ID; the
  installer's shortcuts now carry it, and the window itself tells Windows its icon, name and how to
  start it again (so pinning works with the portable zip too). The window icon now comes in every size.
  If an old pin still shows the generic icon, unpin it and pin PrintView3D again.

## 0.14.0
- **Open STEP files** (`.step`, `.stp`) ([#15](https://github.com/sevagjb/PrintView3D/issues/15)).
  - Shown in 3D through your installed FreeCAD, like FreeCAD documents: converted hidden in the
    background, then remembered. Assembly parts are listed with their names and can be hidden.
  - The details from the file are always shown, also without FreeCAD: STEP version (AP203/214/242),
    CAD program, author, organization and date.
  - **Send to slicer:** the STEP file itself to OrcaSlicer, PrusaSlicer and Bambu Studio; an STL of the
    visible parts to other slicers. *Open in FreeCAD* is in the slicer menu.
  - Added to "Open with" on Windows, Linux and macOS (never made the default app).

## 0.13.0
- **Open more 3D formats**: OBJ, PLY, OFF and glTF / GLB ([#14](https://github.com/sevagjb/PrintView3D/issues/14)).
  - Colours saved in the file are shown: OBJ materials (`.mtl`) and vertex colours, PLY and OFF
    vertex or face colours, glTF material and vertex colours. Textures are not shown.
  - OBJ objects/groups and the objects of a glTF scene are listed separately and can be hidden.
  - glTF is converted from metres to millimetres and turned Z-up, so it stands on the plate.
  - **Send to slicer**: OBJ as it is; PLY, OFF and glTF as STL (only the visible objects).
  - Added to "Open with" on Windows, Linux and macOS (never made the default app).
- A note in the details when a model is smaller than 1 mm (usually a file made in metres).

## 0.12.0
- **Thumbnails in Windows File Explorer** for 3MF, STL, G-code and FreeCAD files ([#13](https://github.com/sevagjb/PrintView3D/issues/13)).
  3MF, G-code and FreeCAD show the preview picture saved in the file; STL models are drawn.
  Installed with PrintView3D (option in the installer, no administrator rights), removed on uninstall.
  It runs in Windows' separate helper process, so a damaged file can never affect File Explorer.

## 0.11.0
- **macOS (beta)** for Apple silicon Macs (M1 and newer), macOS 12+: `PrintView3D-macOS-AppleSilicon.dmg`,
  built automatically with every release. Free, without a paid Apple account: the first start needs
  one *Open Anyway* in System Settings → Privacy & Security (steps in the README).
- Finder: *Open With → PrintView3D* for .stl, .3mf, .gcode and .FCStd; files opened from Finder or
  dropped on the Dock icon open in the window.
- Slicers installed in /Applications are found automatically on the Mac.

## 0.10.1
- Fixed: in Settings on Windows, the highlight of the selected page in the sidebar was taller than
  its row and covered the neighbouring entries, and the text jumped when the mouse moved away.
  The rows now have a fixed height, so highlight and text always line up.

## 0.10.0
- **Updates**: Settings → Updates shows your version with **Check for updates now**, and an
  automatic check (at most once a day) that you can switch on or off at any time. PrintView3D asks
  once whether to check automatically.
- When a new version exists, the **version in the bottom-right corner** shows a red dot
  (`● v0.10.0 → 0.11.0`); click it for *What's new*, *Install update* and *Skip this version*.
- **Windows: one-click update.** PrintView3D downloads the new installer, checks its SHA-256
  fingerprint, installs it (settings kept) and starts the new version. Linux and the portable zip
  open the download page.
- **Settings has a sidebar**: Language · Appearance · Slicer · FreeCAD · Files · Viewer · Updates ·
  About, one page each. The toolbar's About opens the About page.
- README: "Updates and privacy" explains exactly what is contacted and sent (only GitHub, only the
  version question).

## 0.9.0
- **FreeCAD documents (.FCStd)**: open them to look at them. With FreeCAD installed, the model is
  shown in 3D exactly as FreeCAD displays it: visible bodies and solids, no sketches, hidden
  objects, datum planes or features inside a PartDesign Body. FreeCAD runs invisibly in the
  background; the result is cached until the file changes.
- Without FreeCAD: the file's preview picture, FreeCAD version and visible objects, with a
  "Download FreeCAD" button.
- For FreeCAD files the main button is **Open in FreeCAD**; the ▾ arrow sends the visible model
  to any installed slicer as STL.
- Settings → FreeCAD: found automatically (Windows, Linux packages, Snap, Flatpak, AppImage) or
  choose the program yourself.
- Example file `examples/demo_bracket.FCStd`.

## 0.8.0
- **Windows installer** `PrintView3D-Setup.exe`: Next → Install → Finish, no administrator rights,
  Start menu (and optional desktop) shortcut, "Open with" for .stl/.3mf/.gcode, listed in
  Windows Settings → Apps for uninstalling. Running a newer installer updates and keeps settings.
  The zip stays available as the portable version.
- Toolbar button text is bold.
- The Windows file properties now always show the current version.
- README: "Code signing policy" section (free signing via SignPath Foundation applied for).

## 0.7.0
- **Graphite** theme: a warm, dark brownish charcoal that is soft on the eyes.
- **Theme icon** (◐) at the right end of the toolbar: one click opens the theme menu.
- **`Ctrl+T`** steps to the next theme (Dark → Gray → Graphite → Light).
- Toolbar buttons now look like buttons (border and fill) in every theme; an active toggle
  (Plate) gets a teal outline.

## 0.6.0
- **Themes**: Automatic (follows the system's dark/light setting, also while running), Dark,
  Gray and Light. Choose in Settings → Appearance; the switch is immediate.
- The 3D view follows the theme (background, build plate, grid, axis labels). G-code feature and
  model colours stay the same in every theme, and the light backgrounds are light gray so white
  and yellow toolpaths stay visible.
- New installs use *Automatic*; existing installs keep the dark look until you change it.
- New command-line option `--theme` (e.g. `--theme light`).

## 0.5.0
- **Languages**: English, Arabic, Dutch, German, French and Spanish. Choose in Settings →
  Language; the switch is immediate (no restart), and an open file keeps its view, layer and filters.
- **Arabic** uses a right-to-left layout. Measurements stay in Western digits and in reading order.
- Numbers follow the language (e.g. `0,20 mm` in Dutch/German/French/Spanish).
- Qt's own texts (file dialogs, OK/Cancel) are translated too.
- New command-line option `--lang` (e.g. `--lang ar`).
- Translation workflow ready for Weblate: `tools/i18n.py` (update / compile / check / stats / new),
  notes for translators, tests that keep the files in sync. Guide: `docs/WEBLATE.md`.
- The non-English translations are first drafts awaiting review by native speakers.

## 0.4.0
- **Linux support**: a single-file AppImage that runs on most distributions (Ubuntu 22.04+,
  Debian 12+, Fedora 36+, Mint, Arch, …), built and tested automatically.
- Slicers on Linux are found automatically as AppImages (`~/Applications`, `~/Downloads`, `/opt`…),
  Flatpaks, Snaps, distribution packages and menu entries.
- Linux desktop integration: applications-menu entry, "Open With" and default app for STL, 3MF and
  G-code (Settings → Register & make default), with a hint to use the dedicated GPU.
- Wayland desktops are supported (PrintView3D runs through XWayland automatically).
- Slicers started from PrintView3D get a clean environment, so the packaged app's own libraries
  can't interfere with them.
- New command-line options `--register` and `--send-to-slicer [id]`; settings follow the XDG /
  macOS conventions.
- macOS: code is ready; a Mac build is available on request.

## 0.3.0
- Choose your slicer: Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer, UltiMaker Cura,
  Elegoo Slicer, Anycubic Slicer Next, or any other program (Custom). Installed slicers are
  detected automatically.
- The button shows the chosen slicer ("Open in OrcaSlicer"); its ▾ arrow opens the file in
  another installed slicer once, without changing the default.
- If no default is chosen, the first installed slicer is used instead of showing an error.
- Settings from earlier versions (Creality Print path) are carried over automatically.
- Tests no longer depend on which slicers are installed on the build PC.
- Demo files in `examples/`, new README with screenshots and a step-by-step build guide.

## 0.2.1
- Rotation follows the mouse without lag: mouse moves are coalesced into one redraw per
  frame instead of one redraw per mouse event (high-rate mice flooded the renderer).
- Press on the model and drag: it rotates around the exact point under the cursor.
  Press on empty space: it rotates around the model's centre. No more wandering pivot after zooming.
- From below, the plate surface and fine grid are hidden (outline and main grid lines stay),
  instead of relying on transparency, which some graphics drivers did not draw correctly.

## 0.2.0
- New slicer-style camera: left-drag orbits with Z always up (no tumbling/rolling),
  right/middle-drag pans, wheel zooms towards the cursor.
- G-code lines are drawn in a lighter mode while rotating, for smoother movement.
- Build plate becomes see-through when viewed from below, so the underside of the part is visible.
- Grid no longer flickers against the bottom face of the model.
- Settings > Graphics shows which GPU is used and can switch PrintView3D to the
  high-performance GPU on dual-GPU laptops. About shows the GPU too.

## 0.1.1
- Fix: 3MF files that use undeclared XML namespace prefixes (e.g. `p:`) failed with
  "ParseError: unbound prefix". They are now repaired while loading.

## 0.1.0 — first version
- View STL (binary + ASCII), 3MF (incl. Creality Print / OrcaSlicer multi-file projects) and G-code
- G-code: layer slider, "only this layer", feature colouring and filters, travel moves, arcs (G2/G3)
- Reads print time, filament use, printer, bed size and the embedded thumbnail from G-code
- 3MF: per-object visibility, project settings, thumbnail, and preview of sliced plates stored inside the project
- "Open in Creality Print" button (Ctrl+P) with automatic detection of the install
- Settings: register as the default app for .stl / .3mf / .gcode (per user, reversible)
- Drag & drop, recent files, screenshots, dark theme

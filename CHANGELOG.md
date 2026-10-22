# Changelog

## 0.16.0
- **Window transparency: Off, Mica or Acrylic** (Settings → Appearance, Windows 11). New: **Acrylic**,
  frosted glass that blurs whatever lies behind the window (desktop, other windows). Mica stays the
  calm option, a soft tint of the wallpaper. The 0.15 Mica switch carries over.
- **Readable on any wallpaper**: with Mica or Acrylic the toolbar, side panel and status bar get a
  frosted layer in the theme's colour, strongest in the light theme, and the grey labels and box
  headings are a little darker there.
- **The title bar follows the theme** (Windows): PrintView3D now tells Qt whether its theme is light
  or dark. Before, Qt followed Windows' own dark mode and overrode ours, so with Windows in dark mode
  the light theme kept a dark title bar, and with transparency on a dark backdrop behind dark text.
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

# Changelog

## 0.30.3
- **Right-click a toolbar button for its settings.** Each button offers one item that opens Settings
  right at its own options: Theme → **Appearance**, Screenshot → **Files → Screenshots**, Open in
  slicer → **Slicer**, Export STL → **Files → Export STL**, Plate → **Viewer → Build plate**, and
  Check, View and Measure → **Viewer → Measure, View and Check**. The Settings gear, Home, Open, Fit
  and an empty spot on the toolbar offer **Customize toolbar…**.
  [See the table](https://sevagjb.github.io/PrintView3D/use.html#toolbar-buttons).
- **Fixed: Settings opened at different sizes.** Opened from Customize toolbar, Updates or About it
  came out narrower than from the Settings button, and the **Build plate** box on the Viewer page
  then showed its two columns one under the other. It now opens at the same size from everywhere.
- **Fixed: the rows of the Build plate box didn't line up**: *Plate* and *Plate size* sat a few pixels
  higher than *Grid lines every* and *Main grid lines every* beside them.

## 0.30.2
- **Safer with files from the internet.** A review of the code found four ways a file made to harm
  could misuse PrintView3D; all four are closed:
  - A 3MF or glTF file whose triangles point at corners that don't exist made the program crash.
  - A glTF file could make PrintView3D read memory that isn't part of the file.
  - Some 3MF and glTF files never finished loading (objects that contain themselves, or place each
    other without end).
  - Text in a file (its title, description, object names) was read as HTML instead of shown as text.

  Such files now get an ordinary error message, or simply show their text as it is. macOS Quick Look
  has the same protection against 3MF files that never finish.
- **3MF projects with many copies of one object open faster**: an object placed many times is read
  once instead of once per copy.
- **Settings → Viewer**: the **Build plate** box now has two columns, the plate on the left and the
  grid's numbers and lines on the right, so it is half as tall. In a window too narrow for both, the
  right column goes under the left one, and Settings opens wide enough for the two columns when the
  screen allows.

## 0.30.1
- **Fixed: Creality Print G-code had no preview picture**, on the start page and in the side panel.
  Creality Print writes the picture size as `300*300` or `300 300`, which wasn't recognised.
- **ZIP files get a preview** on the start page: the maker's photo or render inside the ZIP, or else
  the picture of its first 3MF or G-code. Only that one picture is read.
- **Fixed: file names on the start page**: a long name without spaces was cut off at the edge of the
  preview card instead of wrapping, and an `&` in a name showed as an underlined letter in the
  recent list and the Recent menu.
- **Settings → Viewer** is now in four boxes: **Build plate**, **Measure, View and Check** (was
  *Other*), the new **Start page**, and **Graphics**. **Start page** can switch the preview card
  off; then no file is read until you open it (handy on a slow network drive).

## 0.30.0
- **Choose your toolbar** (**Settings → Toolbar**, also **☰ → Customize toolbar…** or a right-click on
  the toolbar): hide the buttons you don't use: Home, Open, Check, View, Measure, Screenshot, Theme
  and Settings. The **☰** menu, Open in slicer, Export STL, Plate and Fit always stay. The order never
  changes, hidden buttons keep their keys, and the **☰** menu now also has Check, View, Measure and
  the Theme menu. [See it in action](https://sevagjb.github.io/PrintView3D/use.html#toolbar-buttons).
- **Shorter view buttons** (same page): show Plate, Check, View, Measure and Fit as *Plate (P)*,
  *Plate*, *P* or icons only, and join them into one connected group if you like. Every change shows
  right away; OK keeps it, Cancel goes back.
- **Toolbar buttons light up under the mouse**: the tile fills with the theme's main colour (amber in
  Ember, teal in the other themes), like the view cube. The Settings gear is now orange in Ember, like
  Screenshot and Theme beside it.
- **Website**: the screenshots follow the website's theme (Light, Dark or Ember).
- **Under the hood**: unused code removed.

## 0.29.1
- **Fixed**: in **Check model**, overhangs hidden inside or under the model could show through it,
  more on some graphics cards. From below they are coloured exactly as before.
- **Settings no longer blocks the main window**: you can keep turning and inspecting the model while
  it is open. Opening it again brings the open window to the front.
- **Mouse cursors** show what the mouse does: circling arrows while turning, four arrows while moving
  (panning) and a magnifier while zooming.
- **Screenshots straight to a folder** (**Settings → Files → Screenshots**, off by default): each
  picture is saved at once, named after the file and the time, without asking where.
- **Settings → Viewer** is now in three boxes: **Build plate**, **Other** and **Graphics**.
- **Thanks to [@covrig](https://github.com/covrig)** for finding the bug and building all of this in
  [#82](https://github.com/sevagjb/PrintView3D/pull/82).

## 0.29.0
- **Check before printing** (`C`, the new **Check** button between Plate and View): the **Check
  model** section colours what may cause trouble when printing, with a count for each:
  **Overhangs** steeper than an angle you set (45° by default), **Thin walls** thinner than your
  nozzle (0.4 mm by default, checked in the background), and **Mesh problems**: holes, tangled
  (non-manifold) edges, inside-out faces and small loose parts. A red dot marks the problems found,
  and the colours follow the cuts and the objects you hide.
- **Millimetres or inches** (**Settings → Language and units → Lengths in**): sizes, measurements,
  cuts, the grid and the plate all follow it. Files are not changed.
- **Your own keyboard shortcuts** (**Settings → Keyboard and mouse**): give any action of the main
  window another key, or none. Keys the system uses are refused with the reason, and **Reset to
  defaults** puts them all back. Buttons and tooltips show their key, and follow when you change it.
- **New keys**: `C` Check, `V` the View section, `P` the plate, `S` Settings, `L` Lock facing cut,
  `D` · `A` · `O` measure a distance, an angle or a circle, `K` removes all measurements,
  `Ctrl+Shift+S` saves a screenshot. **Clip from the top** is now `T` and **Clip facing you** `Y`
  (they were `C` and `V`); you can change them back in Settings.
- **Open folder…** (in the **☰** menu): lists the 3D files of a folder in the side panel; step
  through them with `↑` / `↓` or a click. **Open…** is now called **Open file or ZIP…**.
- **Measure inside the model**: with a cut on, Measure also snaps to the outline of the cut, so walls
  and holes inside the model can be measured.
- **Lock facing cut** (`L`) replaces *Freeze the cutting plane*. While the facing cut is not locked,
  the Measure section warns you, because points measured on the cut stay behind when the view turns.
- **Drag the cuts in the 3D view** (**Settings → Viewer**, off by default): each cutting plane gets a
  round handle; drag it and the cut and its slider follow.
- **The grid**: choose the spacing of the fine and main grid lines (or leave it on Automatic); the
  scale numbers count from the plate's front-left corner (0), so no more negative numbers, and they
  follow the zoom. New options in **Settings → Viewer**: **X, Y and Z axes on the build plate**, and
  drawing both cutting planes whole when both cuts are on.
- **Start page**: hold the mouse over a recent file to see its preview picture, name and folder.
- **Settings**: a gear button in the toolbar, an **Apply** button that saves without closing, and the
  window reopens on the page you used last.
- **Also changed**: **Fit** (`F`) only fits the camera; **Reset view** and closing the View section
  also turn the view options off. View and Measure options are toggle buttons. Tooltips show sooner
  and stay inside the window.
- **Fixed**: the plate grid showing through the model (zoomed out, after Check, or seen from below);
  the line where the two cutting planes meet now stays inside them; opening another file or **Show all
  side by side** now clears measurements and cuts.
- **Thanks to [@covrig](https://github.com/covrig)**, who built all of this in [#80](https://github.com/sevagjb/PrintView3D/pull/80).

## 0.28.0
- **Measure** ([#59](https://github.com/sevagjb/PrintView3D/issues/59), `M`, the new button next to **View**): **Distance** (with
  **Show ΔX ΔY ΔZ** for the distance along each axis), **Angle** and **Circle** (diameter and
  radius). A click places a point, a drag still turns the view, and a placed point can be dragged to
  move it. Points snap to corners, the middle of an edge and edges. Every value is written next to
  its measurement, several can stay on screen, and **Clear** removes them. Optional dotted lines, and
  a **Measurement lines** thickness slider in **Settings → Viewer**.
- **The View section**: the **View** button opens a section in the side panel with every option as a
  button, and a button that is on is drawn darker. The clip sliders and checkboxes are part of it,
  with **Reset view** and **Close** at the end. New: **Freeze the cutting plane** keeps the Clip
  facing you cut where it is while you turn and move the model, and **Depth** now reads how far the
  cut is into the model, for example *Depth 22.0 of 44.0 mm*.
- **Object colours**: click an object's colour box in the **Objects** list to give it another colour;
  right-click goes back to the file's colour. Not saved.
- **A tidier side panel**: **Objects** first, **Details** last and foldable, and the file type and
  size at the top.
- **Distances on the grid** ([#69](https://github.com/sevagjb/PrintView3D/issues/69)): **Settings → Viewer → Show distances (mm) along the
  grid** (off by default) writes millimetres along the build plate, with an automatic or a chosen
  spacing.
- **Hints in the 3D view**: how to use the chosen measuring tool, and how to pass the model through a
  cut, are now written at the bottom of the 3D view.
- **New icons** for Plate, View, Measure and Fit; Fit now sits right after Measure.
- **Thanks to [@covrig](https://github.com/covrig)**, who built all of this in [#77](https://github.com/sevagjb/PrintView3D/pull/77): his first pull request
  to PrintView3D.

## 0.27.0
- **Both cuts at once** ([#70](https://github.com/sevagjb/PrintView3D/issues/70)): **Clip from the top** (`C`) and **Clip facing you** (`V`)
  can now be on together, for a corner cut away. Each key turns its own cut on and off, and the side
  panel has a slider for each, **Height** and **Depth**. The cut-away part stays one even ghost, never
  darker where the cuts overlap, and each cutting plane stops where the other cut is. **Turn off** and
  **Reset view** end both.
- **Thanks to [@covrig](https://github.com/covrig)** for the idea and for asking for an even ghost.

## 0.26.0
- **See what a cut takes away** ([#66](https://github.com/sevagjb/PrintView3D/issues/66)): with **Clip from the top** or **Clip facing you**, the part
  the cut hides stays as a white, see-through ghost with outlined edges, and the cutting plane shows as
  a faint sheet the size of the model. Two checkboxes under the slider turn each on or off, and
  **Settings → Viewer** has a Fainter … Stronger slider for each.
- **Reset view** (`R`, in the **View** menu): turns off Wireframe, X-ray and the cuts and fits the
  model, in one go.
- **A calmer toolbar**: **Recent** is in the **☰** menu and on the start page; Home and Open stay.
- **macOS: Quick Look** (beta, [#68](https://github.com/sevagjb/PrintView3D/issues/68)): Finder shows thumbnails of 3MF, STL, G-code, FreeCAD, OBJ
  and PLY files, and the space bar shows STL, 3MF, OBJ and PLY models in 3D.
  [How to switch it on](https://sevagjb.github.io/PrintView3D/install.html).
- **Thanks to [@covrig](https://github.com/covrig)** for the ghost, toolbar and Reset view ideas and all the testing, and to
  [@bmorgenthaler](https://github.com/bmorgenthaler) for the Quick Look idea.

## 0.25.1
- **Fixed**: the round handle of the clip and layer sliders was cut off at the top and bottom
  ([#66](https://github.com/sevagjb/PrintView3D/issues/66)); it is now a full circle, in every theme.
- **Website**: in the Ember theme the tabs at the top turn teal when you point at them, like the
  buttons.
- **Thanks to [@covrig](https://github.com/covrig)** for spotting the slider.

## 0.25.0
- **Look inside your models: the View button** ([#60](https://github.com/sevagjb/PrintView3D/issues/60)), for models (STL, 3MF, OBJ, …; G-code keeps
  its layer slider): **Wireframe** (`W`), **X-ray** (`X`, see-through), **Clip from the top** (`C`)
  with a height slider in the side panel, and **Clip facing you** (`V`): an upright cut that always
  faces you. Turn the view and the model turns through the cut; move (pan) it and the model slides
  across. The walls a cut lays open are drawn in red. The options work together and stay on for
  the next model. [See it in action](https://sevagjb.github.io/PrintView3D/inspect.html).
- **The size of every object** ([#59](https://github.com/sevagjb/PrintView3D/issues/59)): the **Objects** list shows each object's size (X × Y × Z)
  next to its name; the triangle count is in the tooltip.
- **Fixed**: the side panel could be cut off on the left in Arabic, and with long words or large
  fonts in Dutch, German and Romanian.
- **Dutch and Arabic** are now completely checked by a native speaker.
- **Website**: a new page, [Look inside your models](https://sevagjb.github.io/PrintView3D/inspect.html), with short videos, and a choice of
  Light, Dark and Ember, as in the program.
- **Thanks to [@covrig](https://github.com/covrig)** for both ideas and for testing them on Windows.

## 0.24.0
- **Plate menu, for models bigger than the plate** ([#61](https://github.com/sevagjb/PrintView3D/issues/61)): the **Plate** button has a small arrow
  with four choices, also in **Settings → Viewer → Build plate**:
  **Printer's plate (from the file)**, the default; **Grow to fit the model**: the printer's plate,
  made bigger only when the model sticks out of it; **Custom size…**: your own width × depth in mm;
  **Infinite grid**: an endless floor that fades out into the distance. A click on the button itself
  still shows or hides the plate, and your choice is remembered.
- **Objects higher up** ([#62](https://github.com/sevagjb/PrintView3D/issues/62)): the **Objects** box now comes right after the picture, before
  **Details**. Long details, such as a MakerWorld or Printables description, show their first
  4 lines and a **Show more** link. With more than 10 objects the list scrolls inside its own box.
- **Fold the preview picture away** ([#62](https://github.com/sevagjb/PrintView3D/issues/62)): a click on **▾ Preview picture** above the picture
  folds it away and back; it stays that way for the next files.
- **Building from source** now needs Python 3.12 to 3.14: the build scripts say so clearly and
  replace a `.venv` made by an older Python. They also install only the parts of Qt that PrintView3D
  uses (PySide6-Essentials), about 175 MB less to download.
- **Thanks to [@covrig](https://github.com/covrig)** for both ideas, the quick testing on Windows and the build fixes.

## 0.23.0
- **View cube, new look**: see-through faces, thin edges and a dashed ring. The part under the
  mouse lights up in the theme's main colour (amber in Ember, teal in the other themes).
- **Arrows and Home on the view cube**: with the mouse over the cube, ◀ ▶ turn the model to the next
  45° stop and ▲ ▼ tilt it 45° towards Top or Bottom; **Home** goes back to the fitted Iso view.
  View changes now turn smoothly instead of jumping; a click or drag stops a turn.
- **An even calmer toolbar**: with the view cube on, Iso is on the cube too (Home), so the toolbar
  keeps Fit and Plate. The key `1` still works, and Iso comes back with Top, Front and Right when the
  cube is switched off in **Settings → Viewer**.
- **What's new in the menu**: **Menu → What's new** shows this version's notes any time, with a
  button to every change on GitHub.
- **What's new in Arabic and Dutch**: the notes are shown in your language where they are
  translated, otherwise in English. Translators: see [docs/TRANSLATING.md](docs/TRANSLATING.md).
- **Fixed**: a double-click in the 3D view (for example two quick clicks on the view cube) could
  take the mouse controls away: the view cube stopped working and rotating felt different until
  PrintView3D was restarted.

## 0.22.0
- **Themes: four styles, each light and dark.** Choose **Default**, **Gray**, **Graphite** or
  **Ember**, and **Light**, **Dark** or **System** (follows your computer and switches along with it).
  New are Gray and Graphite by day. **Settings → Appearance** has a Light / Dark / System selector and
  a picture card for each style; the palette menu in the toolbar lists the styles, then the modes.
  `Ctrl+T` goes to the next style, the new `Ctrl+Shift+T` switches between light and dark.
  The theme you use now carries over. [Details](README.md#themes).
- **View cube** in the top-right corner of the 3D view: click a face to see the model from that side
  (now also from the back, left and below), drag the cube to rotate, drag the ring under it to turn
  without tilting. Switch it off in **Settings → Viewer** if you don't want it.
- **A calmer toolbar**: Top, Front and Right are on the view cube now, so the toolbar keeps Fit, Iso
  and Plate. The keys `2` `3` `4` still work, and the buttons come back when the cube is switched off.
- **Ember Light**: Export STL and the view buttons are filled with deep teal, with white text.
- **Window transparency** (Windows 11) is chosen with the same kind of selector: Off, Mica or Acrylic.
- **Fixed**: after the Top view, rotating could make the model disappear until a view button was
  pressed.

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

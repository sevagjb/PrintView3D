<p align="center">
  <img src="src/printview3d/resources/icon.png" width="96" alt="PrintView3D icon">
</p>

<h1 align="center">PrintView3D</h1>

<p align="center">
  A fast, free viewer for <b>STL</b>, <b>3MF</b>, <b>G-code</b>, <b>FreeCAD</b>, <b>STEP</b>, <b>OBJ</b>, <b>PLY</b> and <b>glTF</b> files on <b>Windows</b>, <b>Linux</b> and <b>macOS</b>,<br>
  with a one-click button that opens the file in <b>your slicer</b>.<br>
  Open a <b>FreeCAD</b> file and send it as a model straight to your slicer, no export step needed.
</p>

<p align="center">
  📖 <b>Read the guide on the website:</b>
  <a href="https://sevagjb.github.io/PrintView3D/">English</a> ·
  <a href="https://sevagjb.github.io/PrintView3D/ar/">العربية</a> ·
  <a href="https://sevagjb.github.io/PrintView3D/nl/">Nederlands</a>
</p>

<p align="center">
  <a href="../../releases/latest"><b>⬇ Download</b></a> ·
  <a href="#windows">Windows</a> ·
  <a href="#linux">Linux</a> ·
  <a href="#macos">macOS</a> ·
  <a href="#using-printview3d">How to use</a> ·
  <a href="#build-it-yourself">Build it yourself</a> ·
  <a href="CHANGELOG.md">What's new</a>
</p>

![PrintView3D showing a sliced vase with the layer slider at 60 %](docs/screenshot-gcode.png)

Microsoft retired its **3D Viewer** app, and Linux never had a good one. PrintView3D fills the gap, made for people who 3D-print:
it shows models *and* sliced G-code, tells you the size, print time and filament use, and sends the
file to Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer, Cura and others with one click.
Designing in FreeCAD? Open the `.FCStd` file and send it to your slicer as a model directly,
without exporting an STL first.

---

## Features

| | |
|---|---|
| **STL** | Smooth-shaded model on a build plate, with size, triangle count and volume. |
| **3MF** | Every object on the plate, including projects from Creality Print, OrcaSlicer and Bambu Studio. Show or hide each object (each with its size), see the project's printer and filament settings and its thumbnail. If the project is already sliced, view its toolpaths without re-slicing. **Export STL**: save the objects as plain STL files, combined or one per object. |
| **G-code** | Toolpaths coloured by type (walls, infill, top/bottom, supports, bridges, travel…), a layer slider, "show only this layer", print time, filament use and the slicer's preview picture. |
| **FreeCAD** | Open `.FCStd` documents to look at them: shown in 3D exactly as FreeCAD displays them (visible bodies only), with one click to open in FreeCAD or send to your slicer as STL. Uses your installed FreeCAD; without it you still see the preview picture. [Details](#freecad-files). |
| **STEP** | Open `.step` / `.stp` CAD files: shown in 3D with the help of your installed FreeCAD (converted in the background, remembered afterwards), with the CAD program, author and date from the file. OrcaSlicer, PrusaSlicer and Bambu Studio get the STEP file itself; other slicers get an STL. [Details](#step-files). |
| **OBJ, PLY, OFF, glTF / GLB** | Other common 3D formats, with the colours saved in the file (textures are not shown). OBJ objects and glTF scenes are listed as separate objects. OBJ goes to your slicer as it is; PLY, OFF and glTF are sent as STL, because not every slicer reads them. [Details](#other-3d-formats). |
| **ZIP files** | Open a downloaded model package (Printables, Thingiverse, …) directly. Only the 3D files are used; pictures, documents and links are skipped. Pick a model from the list, or **show all** side by side; send one model or all of them to your slicer. [Details](#zip-files). |
| **Open in your slicer** | One click (or `Ctrl+P`) opens the current file in your slicer. Installed slicers are found automatically. |
| **Default app** | Optional: make PrintView3D open `.stl`, `.3mf` and `.gcode` files when you double-click them. Fully reversible. |
| **Your language** | English, العربية (Arabic, right-to-left), Nederlands, Deutsch, Français, Español and Română; switch any time in Settings, no restart needed. [Help translate](#translations). |
| **Themes** | Four styles — Default, Gray, Graphite (warm, easy on the eyes) and Ember (warm orange and teal) — each in a light and a dark version, with Light, Dark or System (follows your computer), for the window and the 3D view. Pick from picture cards in Settings, the palette icon, `Ctrl+T` (next style) or `Ctrl+Shift+T` (light ↔ dark). Toolpath colours stay the same in every theme. |
| **Thumbnails** | Windows File Explorer shows previews of 3MF, STL, G-code and FreeCAD files (installed with PrintView3D, optional). On macOS (beta), Finder shows thumbnails of 3MF, STL, G-code, FreeCAD, OBJ and PLY files, and **Quick Look** (space bar) shows STL, 3MF, OBJ and PLY models in 3D. [Details](#quick-look-finder-previews). |
| **Updates** | **Check for updates** in Settings, or once a day if you allow it. On Windows one click downloads, checks and installs the new version. The version in the corner gets a red dot when an update is ready. [What is sent](#updates-and-privacy). |
| **One window** | A file you double-click while PrintView3D is open is shown in that window, instead of opening another one. Prefer a window per file? **Settings → Files → Open each file in a new window**. |
| **Look inside** | **View** → wireframe, X-ray (see-through), clip from the top with a height slider and a cut that faces you as you turn the view, on their own or both at once, with the cut-away part as a see-through ghost, to check meshes, hidden parts and hollow walls. **Measure** distances, angles and circles. [Details](#view-wireframe-x-ray-and-clip). |
| **Check before printing** | **Check** → overhangs, thin walls, holes, tangled (non-manifold) edges, inside-out faces and loose parts, coloured on the model with a count for each. [Details](#check-before-printing). |
| **Start page** | Your recent files, with a preview card for the one under the mouse: the picture saved in a 3MF, G-code (Creality Print too) or FreeCAD file, or the maker's photo in a ZIP, with its name and folder. Can be switched off. [Details](#using-printview3d). |
| **Your toolbar** | Hide the buttons you don't use, shorten the view buttons to a name, a key or an icon, and join them into one group (**Settings → Toolbar**). Hidden buttons keep their keys and stay in the **☰** menu. [Details](#toolbar-buttons). |
| **Comfortable to use** | Slicer-style camera, drag & drop, recent files, open a whole folder, screenshots, millimetres or inches, and keyboard shortcuts you can change. |

<table>
<tr>
<td width="50%"><img src="docs/screenshot-3mf.png" alt="A 3MF plate with four objects"><br><sub>3MF project: every object listed, each can be hidden.</sub></td>
<td width="50%"><img src="docs/screenshot-layer.png" alt="One G-code layer seen from the top"><br><sub>"Show only this layer": walls and infill of a single layer.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/screenshot-model.png" alt="An STL model on the build plate"><br><sub>STL model with size and volume.</sub></td>
<td width="50%"><img src="docs/screenshot-slicer-menu.png" alt="Slicer button with its menu"><br><sub>The ▾ arrow sends the file to another slicer just once.</sub></td>
</tr>
</table>

### Supported slicers

Found automatically when installed:

**Creality Print · OrcaSlicer · Bambu Studio · PrusaSlicer · UltiMaker Cura · Elegoo Slicer · Anycubic Slicer Next**

Any other slicer works too: choose it as **Custom** in Settings.

---

## Install

You do **not** need Python or anything else to use PrintView3D. Pick your system:

| System | Download | |
|---|---|---|
| **Windows 10 / 11** | `PrintView3D-Setup.exe` (or the portable `PrintView3D-windows.zip`) | [Instructions](#windows) |
| **Linux** (64-bit, x86-64) | `PrintView3D-x86_64.AppImage` | [Instructions](#linux) |
| **macOS 14.4+** (Apple silicon: M1 and newer), beta | `PrintView3D-macOS-AppleSilicon.dmg` | [Instructions](#macos) |
| **macOS 14.4+** (Intel), beta | `PrintView3D-macOS-Intel.dmg` | [Instructions](#macos) |

All downloads are on the **[latest release](../../releases/latest)** page.

### Windows

1. Go to the **[latest release](../../releases/latest)** and download **`PrintView3D-Setup.exe`**.
2. Double-click it and click **Next → Install → Finish**.
   - Installs for your user account only, so **no administrator password** is needed.
   - Adds PrintView3D to the Start menu (desktop shortcut optional) and to "Open with" for
     `.stl`, `.3mf` and `.gcode` files.
3. PrintView3D starts. Done.

**Previews in File Explorer:** the installer also shows **thumbnails of 3MF, STL, G-code and
FreeCAD files** in File Explorer (you can untick this during installation). 3MF, G-code and FreeCAD
show the preview picture saved by your slicer or FreeCAD; STL files are drawn. If thumbnails don't
appear at once, switch the folder view to *Large icons*, or sign out and in again. (If PowerToys'
File Explorer add-ons are on, PowerToys keeps showing STL and G-code thumbnails.)

**Updating:** download the new `PrintView3D-Setup.exe` and run it. It replaces the old version and
keeps your settings.

> **"Windows protected your PC"?** Releases are not code-signed yet (free signing through the
> SignPath Foundation is being applied for, see [Code signing policy](#code-signing-policy)), so
> Windows SmartScreen may warn the first time. Click **More info → Run anyway**. All the source code
> is in this repository, and every release is built automatically by [GitHub Actions](../../actions)
> from that code.

**Portable version:** download `PrintView3D-windows.zip`, extract it and run `PrintView3D.exe`.
Nothing is installed. (`install_windows.bat` in the zip still works too.)

#### Make it the default program for 3D files (optional)

1. In PrintView3D, click **Settings**.
2. Open the **Files** page and click **Register & choose as default…**.
3. Windows Settings opens. Pick **PrintView3D** for `.stl`, `.3mf` and `.gcode`.

Windows requires you to confirm this last step yourself; no program is allowed to do it silently.
**Remove registration** in the same place undoes everything.

#### Uninstall

**Windows Settings → Apps → Installed apps → PrintView3D → Uninstall**. This removes the program,
its shortcuts and file associations, and asks whether to delete your settings too.
(Portable version: run `uninstall_windows.bat` from the extracted folder.)

### Linux

PrintView3D for Linux is a single **AppImage** file: it contains everything it needs and runs on
most distributions without installing packages: Ubuntu 22.04 or newer, Linux Mint 21+, Debian 12+,
Fedora 36+, openSUSE Tumbleweed, Arch, Manjaro, Pop!_OS, elementary OS, Zorin OS and others.

1. Download **`PrintView3D-x86_64.AppImage`** from the **[latest release](../../releases/latest)**.
2. Make it executable: right-click it → **Properties → Permissions → Allow executing file as
   program**, or in a terminal:
   ```bash
   chmod +x PrintView3D-x86_64.AppImage
   ```
3. Double-click it, or run `./PrintView3D-x86_64.AppImage`.

**Add it to your applications menu** (optional, recommended): in PrintView3D open **Settings → Files**
and click **Register & make default**. PrintView3D then appears in your applications menu and in
"Open With", and opens `.stl`, `.3mf` and `.gcode` files on double-click. On Linux this takes effect
immediately; **Remove registration** undoes it.

Tip: keep the AppImage in a fixed place such as `~/Applications` before registering, because the
menu entry points to wherever the file is. Or let the script do it all:

```bash
./install_linux.sh PrintView3D-x86_64.AppImage     # copies to ~/Applications + adds the menu entry
./uninstall_linux.sh                               # removes it again
```

(The two scripts are in the [source code](../../archive/refs/heads/main.zip).)

**Slicers on Linux** are found automatically when installed as an AppImage (in `~/Applications`,
`~/Downloads`, `~/Desktop`, `~/bin`, `/opt`…), as a **Flatpak** or **Snap**, from your
distribution's packages, or in `/opt`. Otherwise choose it once with **Browse…** in Settings.

<details>
<summary><b>Linux troubleshooting</b></summary>

| Problem | Fix |
|---|---|
| Nothing happens / "AppImages require FUSE" | Install FUSE: `sudo apt install libfuse2` (Ubuntu/Debian), `sudo dnf install fuse fuse-libs` (Fedora). Or run it without FUSE: `./PrintView3D-x86_64.AppImage --appimage-extract-and-run` |
| `GLIBC_2.35 not found` | Your distribution is older than Ubuntu 22.04 / Debian 12. Build from source instead (below). |
| Window opens but the 3D view stays black | Make sure your graphics driver is installed (Mesa or the NVIDIA driver). In a virtual machine, enable 3D acceleration. |
| Wayland desktop | Supported. PrintView3D automatically runs through XWayland, because the 3D view needs it. |
| Slow rotation on a laptop with two GPUs | Start PrintView3D from the applications menu after **Register** (the menu entry asks for the dedicated GPU), or use your desktop's *Launch using Dedicated Graphics Card* option. |

</details>

### macOS

> **Beta.** The Mac version is built and checked automatically, but has not been tried by many people
> on real Macs yet. Please [tell us how it works](../../issues/new?template=mac_build.md): your Mac
> model, macOS version, and anything that looks wrong.

For **macOS 14.4 (Sonoma) or newer**, in two versions; pick the one for your Mac
( → **About This Mac**: *Chip* means Apple silicon, *Processor* means Intel):

| Your Mac | Download |
|---|---|
| **Apple silicon** (M1, M2, M3, M4 and newer) | `PrintView3D-macOS-AppleSilicon.dmg` |
| **Intel** (2018 and newer, the Macs that run macOS 14) | `PrintView3D-macOS-Intel.dmg` |

1. From the **[latest release](../../releases/latest)** download the `.dmg` for your Mac.
2. Open it and drag **PrintView3D** onto **Applications**.
3. Start PrintView3D from Applications. **The first time**, macOS says it *cannot verify* the app.
   Click **Done** (not "Move to Trash").
4. Open **System Settings → Privacy & Security**, scroll down to *Security* and click
   **Open Anyway** next to PrintView3D. Confirm with your password or Touch ID.

From then on it opens normally.

> **Why this extra step?** Apple only skips it for apps from developers who pay Apple every year
> for a certificate and "notarization". PrintView3D is free and has no budget for that, so it is
> signed without an Apple account instead. The program is the same open-source code as on Windows
> and Linux, built automatically by [GitHub Actions](../../actions). (Right-click → Open no longer
> works for this on macOS 15 and newer; use Open Anyway as above.)

**Open files with PrintView3D:** in Finder, right-click a `.stl`, `.3mf`, `.gcode` or `.FCStd` file →
**Open With → PrintView3D**. To make it the default: right-click the file → **Get Info** →
*Open with:* **PrintView3D** → **Change All…**.

#### Quick Look (Finder previews)

PrintView3D brings Quick Look support for 3D printing files (beta):

- **Thumbnails in Finder** for 3MF, STL, G-code, FreeCAD, OBJ and PLY files. 3MF, G-code and FreeCAD
  files show the picture your slicer or FreeCAD saved in them; STL files (and 3MF files without a
  picture) are drawn, like on Windows.
- **Space bar preview:** select a file and press the space bar. STL, 3MF, OBJ and PLY models are shown
  in 3D (drag to turn, scroll or pinch to zoom) with their size in millimetres. G-code and FreeCAD files
  show their saved picture. For everything else (layers, objects, settings) open the file in PrintView3D.

It works once PrintView3D is in **Applications** and has been started once (steps 1–4 above). If no
previews appear, open **System Settings → General → Login Items & Extensions**, click **Quick Look**
(the ⓘ next to it) and switch on **PrintView3D**. Finder keeps old thumbnails for a while; files you
copy or save afterwards show the new ones. STEP files are not previewed: reading them needs FreeCAD,
which Quick Look can't use. If another app (a slicer, FreeCAD) also offers previews for one of these
file types, macOS may use that app's preview instead.

**Slicers** in Applications (Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer, Cura, …) are
found automatically. **Updates:** *Download update* opens the release page; drag the new version
into Applications to replace the old one. Older Macs that can't run macOS 14:
[let us know](../../issues/new?template=mac_build.md) if you need a version for them.

---

## Using PrintView3D

**Open a file:** double-click it (if PrintView3D is the default), drag it onto the window, use
**Open file or ZIP…** (`Ctrl+O`), or pick it from **Recent** in the **☰** menu or on the start page. Try the files in [`examples/`](examples) to get started.

**Home:** the house button (`Ctrl+W`) closes the open file and goes back to the start page, with
your recent files. It also gives back the memory the file took, which matters most after a large
G-code or ZIP.

On the start page, hold the mouse over a recent file and a card in the bottom right corner shows its preview
picture (3MF projects, G-code and FreeCAD files that have one), its name and the folder it is in.
A ZIP shows the maker's photo or render inside it, or else the picture of its first 3MF or G-code.
The card stays in the same place for every file, so you can run down the list and compare. Don't
want it? Untick **Settings → Viewer → Start page → Show a preview of recent files when the mouse is
over them**; then the files are not read until you open them.

![The start page: recent files, with the preview card of the one under the mouse](docs/screenshot-start-page.png)

**A whole folder:** **☰ → Open folder…** lists the 3D files of a folder in the side panel; step
through them with `↑` / `↓` or a click.

**One window:** a file you double-click while PrintView3D is already open is shown in that window,
which comes to the front. To give every file its own window (to compare two models side by side),
tick **Settings → Files → Open each file in a new window**. Starting PrintView3D from the Start
menu or applications menu, without a file, always opens a new window.

### Mouse

| Action | What it does |
|---|---|
| **Left-drag** | Rotate. Press *on the model* to rotate around that exact point; press on empty space to rotate around the model's centre. The plate always stays level. |
| **Right-drag** (or middle-drag, or Shift + left-drag) | Move (pan) |
| **Mouse wheel** | Zoom towards the mouse pointer |

While you turn, move or zoom, the pointer shows it (circling arrows, four arrows, a magnifier), and is the normal arrow again when you let go.
| **View cube** (top-right corner) | A see-through cube with a dashed ring. Click a face to jump to that view (Top, Front, Right, Back, Left or Bottom). Drag the cube to rotate, or drag the ring under it to turn without tilting. With the mouse over the cube, **arrows** and a **Home** icon appear: ◀ ▶ turn the model to the next 45° stop, ▲ ▼ tilt it 45° towards Top or Bottom, and Home goes back to the fitted Iso view. The arrows always land on one of the cube's 26 views (faces, edges, corners), so after a free drag the first click lines the view up again. View changes turn smoothly; click or drag to stop one. The part under the mouse lights up in the theme's main colour (amber in Ember). Because Top, Front and Right are on the cube and its Home icon is the Iso view, the toolbar keeps only Fit (handy when you have zoomed far away from the model) and Plate; hide the cube in Settings → Viewer and the Iso, Top, Front and Right buttons come back. The keys `1` `2` `3` `4` work either way. |

Looking from underneath? The plate gets out of the way so you can see the bottom of the part.

### Keyboard

These are the keys PrintView3D comes with. **Settings → Keyboard and mouse** lists them all, and
you can give any of them a key of your own there: click its field and press the new key (the
clear button removes it). The buttons then show your key (tooltips name no keys). **Reset to defaults** puts
them all back. Keys the system uses (the Windows or Super key, Alt+F4, Alt+Tab, ⌘Q, Ctrl+Alt+Del
and the like), Tab, Enter, Esc and Space can't be chosen, and neither can a key another action
already has. The mouse controls are fixed.

| Key | Action |
|---|---|
| `Ctrl+O` | Open a file |
| `Ctrl+W` | Close the file (back to the start page) |
| `Ctrl+P` | Open the file in your default slicer |
| `Ctrl+E` | Export STL (3MF projects, FreeCAD and STEP files) |
| `S` | Settings (it stays open beside the main window, which keeps working) |
| `Ctrl+Shift+S` | Save a screenshot of the 3D view. It asks where, or saves straight to a folder of your choice: **Settings → Files → Screenshots** |
| `Ctrl+T` | Next theme style (Default → Gray → Graphite → Ember), same light/dark mode |
| `Ctrl+Shift+T` | Switch the theme between light and dark |
| `F` | Fit the model in the view |
| `1` · `2` · `3` · `4` | Iso · Top · Front · Right view |
| `P` | Build plate on / off |
| `C` · `V` | Check section · View section, on / off (models) |
| `W` · `X` · `T` · `Y` | Wireframe · X-ray · Clip from the top · Clip facing you, on / off (models) |
| `L` | Lock the facing cut: it stops turning with the view (models) |
| `R` | Reset view: wireframe, X-ray and the cuts off, model fitted (on G-code: fit) |
| `M` | Measure on / off (models) |
| `D` · `A` · `O` | Measure a distance · an angle · a circle |
| `K` | Remove all measurements (Measure stays on) |
| `↑` / `↓` | Next / previous layer (G-code), or the file above / below in a ZIP or folder |
| `Page Up` / `Page Down` | 10 layers up / down |
| `Home` / `End` | First / last layer |

### View: wireframe, X-ray and clip

The **View** button in the toolbar opens the **View** section in the side panel, with every option
as a button (a button that is on is drawn darker). It changes how a model is drawn (STL, 3MF, OBJ
and the other model formats; G-code has its layer slider instead):

- **Wireframe** (`W`): the triangles of the mesh, to see how fine it is or spot broken geometry.
- **X-ray** (`X`): the parts become see-through, so parts inside other parts, cavities and
  hollow walls show.
- **Clip from the top** (`T`): hides everything above a height. A slider in the side panel moves
  the cut; the inside of the walls that the cut lays open is drawn in red. `T` or the button
  again shows the whole model.
- **Clip facing you** (`Y`): an upright cut that always faces you and hides the part of the model
  in front of it. Turn the view and the model turns through the cut; move (pan) the view and it
  slides across, as if you held the model up to a scanner. For a cut from the front or the side,
  click that face on the view cube. The slider moves the cut nearer or further, and **Depth**
  shows how far it is into the model. **Lock facing cut** (`L`, the button left of Reset view)
  stops the cut turning with the view, so you can turn the model and look at the cut from the side;
  the slider still moves it. While the cut is not locked, the Measure section shows a red dot and
  *Facing cut not locked*; hover over it for why: points placed on the cut stay behind when the
  view turns.
- **Both cuts at once**: `T` and `Y` each turn their own cut on and off, so both can be on together
  for a corner cut away, with a **Height** and a **Depth** slider in the side panel. What the cuts
  hide stays one even ghost, and each cutting plane stops where the other cut is. **Reset view**
  ends both.
- **Show the cut-away part** and **Show the cutting plane** (under the sliders, both on by
  default): what the cut hides stays as a white, see-through ghost with outlined edges, and the
  cutting plane shows as a faint sheet the size of the model, so you see what the cut takes away
  and where. Each is a button that stays lit while on, and your choice is remembered. In **Settings → Viewer**, **Cut-away part** and
  **Cutting plane** each have a Fainter … Stronger slider; the 3D view changes while you drag.
- **Drag the cuts in the 3D view** (an option): tick **Settings → Viewer → Also move the cutting
  planes by dragging them in the 3D view** and each cut gets a small round handle on the edge of its cutting
  plane, with a short line showing which way it moves. Under the mouse its colours swap. Drag it
  to move the cut; its slider moves along.
- **Reset view** (`R`): turns all of the above off and fits the model, like **Fit**, in one go.
  Measurements stay.

Wireframe and X-ray stay on when you open the next model; the cuts and the measurements are removed. The options work together (X-ray and clip, for example).

### Measure, object colours and grid numbers

![Measuring a distance, an angle and a hole](docs/assets/inside/measure.png)

- **Measure** (`M`, the button next to **View**): **Distance** (with ΔX ΔY ΔZ if you like),
  **Angle** and **Circle** (diameter and radius). A click places a point, a drag still turns the
  view, and a placed point can be dragged. Points snap to corners and edges, and with a cut on also
  to the outline of the cut, so you can measure inside the model; the value is written next to
  every measurement, and **Clear** (`K`) removes them all.
- **Object colours**: click the colour box of an object in the **Objects** list to give it another
  colour; right-click goes back to the file's colour. Not saved.
- **Grid numbers**: **Settings → Viewer → Show scale numbers on the grid** writes millimetres
  along the build plate, as many as fit at the zoom you look at, counting from the plate's
  front-left corner (0). **Grid lines every** and **Main grid lines every** set the grid itself.

More, with pictures: [Look inside your models](https://sevagjb.github.io/PrintView3D/inspect.html). Built by [@covrig](https://github.com/covrig).

### Check before printing

![Check model: overhangs in red and a thin wall in orange](docs/assets/inside/check.png)

The **Check** button (`C`, between Plate and View) opens the **Check model** section and colours
what may cause trouble when printing, with a count for each (models only, not G-code):

- **Overhangs**: faces facing down and leaning further from vertical than an angle (45° by default);
  faces on the plate don't count.
- **Thin walls**: walls and pins thinner than your nozzle (0.4 mm by default). Runs in the
  background, so it is off until you tick it.
- **Mesh problems**: **Holes** (open edges), **Tangled edges** (non-manifold), **Inside-out faces**
  (flipped normals) and **Loose parts** up to a size you set (5 mm by default).

A red dot marks the problems found. Click a colour box to change its colour; hover over a name for
what it means. The highlights follow the cuts and the objects you hide.
More: [Check before printing](https://sevagjb.github.io/PrintView3D/inspect.html#check-before-printing). Built by [@covrig](https://github.com/covrig).

### Choosing your slicer

![Settings window](docs/screenshot-settings.png)

**Settings → Slicer → Default slicer.** Each slicer is marked *installed* or *not found*. If yours
is installed in an unusual place, click **Browse…** and select its program file. For a slicer that
is not in the list, choose **Custom program…**, give it a name and select its `.exe`.

The green button is renamed to match ("Open in OrcaSlicer"). The small **▾** arrow next to it lists
your other installed slicers, for opening a file in one of them just once.

### FreeCAD files

Open a FreeCAD document (`.FCStd`) with **Open** or drag & drop it onto the window
(PrintView3D does not take over the double-click from FreeCAD).
It is for looking only; nothing in the file is changed.

- **With FreeCAD installed** (free, [freecad.org](https://www.freecad.org/downloads.php)) the model is
  shown in 3D as FreeCAD displays it: visible bodies and solids only, without sketches, hidden
  objects or datum planes. PrintView3D starts FreeCAD invisibly in the background to convert the
  shapes (a few seconds the first time; then it is remembered until the file changes).
  The big button becomes **Open in FreeCAD**, and the ▾ arrow sends the visible model to
  your slicer as an STL. **Export STL** (`Ctrl+E`) saves the visible solids as STL files: all in
  one file, or one file per solid (the same choices as for a 3MF project). This also works for
  STEP files.
- **Without FreeCAD** you see the file's preview picture, the FreeCAD version and the visible
  objects, with a button to download FreeCAD.

FreeCAD is found automatically in its usual places (Windows installer, Linux packages, Snap,
Flatpak, AppImage). If yours is elsewhere, choose it in **Settings → FreeCAD**.

Because FreeCAD itself opens the file, a FreeCAD or STEP file deserves the same trust as when you
open it in FreeCAD: open files from people and sites you trust.

<table>
<tr>
<td width="50%"><img src="docs/screenshot-freecad.png" alt="A FreeCAD bracket shown in 3D"><br><sub>With FreeCAD installed: the bracket in 3D.</sub></td>
<td width="50%"><img src="docs/screenshot-freecad-preview.png" alt="The same file without FreeCAD: the preview picture"><br><sub>Without FreeCAD: the preview picture saved in the file.</sub></td>
</tr>
</table>

### Export STL from 3MF

With a 3MF project open, **Export STL** in the toolbar (`Ctrl+E`) saves its objects as plain STL
files, for example to share a model or open it in a program that does not read 3MF.

- A dialog lists every object with its name and triangle count, all ticked; untick what you don't
  need.
- **The arrow next to the button** offers every way directly: *All objects as one STL*, *One STL per
  object* and *Choose objects…* (the dialog). The one a click makes is shown in bold.
- **What a click does** (and `Ctrl+E`) is chosen in **Settings → Files → Export STL**: show the list
  of objects (the default), save everything as one STL, or save one STL per object. *Change what a
  click does…* at the bottom of the arrow's menu opens that setting.
- **One combined STL**: the ticked objects in one file, placed as they are on the plate.
- **One STL per object**: each file is named after its object and saved into a folder you choose
  (PrintView3D asks before replacing files that are already there).
- A file with only one object always goes straight to the Save dialog.
- **Raw geometry only:** modifiers, negative parts and support blockers / enforcers are left out
  (as recorded by Creality Print, OrcaSlicer, Bambu Studio and PrusaSlicer), and so are colours,
  materials and print settings. Sizes are in millimetres; the files are binary STL.

### ZIP files

Model downloads often come as a ZIP. Open it like any other file (**Open file or ZIP…** or drag it onto the
window); there is no need to unpack it first.

<table>
<tr>
<td width="50%"><img src="docs/screenshot-zip-showall.png" alt="Four models from a ZIP side by side, with the list of files in the ZIP"><br><sub><b>Show all side by side</b>: tick or untick each model; the G-code opens on its own.</sub></td>
<td width="50%"><img src="docs/screenshot-zip-gcode.png" alt="The sliced G-code from the same ZIP, with the file list"><br><sub>Click a file in the list, or use ↑ / ↓: here the sliced G-code from the same ZIP.</sub></td>
</tr>
</table>

- **Only the 3D files are used**: STL, 3MF, OBJ, PLY, OFF, glTF/GLB, STEP, FreeCAD and G-code.
  Pictures, PDFs, read-me files, web links, ZIPs inside the ZIP and the hidden `__MACOSX` folder
  are skipped, and the panel says how many were skipped.
- **A ZIP with one 3D file** opens just like that file.
- **More files** are listed in the side panel with a coloured label for their type (STL, 3MF,
  G-code, …) and a short explanation of each type. The first file is shown; click another one, or
  use **↑ / ↓**, to switch.
- **Show all side by side** places the models next to each other: up to three in one row, then a
  grid (four as 2 × 2, six as 3 × 2, nine as 3 × 3, …), spaced by their real size. Untick models in
  **Objects** to hide them. G-code, STEP and FreeCAD files are opened one at a time.
- **Open in slicer** sends the model you are looking at; in Show all, the ticked models. The arrow
  next to the button has **Send all models in the ZIP**.
- A slicer opens a **3MF as a project on its own**, so it cannot take a 3MF together with other
  files. When the models to send include a 3MF, PrintView3D asks: the 3MF project (with its
  plates and settings), the other models on one plate, or **everything as STL** (the project's
  objects become a plain STL, so all models go on one plate).

  <img src="docs/screenshot-zip-send.png" alt="The Send to slicer dialog: the 3MF project, the other models, or everything as STL" width="520">

The 3D files are unpacked into PrintView3D's own cache folder (slicers need real files); the sizes
are checked first, so a damaged or malicious ZIP cannot fill your disk. Files from ZIPs opened more
than a day ago are removed automatically.

### STEP files

STEP (`.step`, `.stp`) is the common format for exchanging CAD models between programs. It stores
exact shapes (curved surfaces), not triangles, so PrintView3D uses **FreeCAD** to turn them into a
mesh, the same way as for [FreeCAD files](#freecad-files): hidden in the background, a few seconds
the first time, then remembered until the file changes.

- **Parts:** an assembly's parts are listed separately with their names from the file, and can be
  hidden. (If FreeCAD's import gives anything unexpected, PrintView3D shows each solid instead, so
  the shape is always right.)
- **Without FreeCAD** you still see the details from the file (STEP version, the CAD program it was
  made with, author, organization, date) and a button to download FreeCAD.
- **Send to slicer:** OrcaSlicer, PrusaSlicer and Bambu Studio open STEP files themselves and get the
  file as it is (also without FreeCAD). Other slicers get the visible parts as STL, which needs FreeCAD.
- STEP files are added to **Open with**, but PrintView3D never makes itself their default app.

### Other 3D formats

| Format | What is read | Sent to your slicer as |
|---|---|---|
| **OBJ** (`.obj`) | Objects (`o`) or groups (`g`) as separate objects; colours from the `.mtl` file next to it, or vertex colours. | The `.obj` itself |
| **PLY** (`.ply`) | Text and binary; vertex or face colours. Point clouds (no faces) can't be shown. | STL |
| **OFF** (`.off`) | Text files (also COFF), with vertex or face colours. | STL |
| **glTF / GLB** (`.gltf`, `.glb`) | Every object in the scene at its position, with its material colour or vertex colours. | STL |

- **Sizes:** OBJ, PLY and OFF have no units; PrintView3D treats the numbers as millimetres, like
  slicers do. If a model shows up tiny, the file was probably made in metres; your slicer can scale it.
  glTF is always in metres and is shown in millimetres (with Z up, as on a printer).
- **Not read:** textures (image files on the model), animations, and glTF files compressed with Draco
  or meshoptimizer (PrintView3D says so; export them again without compression).
- These types are added to **Open with**, but PrintView3D never makes itself their default app.

### Language

**Settings → Language and units → Language** switches the whole program immediately, including file dialogs and
standard buttons. English is the default; *Automatic* follows your system language. Arabic uses a
right-to-left layout; measurements always use Western digits (0.20 mm).
A wrong or missing word? The link on that page leads to [How to translate](docs/TRANSLATING.md).

**Millimetres or inches:** **Settings → Language and units → Lengths in** shows every length (sizes,
measurements, cuts, the grid and the plate) in millimetres or inches. Files are not changed.

### Themes

A theme is a **style** in a **mode**. There are four styles — **Default**, **Gray**, **Graphite**
and **Ember** — and each comes in a light and a dark version. The mode picks which one you see:

- **Light** or **Dark**: always that version.
- **System**: follows the dark/light setting of Windows, macOS or your Linux desktop, and switches
  along when that changes. On Linux it reads the GNOME, GTK or KDE setting; if the desktop doesn't
  say dark anywhere, PrintView3D starts light.

Where to choose:

- **Settings → Appearance → Theme**: a Light / Dark / System selector and a **picture card** for
  each style, showing PrintView3D in that style and mode. Click a card or a mode and every window
  switches at once, so you can try them one after another. **OK** keeps your choice; **Cancel**
  goes back to the theme you had when you opened Settings.
- The **palette icon** at the right end of the toolbar: the four styles with a colour swatch, then
  Light, Dark and System.
- **`Ctrl+T`** steps to the next style and keeps the mode; **`Ctrl+Shift+T`** switches the same
  style between light and dark.

The styles:

- **Default**: neutral greys with teal buttons — white-grey by day, charcoal at night.
- **Gray**: cooler, mid greys in both versions.
- **Graphite**: warm coffee tones — latte and taupe by day, a dark brownish charcoal that is soft
  on the eyes at night.
- **Ember**: orange and teal. By day warm cream: the slicer button, OK and the chosen
  Settings page are orange; the toolbar tiles, sliders and focus are teal; Export STL and the view
  buttons (Fit and Plate; Iso too when the view cube is off) are filled with a deep teal with white text; text is
  a soft slate grey instead of black, and the 3D view a deeper sand colour, so white and yellow
  toolpaths stay visible. At night the same orange and teal on deep lagoon greens, with a teal-lit
  build plate.

Settings from older versions carry over: *Automatic* becomes Default + System, *Ember Light*
becomes Ember + Light, *Ember Dark* becomes Ember + Dark, and so on.

**Window transparency** (Windows 11) sits under the theme, with the same kind of selector:
**Off**, **Mica** (a soft tint of your wallpaper) or **Acrylic** (frosted glass). It takes effect
after a restart; on other systems it stays Off.

The switch is immediate; the 3D background, plate and grid change with it, while G-code and
model colours stay the same so they always match your slicer. In every theme, text and grey labels
have a contrast of at least 4.5 : 1 against the window, so they stay easy to read.

![Settings → Appearance with a picture card for every theme style](docs/screenshot-theme-picker.png)

![Ember Light with a 3MF plate, and Ember Dark with G-code](docs/screenshot-theme-ember.png)

![The theme menu on the toolbar](docs/screenshot-theme-menu.png)

![The same G-code in the Dark, Gray, Graphite and Light themes](docs/screenshot-themes.png)

#### Window transparency (Windows 11)

**Settings → Appearance → Window transparency** lets the toolbar, side panel and status bar show
what lies behind the window, in any theme:

- **Mica**: a soft tint of your desktop wallpaper (as in File Explorer).
- **Acrylic**: frosted glass that blurs the desktop and other windows behind it.
- **Off** (default): solid, as before.

The 3D view always stays solid. It takes effect after a restart: when you click OK, PrintView3D
asks **Restart now** (it closes and opens again, with the same file) or **Later**. Windows draws the
effect itself and shows a plain colour while the window is not active, and switches it off with
*Transparency effects* off in Windows Settings or in battery saver. Windows 10 and other systems
keep the normal look.

### Toolbar buttons

**Settings → Toolbar** (also **☰ → Customize toolbar…**, or right-click the gear or an empty spot on the toolbar) chooses which
buttons the toolbar shows, for a calmer toolbar if you don't use every feature:

- **Can be hidden:** Home, Open, Check, View, Measure, Screenshot, Theme and Settings.
- **Always shown:** the **☰** menu, Open in slicer, Export STL (3MF and CAD files), Plate and Fit.
- **The order never changes.** A hidden button only leaves the toolbar; Plate stays the first of the
  view buttons and Fit the last.
- **Nothing gets lost.** A hidden button keeps its key (`C`, `V`, `M`, `Ctrl+W`, …), and the **☰**
  menu has everything, including Check, View, Measure and the Theme menu.
- **Right-click a button for its settings.** Each button offers one item that opens Settings at
  that button's own options:

  | Right-click on | Opens |
  |---|---|
  | Theme | **Appearance** (the themes) |
  | Screenshot | **Files → Screenshots** (the folder, save without asking) |
  | Open in slicer | **Slicer** (the default slicer) |
  | Export STL | **Files → Export STL** (what a click does) |
  | Plate | **Viewer → Build plate** |
  | Check, View, Measure | **Viewer → Measure, View and Check** |
  | Settings, Home, Open, Fit or an empty spot | **Customize toolbar…** |

Under **Look** you choose how the view buttons (Plate, Check, View, Measure and Fit) are labelled:
**icon, name and key** (*Plate (P)*, the default), **icon and name** (*Plate*), **icon and key**
(*P*) or **icon only** (the tooltip names it). **Join the view buttons into one group** draws them
as one connected bar.

![Settings → Toolbar: buttons switched off, shorter labels and a joined group, shown live on the toolbar](docs/assets/toolbar-settings.gif)

Every change shows in the window, and in the picture at the top of the page, right away: **OK**
keeps it, **Cancel** goes back. **Reset to defaults** shows every button again.

### Updates

**Settings → Updates** shows your version and has **Check for updates now**. You can also switch on
**Check for updates automatically (once a day)**; PrintView3D asks once whether you want this (on
the second start: the first start shows only the program), and you can change it there at any time.

When a new version exists, the version in the bottom-right corner shows a **red dot** (`● v0.10.0 →
0.11.0`), and so does *Updates* in Settings. Click it to see **What's new**, then:

- **Windows (installed with Setup.exe): Install update.** PrintView3D downloads the new installer,
  checks its SHA-256 fingerprint against the one GitHub publishes, installs it (no questions, your
  settings are kept) and starts the new version.
- **Linux (AppImage) and the portable Windows zip: Download update** opens the release page;
  download the new file and replace the old one. The AppImage can also be updated with
  [AppImageUpdate](https://github.com/AppImageCommunity/AppImageUpdate) or other tools that read
  AppImage update information: they download only the changed parts, using the
  `PrintView3D-x86_64.AppImage.zsync` file published with every release. PrintView3D itself never
  starts such a tool.
- **Skip this version** hides that version; the next one is shown again.

After an update, the first start shows **What's new** since the version you had, once, however
you updated (installer, winget, zip or AppImage). Any time later, **Menu → What's new** shows the
notes of the version you have, with a button to every change on GitHub. Both are read from the
changelog that comes with the program, so they need no connection; a fresh install doesn't show the
window by itself. The notes are in your language where the changelog is translated (Arabic and
Dutch: [`CHANGELOG.ar.md`](CHANGELOG.ar.md), [`CHANGELOG.nl.md`](CHANGELOG.nl.md)); otherwise, or
for a version not translated yet, they are shown in English.

![Settings → Updates when a new version is available](docs/screenshot-updates.png)

#### Updates and privacy

PrintView3D works offline. It connects to the internet **only** for updates, and only when you
click *Check for updates now* or have switched on the daily check:

| | |
|---|---|
| **What is contacted** | `api.github.com` (to ask for the newest release of this project) and, when you click *Install update*, the download from `github.com` |
| **How often** | At most once a day (automatic check), or when you click *Check for updates now* |
| **What is sent** | Only the request for the newest version, with the program name and version (`PrintView3D/0.10.0`). No personal data, no files, no usage statistics, no ID. |
| **What GitHub sees** | Like any website: your IP address. See [GitHub's privacy statement](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement). |
| **How to turn it off** | Settings → Updates → untick *Check for updates automatically*. Nothing is contacted after that. |

### Smoother rotation on laptops

Many laptops have two graphics chips and run programs on the slower one by default.
**Settings → Viewer → Graphics** shows which one PrintView3D uses. If it says *Intel*, tick
**Use the high-performance graphics card** and click OK; choose **Restart now** (or **Later**, and
it switches the next time you start PrintView3D).

---

## Build it yourself

Only needed if you want to change the code or don't want to use the ready-made download.

### Step 1: Install the right Python version ⚠️

PrintView3D uses **VTK** for its 3D drawing, and VTK only supports certain Python versions.
**The newest Python is often *not* supported yet**, and python.org's big download button always
gives you the newest one.

| Python version | Works? |
|---|---|
| 3.10, 3.11 | ❌ No (too old for the library versions the builds use, such as NumPy 2.5) |
| **3.12** | ✅ **Yes, recommended** (what the official builds use) |
| 3.13, 3.14 | ✅ Yes |
| 3.15 and newer | ❌ Not yet (no VTK version for it) |

#### Windows

**Already have Python?** Check which versions you have: open *Command Prompt* and type `py --list`.

**Install Python 3.12**, using one of these:

- **Easiest**, in *Command Prompt* or *PowerShell*:
  ```
  winget install Python.Python.3.12
  ```
- **Or** from python.org: go to [python.org/downloads/windows](https://www.python.org/downloads/windows/),
  find the latest **Python 3.12.x** release and download the *Windows installer (64-bit)*.
  During setup, tick **"Add python.exe to PATH"** *only if* you have no other Python installed.

#### Linux

Check with `python3 --version`. If it says 3.11 or older, or 3.15 or newer, install 3.12 next to it:

| Distribution | Command |
|---|---|
| Ubuntu / Mint / Pop!_OS | `sudo apt install python3.12 python3.12-venv` (on older Ubuntu first: `sudo add-apt-repository ppa:deadsnakes/ppa`) |
| Debian | `sudo apt install python3 python3-venv` (Debian 13 ships 3.13; Debian 12 ships 3.11, which is too old: use [pyenv](https://github.com/pyenv/pyenv)) |
| Fedora | `sudo dnf install python3.12` |
| Arch / Manjaro | `yay -S python312`, or use [pyenv](https://github.com/pyenv/pyenv) |

You also need `curl` and `git` (usually already installed).

> You can keep several Python versions side by side; they don't interfere with each other. The
> build scripts automatically pick a supported one (3.12 first), so an existing newer Python is not
> a problem.

### Step 2: Get the code

Either click the green **Code → Download ZIP** button on this page and extract it, or:

```
git clone https://github.com/sevagjb/PrintView3D.git
```

### Step 3: Build

**Windows:** double-click **`build_windows.bat`** in the project folder (or run it from a terminal).
Then run **`install_windows.bat`**. If [Inno Setup 6](https://jrsoftware.org/isinfo.php) is
installed, the build also makes the installer `dist\PrintView3D-Setup.exe`.

**Linux:** in a terminal, in the project folder:

```bash
./build_linux.sh          # makes dist/PrintView3D-x86_64.AppImage
./install_linux.sh        # optional: copy to ~/Applications + add to the applications menu
```

The first build takes a few minutes (it downloads about 300 MB of libraries); later builds are faster.

### What the build script does

```mermaid
flowchart LR
    A["Find a supported Python<br/>(3.12 → 3.13 → 3.14)"] --> B["Create a private<br/>environment (.venv)"]
    B --> C["Install libraries<br/>(Qt, VTK, PyVista, NumPy)"]
    C --> D["Run the tests"]
    D --> E["PyInstaller packs everything<br/>into dist/PrintView3D"]
    E --> F["Windows: zip folder<br/>Linux: AppImage"]
```

1. **Find Python.** It looks for 3.12, then 3.13 and 3.14 (Windows: through the `py`
   launcher; Linux: `python3.12`, `python3.13`, …) and uses the first one it finds. If none is
   installed, it stops and tells you what to install.
2. **Create `.venv`.** A private folder with its own copy of the libraries, so nothing is installed
   into your system Python and nothing else on your PC is affected. Delete `.venv` to start fresh. A `.venv` made earlier by an
   unsupported Python is replaced automatically.
3. **Install libraries** listed in `requirements.txt` (the app) and `requirements-build.txt`
   (PyInstaller and pytest).
4. **Run the tests** in `tests/`. The build stops if any test fails.
5. **Package.** PyInstaller collects Python, the libraries and the app into
   `dist\PrintView3D\PrintView3D.exe` plus an `_internal` folder. That folder is the finished
   program and runs on any Windows 10/11 PC without Python. It is large (several hundred MB),
   mainly because of the VTK 3D engine.
6. **Linux only: AppImage.** `build_linux.sh` downloads
   [appimagetool](https://github.com/AppImage/appimagetool) once and packs `dist/PrintView3D/` into
   the single file `dist/PrintView3D-x86_64.AppImage`. (`--no-appimage` skips this step.)

### Troubleshooting the build

| Problem | Fix |
|---|---|
| `No supported Python version was found` | Install Python 3.12 (Step 1). |
| `Python was not found` / `'py' is not recognized` | Install Python from python.org or with winget (Step 1); both include the `py` launcher. |
| Linux: `Could not create a virtual environment` | Install the venv module, e.g. `sudo apt install python3.12-venv`. |
| Linux: `qt.qpa.plugin: Could not load the Qt platform plugin "xcb"` when running from source | Install Qt's X11 helper: `sudo apt install libxcb-cursor0` (Fedora: `xcb-util-cursor`). The AppImage already includes it. |
| `Cannot install numpy` … `conflicting dependencies` / `ResolutionImpossible` | Your Python is older than 3.12 (an older build script accepted 3.10 and 3.11). Install 3.12 (Step 1) and run the build again; the script replaces the old `.venv` by itself. |
| Build fails while installing `vtk` | You are on an unsupported Python. Install 3.12 and run the build again; the script replaces the old `.venv` by itself. |
| Tests fail | Please [open an issue](../../issues) and paste the output. |
| Windows Defender deletes or blocks the `.exe` | A known false alarm with PyInstaller programs. Allow it in *Windows Security → Protection history*. |

### Developing

```bat
run_from_source.bat                    :: start from the source code, no packaging (Linux: ./run_from_source.sh)
.venv\Scripts\python -m pytest -q      :: run the tests
.venv\Scripts\python tools\make_demo.py         :: regenerate examples\
.venv\Scripts\python tools\make_screenshots.py  :: regenerate the README pictures
```

```
src/printview3d/
  app.py              entry point and command-line options
  loaders/gcode.py    G-code reader (layers, feature types, print info, thumbnails)
  loaders/mesh.py     STL and 3MF readers, STL writer (Export STL)
  slicer.py           list of slicers, detection and launching
  file_assoc.py       "Open with" / default app (assoc_windows.py: registry, assoc_linux.py: freedesktop)
  gpu.py              graphics-card info and high-performance GPU setting
  settings.py         settings file: %APPDATA%\PrintView3D\settings.json
  ui/                 window, 3D scene, camera controls, settings dialog, theme
tests/                automated tests and sample files
tools/                demo-file and screenshot generators
packaging/linux/      AppImage launcher and menu entry
packaging/macos/quicklook/  Finder thumbnails and Quick Look preview (Swift app extensions)
printview3d.spec      PyInstaller recipe (Windows and Linux)
```

**Automatic builds:** every push builds and tests the Windows program on GitHub
([Actions](../../actions)). When the version number in `src/printview3d/__init__.py` changes,
it also publishes a new [release](../../releases) with the Windows zip and the Linux AppImage
attached.

### Command line

```
PrintView3D.exe model.stl                          open a file (in the window already open, if any)
PrintView3D.exe model.stl --new-window             open a file in a new window
PrintView3D.exe part.gcode --screenshot out.png    save a picture and exit
                     [--layer 25] [--view iso|top|front|right]
PrintView3D.exe model.stl --send-to-slicer         open the file in your default slicer and exit
PrintView3D.exe model.stl --send-to-slicer orcaslicer   ...or in a specific one
PrintView3D.exe --lang ar                          start in a language (en, ar, nl, de, fr, es)
PrintView3D.exe --theme light                      start with a theme (auto, dark, gray, graphite, light, ember, ember_dark)
PrintView3D.exe --register                         add to "Open with" (Linux: also the applications menu)
PrintView3D.exe --unregister                       remove file associations
(on Linux use ./PrintView3D-x86_64.AppImage instead of PrintView3D.exe)
```

---

## Translations

| Language | Status |
|---|---|
| English | Source language |
| العربية Arabic | Complete, reviewed by a native speaker |
| Nederlands | Complete, reviewed |
| Deutsch | Complete, needs review by a native speaker |
| Français | Complete, needs review by a native speaker |
| Español | Complete, needs review by a native speaker |
| Română (Romanian) | Complete, reviewed by a native speaker |

**Speak one of these languages? Or want PrintView3D in yours?** Your help is very welcome:
spotting one wrong word already helps. Translations are made right here on GitHub: change the
file for your language in [`translations/`](translations) and open a pull request, all in the
browser. Step by step: **[How to translate](docs/TRANSLATING.md)**.
Untranslated texts simply appear in English, so a language can be added step by step.

![PrintView3D in Arabic, right-to-left](docs/screenshot-arabic.png)

## Contributing

Bug reports, ideas and pull requests are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).
Is your slicer missing? It is usually a single entry in `SLICERS` in
[`src/printview3d/slicer.py`](src/printview3d/slicer.py).

## Notes and limits

- Windows 10/11 and Linux (x86-64) are packaged and tested. The Mac versions (Apple silicon and Intel,
  macOS 14.4+) are in [beta](#macos). ARM Linux (Raspberry Pi etc.) is not packaged yet.
- A 3MF *project* saved in one brand of slicer may lose its printer/print settings when opened in a
  different brand. The model itself loads fine; that's how the slicers behave.
- Binary G-code (`.bgcode`) is not supported yet.
- File Explorer thumbnails are made for 3MF, STL, G-code and FreeCAD files; not yet for OBJ, PLY, OFF and glTF.
  On macOS, Quick Look covers 3MF, STL, G-code, FreeCAD, OBJ and PLY (not STEP, OFF or glTF).
- FreeCAD documents need an installed FreeCAD for the 3D view (PrintView3D does not include
  FreeCAD's geometry engine). Very old or very new FreeCAD versions may not open each other's files.

## Code signing policy

Windows releases are built automatically from this repository by
[GitHub Actions](.github/workflows/build.yml); no binaries are built or uploaded by hand.

*Status: applying for free code signing for open-source projects. When approved:*
Free code signing provided by [SignPath.io](https://about.signpath.io/), certificate by
[SignPath Foundation](https://signpath.org/).

| Role | Members |
|---|---|
| Committers and reviewers | [sevagjb](https://github.com/sevagjb) |
| Approvers | [sevagjb](https://github.com/sevagjb) |

Every signing request is approved by hand by an approver. Contributions from other people are
reviewed before they are merged.

**Privacy:** this program will not transfer any information to other networked systems unless
specifically requested by the user or the person installing or operating it. PrintView3D works
fully offline; it only opens your files and starts the slicer you choose. The only connection it
ever makes is the update check, and only when you ask for it or switched on the daily check;
see [Updates and privacy](#updates-and-privacy).

## License

[MIT](LICENSE). Free to use, change and share.
Built with [Qt for Python](https://doc.qt.io/qtforpython/), [PyVista](https://pyvista.org) and
[VTK](https://vtk.org).

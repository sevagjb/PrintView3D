# Install

You do **not** need Python or anything else to use PrintView3D. Pick your system:

| System | Download | |
|---|---|---|
| **Windows 10 / 11** | `PrintView3D-Setup.exe` (or the portable `PrintView3D-windows.zip`) | [Instructions](#windows) |
| **Linux** (64-bit, x86-64) | `PrintView3D-x86_64.AppImage` | [Instructions](#linux) |
| **macOS 14.4+** (Apple silicon: M1 and newer), beta | `PrintView3D-macOS-AppleSilicon.dmg` | [Instructions](#macos) |
| **macOS 14.4+** (Intel), beta | `PrintView3D-macOS-Intel.dmg` | [Instructions](#macos) |

All downloads are on the **[latest release](https://github.com/sevagjb/PrintView3D/releases/latest)** page.

## Windows

1. Go to the **[latest release](https://github.com/sevagjb/PrintView3D/releases/latest)** and download **`PrintView3D-Setup.exe`**.
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
> SignPath Foundation is being applied for, see [Code signing policy](contribute.md#code-signing-policy)), so
> Windows SmartScreen may warn the first time. Click **More info → Run anyway**. All the source code
> is in this repository, and every release is built automatically by [GitHub Actions](https://github.com/sevagjb/PrintView3D/actions)
> from that code.

**Portable version:** download `PrintView3D-windows.zip`, extract it and run `PrintView3D.exe`.
Nothing is installed. (`install_windows.bat` in the zip still works too.)

### Make it the default program for 3D files (optional)

1. In PrintView3D, click **Settings**.
2. Open the **Files** page and click **Register & choose as default…**.
3. Windows Settings opens. Pick **PrintView3D** for `.stl`, `.3mf` and `.gcode`.

Windows requires you to confirm this last step yourself; no program is allowed to do it silently.
**Remove registration** in the same place undoes everything.

### Uninstall

**Windows Settings → Apps → Installed apps → PrintView3D → Uninstall**. This removes the program,
its shortcuts and file associations, and asks whether to delete your settings too.
(Portable version: run `uninstall_windows.bat` from the extracted folder.)

## Linux

PrintView3D for Linux is a single **AppImage** file: it contains everything it needs and runs on
most distributions without installing packages: Ubuntu 22.04 or newer, Linux Mint 21+, Debian 12+,
Fedora 36+, openSUSE Tumbleweed, Arch, Manjaro, Pop!_OS, elementary OS, Zorin OS and others.

1. Download **`PrintView3D-x86_64.AppImage`** from the **[latest release](https://github.com/sevagjb/PrintView3D/releases/latest)**.
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

(The two scripts are in the [source code](https://github.com/sevagjb/PrintView3D/archive/refs/heads/main.zip).)

**Slicers on Linux** are found automatically when installed as an AppImage (in `~/Applications`,
`~/Downloads`, `~/Desktop`, `~/bin`, `/opt`…), as a **Flatpak** or **Snap**, from your
distribution's packages, or in `/opt`. Otherwise choose it once with **Browse…** in Settings.

<details markdown>
<summary><b>Linux troubleshooting</b></summary>

| Problem | Fix |
|---|---|
| Nothing happens / "AppImages require FUSE" | Install FUSE: `sudo apt install libfuse2` (Ubuntu/Debian), `sudo dnf install fuse fuse-libs` (Fedora). Or run it without FUSE: `./PrintView3D-x86_64.AppImage --appimage-extract-and-run` |
| `GLIBC_2.35 not found` | Your distribution is older than Ubuntu 22.04 / Debian 12. Build from source instead (below). |
| Window opens but the 3D view stays black | Make sure your graphics driver is installed (Mesa or the NVIDIA driver). In a virtual machine, enable 3D acceleration. |
| Wayland desktop | Supported. PrintView3D automatically runs through XWayland, because the 3D view needs it. |
| Slow rotation on a laptop with two GPUs | Start PrintView3D from the applications menu after **Register** (the menu entry asks for the dedicated GPU), or use your desktop's *Launch using Dedicated Graphics Card* option. |

</details>

## macOS

> **Beta.** The Mac version is built and checked automatically, but has not been tried by many people
> on real Macs yet. Please [tell us how it works](https://github.com/sevagjb/PrintView3D/issues/new?template=mac_build.md): your Mac
> model, macOS version, and anything that looks wrong.

For **macOS 14.4 (Sonoma) or newer**, in two versions; pick the one for your Mac
(Apple menu → **About This Mac**: *Chip* means Apple silicon, *Processor* means Intel):

| Your Mac | Download |
|---|---|
| **Apple silicon** (M1, M2, M3, M4 and newer) | `PrintView3D-macOS-AppleSilicon.dmg` |
| **Intel** (2018 and newer, the Macs that run macOS 14) | `PrintView3D-macOS-Intel.dmg` |

1. From the **[latest release](https://github.com/sevagjb/PrintView3D/releases/latest)** download the `.dmg` for your Mac.
2. Open it and drag **PrintView3D** onto **Applications**.
3. Start PrintView3D from Applications. **The first time**, macOS says it *cannot verify* the app.
   Click **Done** (not "Move to Trash").
4. Open **System Settings → Privacy & Security**, scroll down to *Security* and click
   **Open Anyway** next to PrintView3D. Confirm with your password or Touch ID.

From then on it opens normally.

> **Why this extra step?** Apple only skips it for apps from developers who pay Apple every year
> for a certificate and "notarization". PrintView3D is free and has no budget for that, so it is
> signed without an Apple account instead. The program is the same open-source code as on Windows
> and Linux, built automatically by [GitHub Actions](https://github.com/sevagjb/PrintView3D/actions). (Right-click → Open no longer
> works for this on macOS 15 and newer; use Open Anyway as above.)

**Open files with PrintView3D:** in Finder, right-click a `.stl`, `.3mf`, `.gcode` or `.FCStd` file →
**Open With → PrintView3D**. To make it the default: right-click the file → **Get Info** →
*Open with:* **PrintView3D** → **Change All…**.

**Slicers** in Applications (Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer, Cura, …) are
found automatically. **Updates:** *Download update* opens the release page; drag the new version
into Applications to replace the old one. Older Macs that can't run macOS 14:
[let us know](https://github.com/sevagjb/PrintView3D/issues/new?template=mac_build.md) if you need a version for them.


### Quick Look (Finder previews) {#quick-look}

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

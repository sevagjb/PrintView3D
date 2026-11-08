#!/usr/bin/env bash
# ============================================================
#  PrintView3D - build the Linux program (AppImage)
#  Requires Python 3.12-3.14 (3.12 recommended) with the venv module.
#  Result: dist/PrintView3D-x86_64.AppImage
#  Options: --no-appimage   only build the folder dist/PrintView3D/
# ============================================================
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

MAKE_APPIMAGE=1
[[ "${1:-}" == "--no-appimage" ]] && MAKE_APPIMAGE=0

# Pick a supported Python explicitly instead of whatever "python3" happens to be.
# 3.12 is the oldest: the exact library versions the releases are built with
# (requirements-build-lock.txt, e.g. NumPy 2.5) need it. 3.14 is the newest:
# the 3D engine (VTK) has no version for 3.15 yet.
SUPPORTED='import sys; sys.exit(0 if (3,12) <= sys.version_info[:2] <= (3,14) else 1)'
PY=""
for v in 3.12 3.13 3.14; do
    if command -v "python$v" >/dev/null 2>&1; then PY="python$v"; break; fi
done
if [[ -z "$PY" ]] && command -v python3 >/dev/null 2>&1; then
    if python3 -c "$SUPPORTED"; then
        PY=python3
    fi
fi
if [[ -z "$PY" ]]; then
    echo "[ERROR] No supported Python version was found."
    echo "        Building PrintView3D needs Python 3.12 to 3.14 (3.12 recommended)."
    echo "        Older versions such as 3.11 are too old for the libraries it is built with,"
    echo "        newer versions such as 3.15 are not supported yet by the VTK 3D engine."
    echo "        Ubuntu/Debian: sudo apt install python3.12 python3.12-venv"
    echo "        Fedora:        sudo dnf install python3.12"
    echo "        Arch:          use pyenv or the python312 AUR package"
    exit 1
fi
echo "Using Python: $PY ($($PY --version))"

echo "[1/5] Creating virtual environment (.venv) ..."
# A .venv made earlier by an unsupported Python (or one that was removed since)
# would make step 2 fail, so make a new one.
if [[ -e .venv ]] && ! .venv/bin/python -c "$SUPPORTED" >/dev/null 2>&1; then
    echo "      The existing .venv uses an unsupported Python - making a new one."
    rm -rf .venv
fi
if [[ ! -x .venv/bin/python ]]; then
    "$PY" -m venv .venv || {
        echo "[ERROR] Could not create a virtual environment."
        echo "        Ubuntu/Debian: sudo apt install ${PY}-venv"
        exit 1
    }
fi

echo "[2/5] Installing dependencies (first time takes a few minutes) ..."
.venv/bin/python -m pip install --upgrade pip >/dev/null
.venv/bin/python -m pip install -r requirements.txt -r requirements-build.txt -c requirements-build-lock.txt

echo "[3/5] Building translations and running tests ..."
.venv/bin/python tools/i18n.py compile
.venv/bin/python tests/make_samples.py >/dev/null
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests

echo "[4/5] Building the program ..."
.venv/bin/pyinstaller --noconfirm --clean printview3d.spec

if [[ "$MAKE_APPIMAGE" == 0 ]]; then
    echo "Done: dist/PrintView3D/PrintView3D"
    exit 0
fi

echo "[5/5] Packing the AppImage ..."
ARCH="$(uname -m)"
TOOL="build/appimagetool-$ARCH.AppImage"
# appimagetool: a fixed version (the same tool on every build). GitHub's release downloads sometimes
# answer "504 Gateway Timeout" for minutes at a time (November 2026, the 0.30.0 release), so this
# tries for a few minutes, switching between the fixed version and the "continuous" build. In CI
# the tool is also kept in GitHub's cache (build.yml), so most builds don't download it at all.
APPIMAGETOOL_VERSION="${APPIMAGETOOL_VERSION:-1.9.0}"
if [[ ! -x "$TOOL" ]]; then
    mkdir -p build
    BASE="https://github.com/AppImage/appimagetool/releases/download"
    ok=0
    for round in 1 2 3 4; do
        for tag in "$APPIMAGETOOL_VERSION" continuous; do
            if curl -fsSL --retry 3 --retry-delay 15 --retry-all-errors -o "$TOOL.part" \
                    "$BASE/$tag/appimagetool-$ARCH.AppImage"; then
                mv "$TOOL.part" "$TOOL"
                ok=1
                echo "appimagetool: $tag"
                break 2
            fi
            echo "appimagetool $tag: not available right now (round $round of 4)"
        done
        sleep 20
    done
    rm -f "$TOOL.part"
    if [[ $ok != 1 ]]; then
        echo "Could not download appimagetool from GitHub. Try again later." >&2
        exit 1
    fi
    chmod +x "$TOOL"
fi
APPDIR=build/AppDir
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib"
cp -a dist/PrintView3D "$APPDIR/usr/lib/printview3d"
cp packaging/linux/AppRun "$APPDIR/AppRun"
cp packaging/linux/printview3d.desktop "$APPDIR/printview3d.desktop"
cp src/printview3d/resources/icon.png "$APPDIR/printview3d.png"
cp src/printview3d/resources/icon.png "$APPDIR/.DirIcon"
OUT="dist/PrintView3D-$ARCH.AppImage"
# Update information, so AppImageUpdate and similar tools can update the AppImage from the newest
# GitHub release. appimagetool also writes PrintView3D-$ARCH.AppImage.zsync (into the current
# folder); it is published next to the AppImage. A fork can point it elsewhere:
# UPDATE_INFO="gh-releases-zsync|user|repo|latest|PrintView3D-*$ARCH.AppImage.zsync" ./build_linux.sh
UPDATE_INFO="${UPDATE_INFO:-gh-releases-zsync|sevagjb|PrintView3D|latest|PrintView3D-$ARCH.AppImage.zsync}"
ZSYNC="PrintView3D-$ARCH.AppImage.zsync"
rm -f "$ZSYNC" "dist/$ZSYNC"
# APPIMAGE_EXTRACT_AND_RUN: works on machines without FUSE (containers, CI)
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$TOOL" --no-appstream -u "$UPDATE_INFO" "$APPDIR" "$OUT"
chmod +x "$OUT"
if [[ -f "$ZSYNC" ]]; then
    mv "$ZSYNC" "dist/$ZSYNC"
else
    echo "[WARNING] No $ZSYNC was made; the AppImage still works, but cannot update itself."
fi

echo
echo "============================================================"
echo " Done!  $OUT"
echo " Run ./install_linux.sh to add it to your applications menu."
echo "============================================================"

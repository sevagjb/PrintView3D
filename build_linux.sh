#!/usr/bin/env bash
# ============================================================
#  PrintView3D - build the Linux program (AppImage)
#  Requires Python 3.10-3.14 (3.12 recommended) with the venv module.
#  Result: dist/PrintView3D-x86_64.AppImage
#  Options: --no-appimage   only build the folder dist/PrintView3D/
# ============================================================
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

MAKE_APPIMAGE=1
[[ "${1:-}" == "--no-appimage" ]] && MAKE_APPIMAGE=0

# The 3D engine (VTK) only supports certain Python versions, so pick one of
# those explicitly instead of whatever "python3" happens to be.
PY=""
for v in 3.12 3.13 3.14 3.11 3.10; do
    if command -v "python$v" >/dev/null 2>&1; then PY="python$v"; break; fi
done
if [[ -z "$PY" ]] && command -v python3 >/dev/null 2>&1; then
    if python3 -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)'; then
        PY=python3
    fi
fi
if [[ -z "$PY" ]]; then
    echo "[ERROR] No supported Python version was found."
    echo "        PrintView3D needs Python 3.10 to 3.14 (3.12 recommended)."
    echo "        Ubuntu/Debian: sudo apt install python3.12 python3.12-venv"
    echo "        Fedora:        sudo dnf install python3.12"
    echo "        Arch:          use pyenv or the python312 AUR package"
    exit 1
fi
echo "Using Python: $PY ($($PY --version))"

echo "[1/5] Creating virtual environment (.venv) ..."
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
if [[ ! -x "$TOOL" ]]; then
    mkdir -p build
    curl -fL -o "$TOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
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

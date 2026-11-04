#!/bin/bash
# Builds PrintView3D's two Quick Look extensions for macOS, and their test program:
#   out/PrintView3DThumbnail.appex  - Finder icons (thumbnails)
#   out/PrintView3DPreview.appex    - the space-bar preview
#   out/ql_test                     - tests the same code without Quick Look (see Test/main.swift)
# They go into PrintView3D.app/Contents/PlugIns (see .github/workflows/build.yml), and must be
# signed there with QuickLook.entitlements (Quick Look extensions have to run sandboxed).
#
# Needs only the Xcode command line tools (no Xcode project, no Apple account). Run on a Mac:
#   packaging/macos/quicklook/build.sh <version> [arm64|x86_64]
# The pictures and STL drawing come from the same C++ code as the Windows thumbnails
# (packaging/windows/thumbnails/thumbcore.cpp).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
core="$here/../../windows/thumbnails"
version="${1:-dev}"
arch="${2:-$(uname -m)}"
target="$arch-apple-macos14.4"        # the same oldest macOS as PrintView3D.app
out="$here/out"
rm -rf "$out"
mkdir -p "$out/obj"

echo "Building the Quick Look extensions $version for $target"
cflags=(-target "$target" -O2 -fapplication-extension -Wall -I"$core" -I"$here/bridge")
clang "${cflags[@]}" -c "$core/tinf/tinflate.c" -o "$out/obj/tinflate.o"
clang++ "${cflags[@]}" -std=c++17 -c "$core/thumbcore.cpp" -o "$out/obj/thumbcore.o"
clang++ "${cflags[@]}" -std=c++17 -c "$here/bridge/pv3d_bridge.cpp" -o "$out/obj/pv3d_bridge.o"
objs=("$out/obj/tinflate.o" "$out/obj/thumbcore.o" "$out/obj/pv3d_bridge.o")
shared=("$here"/Shared/*.swift)
swiftflags=(-target "$target" -O -swift-version 5 -import-objc-header "$here/bridge/pv3d_bridge.h" -lc++)

# An app extension is a bundle whose program starts in Foundation's NSExtensionMain.
make_appex() {
    local name="$1" module="$2" dir="$3"; shift 3
    local appex="$out/$name.appex"
    mkdir -p "$appex/Contents/MacOS"
    swiftc "${swiftflags[@]}" -application-extension -parse-as-library -module-name "$module" \
        "${shared[@]}" "$here/$dir"/*.swift "${objs[@]}" "$@" \
        -Xlinker -e -Xlinker _NSExtensionMain -o "$appex/Contents/MacOS/$name"
    sed "s/@VERSION@/$version/g" "$here/$dir/Info.plist" > "$appex/Contents/Info.plist"
    plutil -lint "$appex/Contents/Info.plist"
    echo "Built $appex"
}

make_appex PrintView3DThumbnail PV3DThumbnail Thumbnail -framework QuickLookThumbnailing -framework AppKit
make_appex PrintView3DPreview PV3DPreview Preview -framework Quartz -framework SceneKit -framework AppKit

swiftc "${swiftflags[@]}" -module-name ql_test "${shared[@]}" "$here/Test/main.swift" "${objs[@]}" -o "$out/ql_test"
echo "Built $out/ql_test"

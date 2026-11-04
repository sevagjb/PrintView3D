// Test for the Quick Look code (run by GitHub Actions on both kinds of Mac):
//   ql_test <out-folder> <file>...
// Uses exactly the code of the two extensions (Shared/), without Quick Look itself:
//   - every file must give a thumbnail with visible pixels (saved as <out>/<name>.png),
//   - every model file must give triangles (count and size are printed),
//   - cut-off and scrambled copies of every file must not crash anything.

import CoreGraphics
import Foundation
import ImageIO

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: ql_test <out-folder> <file>...\n".data(using: .utf8)!)
    exit(2)
}
let outDir = URL(fileURLWithPath: args[1], isDirectory: true)
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
var failed = 0

func visiblePixels(_ img: CGImage) -> Int {
    let w = img.width, h = img.height
    var buf = [UInt8](repeating: 0, count: w * h * 4)
    let ok = buf.withUnsafeMutableBytes { raw -> Bool in
        guard let ctx = CGContext(data: raw.baseAddress, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                                  space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
        ctx.draw(img, in: CGRect(x: 0, y: 0, width: w, height: h))
        return true
    }
    guard ok else { return 0 }
    var n = 0
    var i = 3
    while i < buf.count { if buf[i] > 0 { n += 1 }; i += 4 }
    return n
}

func savePNG(_ img: CGImage, _ url: URL) {
    guard let dest = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else { return }
    CGImageDestinationAddImage(dest, img, nil)
    CGImageDestinationFinalize(dest)
}

for path in args[2...] {
    let url = URL(fileURLWithPath: path)
    let name = url.lastPathComponent
    guard let kind = PV3DKind(url: url), let file = MappedFile(url: url) else {
        print("FAIL \(name): not a supported file"); failed += 1; continue
    }
    let t0 = Date()
    if let img = Pictures.thumbnail(url: url, maxPixels: 256) {
        let vis = visiblePixels(img)
        savePNG(img, outDir.appendingPathComponent(name + ".png"))
        let ms = Int(Date().timeIntervalSince(t0) * 1000)
        if vis < 50 { print("FAIL \(name): thumbnail \(img.width)x\(img.height) is empty"); failed += 1 }
        else { print("ok   \(name): thumbnail \(img.width)x\(img.height), \(vis) visible pixels, \(ms) ms") }
    } else {
        print("FAIL \(name): no thumbnail"); failed += 1
    }
    if kind.hasMesh {
        if let m = MeshLoader.load(url: url, kind: kind, file: file), let b = m.bounds() {
            let s = b.max - b.min
            print(String(format: "ok   %@: %ld triangles, %.1f x %.1f x %.1f mm", name, m.triangleCount, s.x, s.y, s.z))
            // The preview's 3D image is the same model; draw it once as well.
            if let r = Pictures.render(m, px: 256) { savePNG(r, outDir.appendingPathComponent(name + ".model.png")) }
        } else {
            print("FAIL \(name): no 3D model"); failed += 1
        }
    }
    // Broken copies: cut off at many places, and with scrambled bytes. Only "no crash" counts.
    var bytes = [UInt8](file.data)
    let tmp = outDir.appendingPathComponent("broken." + url.pathExtension)
    let cuts = stride(from: 0, to: bytes.count, by: max(1, bytes.count / 25))
    for cut in cuts {
        try? Data(bytes[0..<cut]).write(to: tmp)
        _ = Pictures.thumbnail(url: tmp, maxPixels: 128)
        if let f = MappedFile(url: tmp) { _ = MeshLoader.load(url: tmp, kind: kind, file: f) }
    }
    var rng = SystemRandomNumberGenerator()
    for _ in 0..<5 {
        for _ in 0..<max(1, bytes.count / 200) { bytes[Int.random(in: 0..<bytes.count, using: &rng)] = UInt8.random(in: 0...255, using: &rng) }
        try? Data(bytes).write(to: tmp)
        _ = Pictures.thumbnail(url: tmp, maxPixels: 128)
        if let f = MappedFile(url: tmp) { _ = MeshLoader.load(url: tmp, kind: kind, file: f) }
    }
    try? FileManager.default.removeItem(at: tmp)
    print("ok   \(name): broken copies handled")
}

print(failed == 0 ? "All Quick Look tests passed" : "\(failed) Quick Look test(s) failed")
exit(failed == 0 ? 0 : 1)

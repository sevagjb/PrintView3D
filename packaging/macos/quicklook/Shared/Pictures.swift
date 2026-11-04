// PrintView3D Quick Look - pictures: the one saved in the file, or the model drawn by the
// same C++ code as the Windows thumbnails (seen from the front-left above, model blue).

import CoreGraphics
import Foundation
import ImageIO

enum Pictures {
    /// PNG / JPEG bytes as an image, at most maxPixels on its longer side (nil: full size).
    static func decode(_ data: Data, maxPixels: Int?) -> CGImage? {
        guard let src = CGImageSourceCreateWithData(data as CFData, nil) else { return nil }
        guard let maxPixels = maxPixels else { return CGImageSourceCreateImageAtIndex(src, 0, nil) }
        let opts: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceThumbnailMaxPixelSize: max(16, maxPixels),
        ]
        return CGImageSourceCreateThumbnailAtIndex(src, 0, opts as CFDictionary)
    }

    /// px x px RGBA pixels (not premultiplied) from the C++ core as an image.
    static func image(rgba: Data, px: Int) -> CGImage? {
        guard rgba.count == px * px * 4, let provider = CGDataProvider(data: rgba as CFData),
              let space = CGColorSpace(name: CGColorSpace.sRGB) else { return nil }
        return CGImage(width: px, height: px, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: px * 4,
                       space: space, bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.last.rawValue),
                       provider: provider, decode: nil, shouldInterpolate: true, intent: .defaultIntent)
    }

    static func render(_ mesh: Mesh, px: Int) -> CGImage? {
        return mesh.xyz.withUnsafeBufferPointer { b -> CGImage? in
            var out = pv3d_buffer(data: nil, size: 0)
            guard pv3d_render_triangles(b.baseAddress, mesh.triangleCount, Int32(px), &out) == 1,
                  let d = takeData(out) else { return nil }
            return image(rgba: d, px: px)
        }
    }

    /// The Finder thumbnail of a file, at most maxPixels on its longer side.
    /// 3MF / FreeCAD / G-code: the picture saved by the slicer or FreeCAD; a 3MF without one and
    /// STL / OBJ / PLY: the model drawn.
    static func thumbnail(url: URL, maxPixels: Int) -> CGImage? {
        guard let kind = PV3DKind(url: url), let file = MappedFile(url: url) else { return nil }
        let px = min(max(maxPixels, 64), 1024)
        if let pic = file.embeddedPicture(kind), let img = decode(pic, maxPixels: maxPixels) {
            return img
        }
        switch kind {
        case .stl:
            return file.renderSTL(px: px).flatMap { image(rgba: $0, px: px) }
        case .threeMF, .obj, .ply:
            return MeshLoader.load(url: url, kind: kind, file: file).flatMap { render($0, px: px) }
        case .gcode, .freecad:
            return nil
        }
    }
}

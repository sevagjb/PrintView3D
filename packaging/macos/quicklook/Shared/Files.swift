// PrintView3D Quick Look - shared by the thumbnail and the preview extension (and ql_test).
// What kind of file it is, and reading it through the C++ core (pv3d_bridge.h).

import Foundation

enum PV3DKind {
    case stl, threeMF, gcode, freecad, obj, ply

    init?(url: URL) {
        switch url.pathExtension.lowercased() {
        case "stl": self = .stl
        case "3mf": self = .threeMF
        case "gcode", "gco", "g": self = .gcode
        case "fcstd": self = .freecad
        case "obj": self = .obj
        case "ply": self = .ply
        default: return nil
        }
    }

    /// Files that hold a 3D model (not only a picture).
    var hasMesh: Bool {
        switch self {
        case .stl, .threeMF, .obj, .ply: return true
        case .gcode, .freecad: return false
        }
    }
}

enum PV3DError: LocalizedError {
    case unsupported, unreadable

    var errorDescription: String? {
        switch self {
        case .unsupported: return "PrintView3D can't show this kind of file in Quick Look."
        case .unreadable: return "PrintView3D could not read this file."
        }
    }
}

/// The file mapped into memory (not read: a 300 MB STL costs no memory until it is used).
final class MappedFile {
    let data: Data

    init?(url: URL) {
        guard let d = try? Data(contentsOf: url, options: .alwaysMapped), !d.isEmpty else { return nil }
        data = d
    }

    func withBytes<T>(_ body: (UnsafePointer<UInt8>, Int) -> T?) -> T? {
        return data.withUnsafeBytes { raw -> T? in
            guard let p = raw.bindMemory(to: UInt8.self).baseAddress, raw.count > 0 else { return nil }
            return body(p, raw.count)
        }
    }
}

/// Takes over a buffer filled by the C++ core.
func takeData(_ buf: pv3d_buffer) -> Data? {
    guard let p = buf.data, buf.size > 0 else { return nil }
    return Data(bytesNoCopy: p, count: buf.size, deallocator: .free)
}

func takeFloats(_ buf: pv3d_buffer) -> [Float]? {
    var b = buf
    guard let p = b.data, b.size >= MemoryLayout<Float>.size else {
        pv3d_buffer_free(&b)
        return nil
    }
    let floats = Array(UnsafeBufferPointer(start: p.assumingMemoryBound(to: Float.self),
                                           count: b.size / MemoryLayout<Float>.size))
    pv3d_buffer_free(&b)
    return floats
}

extension MappedFile {
    /// The preview picture saved in a 3MF, FreeCAD or G-code file (PNG / JPEG bytes).
    func embeddedPicture(_ kind: PV3DKind) -> Data? {
        return withBytes { p, n -> Data? in
            var out = pv3d_buffer(data: nil, size: 0)
            let ok: Int32
            switch kind {
            case .threeMF, .freecad: ok = pv3d_zip_picture(p, n, &out)
            case .gcode: ok = pv3d_gcode_picture(p, n, &out)
            default: return nil
            }
            return ok == 1 ? takeData(out) : nil
        }
    }

    /// The names of the files inside a zip (3MF).
    func zipNames() -> [String] {
        return withBytes { p, n -> [String] in
            var out = pv3d_buffer(data: nil, size: 0)
            guard pv3d_zip_names(p, n, &out) == 1, let d = takeData(out) else { return [] }
            return String(decoding: d, as: UTF8.self).split(separator: "\n").map(String.init)
        } ?? []
    }

    /// One file from inside a zip (3MF).
    func zipRead(_ name: String, maxBytes: UInt64) -> Data? {
        return withBytes { p, n -> Data? in
            var out = pv3d_buffer(data: nil, size: 0)
            let ok = name.withCString { pv3d_zip_read(p, n, $0, maxBytes, &out) }
            return ok == 1 ? takeData(out) : nil
        }
    }

    func stlTriangles() -> [Float]? {
        return withBytes { p, n -> [Float]? in
            var out = pv3d_buffer(data: nil, size: 0)
            guard pv3d_stl_triangles(p, n, &out) == 1 else { return nil }
            return takeFloats(out)
        }
    }

    /// An STL drawn into px x px RGBA pixels.
    func renderSTL(px: Int) -> Data? {
        return withBytes { p, n -> Data? in
            var out = pv3d_buffer(data: nil, size: 0)
            return pv3d_render_stl(p, n, Int32(px), &out) == 1 ? takeData(out) : nil
        }
    }
}

// PrintView3D Quick Look - the 3D model of a file as plain triangles, in millimetres, Z up
// (as PrintView3D and slicers show it).

import Foundation
import ModelIO
import simd

struct Mesh {
    /// 9 floats per triangle: x, y, z of the three corners.
    var xyz: [Float]

    var triangleCount: Int { xyz.count / 9 }

    /// Smallest and largest corner, ignoring broken (NaN / infinite) numbers.
    func bounds() -> (min: SIMD3<Float>, max: SIMD3<Float>)? {
        var lo = SIMD3<Float>(repeating: .greatestFiniteMagnitude)
        var hi = SIMD3<Float>(repeating: -.greatestFiniteMagnitude)
        var any = false
        var i = 0
        while i + 2 < xyz.count {
            let v = SIMD3<Float>(xyz[i], xyz[i + 1], xyz[i + 2])
            if v.x.isFinite && v.y.isFinite && v.z.isFinite {
                lo = simd_min(lo, v)
                hi = simd_max(hi, v)
                any = true
            }
            i += 3
        }
        return any ? (lo, hi) : nil
    }

    /// At most `limit` triangles (every n-th one is kept), so a huge model stays quick.
    func thinned(to limit: Int) -> Mesh {
        let n = triangleCount
        guard n > limit, limit > 0 else { return self }
        let step = (n + limit - 1) / limit
        var out = [Float]()
        out.reserveCapacity((n / step + 1) * 9)
        var t = 0
        while t < n {
            out.append(contentsOf: xyz[(t * 9)..<(t * 9 + 9)])
            t += step
        }
        return Mesh(xyz: out)
    }
}

enum MeshLoader {
    /// Like the Windows thumbnails: at most 4 million triangles are read.
    static let maxTriangles = 4_000_000

    static func load(url: URL, kind: PV3DKind, file: MappedFile) -> Mesh? {
        let mesh: Mesh?
        switch kind {
        case .stl: mesh = file.stlTriangles().map { Mesh(xyz: $0) }
        case .threeMF: mesh = ThreeMFReader(file: file).read()
        case .obj, .ply: mesh = loadWithModelIO(url: url)
        case .gcode, .freecad: mesh = nil
        }
        guard let m = mesh, m.triangleCount > 0, m.bounds() != nil else { return nil }
        return m
    }

    /// OBJ and PLY through Apple's Model I/O (it also splits polygons into triangles).
    static func loadWithModelIO(url: URL) -> Mesh? {
        let asset = MDLAsset(url: url, vertexDescriptor: nil, bufferAllocator: nil,
                             preserveTopology: false, error: nil)
        guard let meshes = asset.childObjects(of: MDLMesh.self) as? [MDLMesh] else { return nil }
        var out = [Float]()
        for mesh in meshes {
            guard let pos = mesh.vertexAttributeData(forAttributeNamed: MDLVertexAttributePosition,
                                                     as: .float3) else { continue }
            let count = mesh.vertexCount
            let base = pos.dataStart
            let stride = pos.stride
            guard stride >= 12, count > 0 else { continue }
            let world = MDLTransform.globalTransform(with: mesh, atTime: 0)
            func vertex(_ i: Int) -> SIMD3<Float> {
                let p = (base + i * stride).assumingMemoryBound(to: Float.self)
                let v = world * SIMD4<Float>(p[0], p[1], p[2], 1)
                return SIMD3<Float>(v.x, v.y, v.z)
            }
            for case let sub as MDLSubmesh in mesh.submeshes ?? [] {
                guard sub.geometryType == .triangles else { continue }
                let map = sub.indexBuffer.map()
                let bytes = map.bytes
                let n = sub.indexCount - sub.indexCount % 3
                func index(_ k: Int) -> Int {
                    switch sub.indexType {
                    case .uInt8: return Int(bytes.load(fromByteOffset: k, as: UInt8.self))
                    case .uInt16: return Int(bytes.load(fromByteOffset: k * 2, as: UInt16.self))
                    default: return Int(bytes.load(fromByteOffset: k * 4, as: UInt32.self))
                    }
                }
                var k = 0
                while k < n {
                    let a = index(k), b = index(k + 1), c = index(k + 2)
                    k += 3
                    guard a < count, b < count, c < count else { continue }
                    for v in [vertex(a), vertex(b), vertex(c)] {
                        out.append(v.x); out.append(v.y); out.append(v.z)
                    }
                    if out.count >= maxTriangles * 9 { return Mesh(xyz: out) }
                }
            }
        }
        return out.isEmpty ? nil : Mesh(xyz: out)
    }
}

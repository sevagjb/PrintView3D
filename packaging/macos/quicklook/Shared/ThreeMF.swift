// PrintView3D Quick Look - the 3D model of a 3MF file, read the same way as PrintView3D
// (src/printview3d/loaders/mesh.py): every build item with its components, including those
// in other model files of the project (the production extension's "path"), placed on the
// plate with their transforms, in millimetres. Like the viewer, everything is shown.

import Foundation
import simd

final class ThreeMFReader {
    /// A model file inside the 3MF can be large; at most this much is read.
    static let maxModelBytes: UInt64 = 300 << 20
    static let unitScale: [String: Float] = [
        "micron": 0.001, "millimeter": 1, "centimeter": 10, "inch": 25.4, "foot": 304.8, "meter": 1000,
    ]

    struct Component { let objectID: String; let path: String?; let matrix: simd_float4x4 }
    final class Object {
        var vertices = [Float]()
        var triangles = [UInt32]()
        var components = [Component]()
    }
    struct Part { var objects: [String: Object]; var items: [Component]; var scale: Float }

    private let file: MappedFile
    private var lowerNames = [String: String]()
    private var parts = [String: Part]()
    private var out = [Float]()
    private var full = false

    init(file: MappedFile) {
        self.file = file
        for n in file.zipNames() { lowerNames[n.lowercased()] = n }
    }

    func read() -> Mesh? {
        guard let root = rootModelPath(), let main = part(root) else { return nil }
        var items = main.items
        if items.isEmpty {   // some exporters leave out <build>: show every object
            items = main.objects.keys.sorted().map { Component(objectID: $0, path: nil, matrix: matrix_identity_float4x4) }
        }
        for item in items where !full {
            collect(path: item.path ?? root, id: item.objectID, matrix: item.matrix, depth: 0)
        }
        return out.isEmpty ? nil : Mesh(xyz: out)
    }

    // MARK: - parts

    private static func norm(_ p: String) -> String {
        var s = Substring(p)
        while s.first == "/" { s = s.dropFirst() }
        return String(s)
    }

    private func rootModelPath() -> String? {
        if let rels = file.zipRead("_rels/.rels", maxBytes: 1 << 20) {
            let finder = RelsParser()
            let parser = XMLParser(data: rels)
            parser.delegate = finder
            parser.parse()
            if let t = finder.target { return Self.norm(t) }
        }
        return lowerNames.keys.sorted().first { $0.hasPrefix("3d/") && $0.hasSuffix(".model") }
            .flatMap { lowerNames[$0] }
    }

    private func part(_ path: String) -> Part? {
        let key = Self.norm(path).lowercased()
        if let p = parts[key] { return p }
        let real = lowerNames[key] ?? Self.norm(path)
        guard let data = file.zipRead(real, maxBytes: Self.maxModelBytes) else { return nil }
        let reader = ModelParser()
        let parser = XMLParser(data: data)
        parser.delegate = reader
        parser.shouldProcessNamespaces = false
        parser.parse()   // a broken end keeps what was read before it
        let p = Part(objects: reader.objects, items: reader.items,
                     scale: Self.unitScale[reader.unit] ?? 1)
        parts[key] = p
        return p
    }

    private func collect(path: String, id: String, matrix: simd_float4x4, depth: Int) {
        guard depth <= 16, !full, let p = part(path), let obj = p.objects[id] else { return }
        let vcount = obj.vertices.count / 3
        var t = 0
        while t + 2 < obj.triangles.count {
            let a = Int(obj.triangles[t]), b = Int(obj.triangles[t + 1]), c = Int(obj.triangles[t + 2])
            t += 3
            guard a < vcount, b < vcount, c < vcount else { continue }
            for i in [a, b, c] {
                let v = matrix * SIMD4<Float>(obj.vertices[i * 3] * p.scale, obj.vertices[i * 3 + 1] * p.scale,
                                              obj.vertices[i * 3 + 2] * p.scale, 1)
                out.append(v.x); out.append(v.y); out.append(v.z)
            }
            if out.count >= MeshLoader.maxTriangles * 9 { full = true; return }
        }
        for comp in obj.components {
            // 3MF uses row vectors: a component inside a placed object is placed by
            // (component transform) then (the object's placement).
            collect(path: comp.path ?? path, id: comp.objectID, matrix: matrix * comp.matrix, depth: depth + 1)
        }
    }

    // MARK: - XML

    static func localName(_ name: String) -> String {
        if let i = name.lastIndex(of: ":") { return String(name[name.index(after: i)...]) }
        return name
    }

    /// "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32" (row vectors) as a column-vector matrix.
    static func transform(_ s: String?) -> simd_float4x4 {
        guard let s = s else { return matrix_identity_float4x4 }
        let v = s.split(whereSeparator: { $0 == " " || $0 == "\t" || $0 == "\n" || $0 == "\r" }).compactMap { Float($0) }
        guard v.count == 12, v.allSatisfy({ $0.isFinite }) else { return matrix_identity_float4x4 }
        return simd_float4x4(columns: (SIMD4(v[0], v[1], v[2], 0), SIMD4(v[3], v[4], v[5], 0),
                                       SIMD4(v[6], v[7], v[8], 0), SIMD4(v[9], v[10], v[11], 1)))
    }

    static func pathAttribute(_ attrs: [String: String]) -> String? {
        for (k, v) in attrs where localName(k) == "path" && k.contains(":") { return v }
        return nil
    }

    private final class RelsParser: NSObject, XMLParserDelegate {
        var target: String?
        func parser(_ parser: XMLParser, didStartElement name: String, namespaceURI: String?,
                    qualifiedName: String?, attributes: [String: String] = [:]) {
            if target == nil, ThreeMFReader.localName(name) == "Relationship",
               (attributes["Type"] ?? "").hasSuffix("/3dmodel"), let t = attributes["Target"] {
                target = t
            }
        }
    }

    private final class ModelParser: NSObject, XMLParserDelegate {
        var objects = [String: Object]()
        var items = [Component]()
        var unit = "millimeter"
        private var current: Object?
        private var inBuild = false
        private var triangles = 0

        func parser(_ parser: XMLParser, didStartElement name: String, namespaceURI: String?,
                    qualifiedName: String?, attributes a: [String: String] = [:]) {
            switch ThreeMFReader.localName(name) {
            case "vertex":
                guard let o = current else { return }
                o.vertices.append(Float(a["x"] ?? "") ?? 0)
                o.vertices.append(Float(a["y"] ?? "") ?? 0)
                o.vertices.append(Float(a["z"] ?? "") ?? 0)
            case "triangle":
                guard let o = current, let v1 = UInt32(a["v1"] ?? ""), let v2 = UInt32(a["v2"] ?? ""),
                      let v3 = UInt32(a["v3"] ?? "") else { return }
                o.triangles.append(v1); o.triangles.append(v2); o.triangles.append(v3)
                triangles += 1
                if triangles > MeshLoader.maxTriangles * 2 { parser.abortParsing() }
            case "component":
                guard let o = current, let id = a["objectid"] else { return }
                o.components.append(Component(objectID: id, path: ThreeMFReader.pathAttribute(a),
                                              matrix: ThreeMFReader.transform(a["transform"])))
            case "object":
                let o = Object()
                current = o
                if let id = a["id"] { objects[id] = o }
            case "build":
                inBuild = true
            case "item":
                guard inBuild, let id = a["objectid"] else { return }
                items.append(Component(objectID: id, path: ThreeMFReader.pathAttribute(a),
                                       matrix: ThreeMFReader.transform(a["transform"])))
            case "model":
                if let u = a["unit"] { unit = u }
            default:
                break
            }
        }

        func parser(_ parser: XMLParser, didEndElement name: String, namespaceURI: String?,
                    qualifiedName: String?) {
            switch ThreeMFReader.localName(name) {
            case "object": current = nil
            case "build": inBuild = false
            default: break
            }
        }
    }
}

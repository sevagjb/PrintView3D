// PrintView3D Quick Look preview: what the space bar shows in Finder.
//   STL, 3MF, OBJ, PLY: the model in 3D (drag to turn it, scroll / pinch to zoom), seen like
//                       PrintView3D's Iso view, with its size in millimetres.
//   G-code, FreeCAD:    the picture saved in the file by the slicer or FreeCAD.
//                       (A 3MF whose model can't be read shows its picture too.)
// It stays a preview: opening the file in PrintView3D gives the full viewer.

import AppKit
import Quartz
import SceneKit

@objc(PV3DPreviewViewController)
final class PreviewViewController: NSViewController, QLPreviewingController {
    /// More triangles than this are thinned out for the preview (keeps it quick and light).
    static let maxPreviewTriangles = 1_500_000
    static let modelBlue = NSColor(srgbRed: 74 / 255, green: 163 / 255, blue: 223 / 255, alpha: 1)

    private enum Content {
        case mesh(Mesh)
        case picture(CGImage)
    }

    override var nibName: NSNib.Name? { nil }

    override func loadView() {
        let v = NSView(frame: NSRect(x: 0, y: 0, width: 800, height: 600))
        v.autoresizingMask = [.width, .height]
        view = v
        preferredContentSize = NSSize(width: 800, height: 600)
    }

    func preparePreviewOfFile(at url: URL, completionHandler handler: @escaping (Error?) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            let content = Self.load(url)
            DispatchQueue.main.async {
                switch content {
                case .mesh(let m)?: self.show(mesh: m)
                case .picture(let img)?: self.show(picture: img)
                case nil:
                    handler(PV3DKind(url: url) == nil ? PV3DError.unsupported : PV3DError.unreadable)
                    return
                }
                handler(nil)
            }
        }
    }

    private static func load(_ url: URL) -> Content? {
        guard let kind = PV3DKind(url: url), let file = MappedFile(url: url) else { return nil }
        if kind.hasMesh, let m = MeshLoader.load(url: url, kind: kind, file: file) {
            return .mesh(m.thinned(to: maxPreviewTriangles))
        }
        if let pic = file.embeddedPicture(kind), let img = Pictures.decode(pic, maxPixels: 2048) {
            return .picture(img)
        }
        return nil
    }

    // MARK: - picture

    private func show(picture: CGImage) {
        let iv = NSImageView(frame: view.bounds)
        iv.autoresizingMask = [.width, .height]
        iv.imageScaling = .scaleProportionallyUpOrDown
        iv.image = NSImage(cgImage: picture, size: NSSize(width: picture.width, height: picture.height))
        view.addSubview(iv)
        preferredContentSize = NSSize(width: max(320, min(1000, picture.width)),
                                      height: max(240, min(800, picture.height)))
    }

    // MARK: - 3D

    private func show(mesh: Mesh) {
        guard let box = mesh.bounds() else { return }
        let lo = box.min, hi = box.max
        let center = (lo + hi) / 2
        let size = hi - lo
        let radius = max(simd_length(size) / 2, 0.001)

        let scene = SCNScene()
        // Models are Z up (as in slicers); SceneKit is Y up.
        let zUp = SCNNode()
        zUp.eulerAngles.x = -.pi / 2
        scene.rootNode.addChildNode(zUp)
        let model = SCNNode(geometry: Self.geometry(mesh))
        model.position = SCNVector3(-center.x, -center.y, -center.z)
        zUp.addChildNode(model)

        let ambient = SCNNode()
        ambient.light = SCNLight()
        ambient.light!.type = .ambient
        ambient.light!.intensity = 350
        scene.rootNode.addChildNode(ambient)

        // Camera like PrintView3D's Iso view: front-left, 30 degrees from above.
        let cam = SCNCamera()
        cam.fieldOfView = 30
        let distance = Double(radius) / sin(15 * Double.pi / 180) * 1.1
        cam.zNear = max(distance - Double(radius) * 4, distance / 1000)
        cam.zFar = distance + Double(radius) * 4
        let camNode = SCNNode()
        camNode.camera = cam
        // Model direction (-cos30 sin45, -cos30 cos45, sin30); in SceneKit (x, z, -y).
        let dir = simd_normalize(SIMD3<Double>(-0.612, 0.5, 0.612))
        camNode.position = SCNVector3(dir.x * distance, dir.y * distance, dir.z * distance)
        camNode.look(at: SCNVector3(0, 0, 0))
        scene.rootNode.addChildNode(camNode)

        let sv = SCNView(frame: view.bounds, options: nil)
        sv.autoresizingMask = [.width, .height]
        sv.scene = scene
        sv.pointOfView = camNode
        sv.allowsCameraControl = true
        sv.defaultCameraController.interactionMode = .orbitTurntable
        sv.autoenablesDefaultLighting = true
        sv.antialiasingMode = .multisampling4X
        let dark = view.effectiveAppearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua
        sv.backgroundColor = dark ? NSColor(white: 0.17, alpha: 1) : NSColor(white: 0.95, alpha: 1)
        view.addSubview(sv)

        // Size in millimetres (numbers only, so it needs no translation).
        let label = NSTextField(labelWithString: String(format: "%.1f × %.1f × %.1f mm", size.x, size.y, size.z))
        label.font = .systemFont(ofSize: 12)
        label.textColor = dark ? NSColor(white: 0.8, alpha: 1) : NSColor(white: 0.3, alpha: 1)
        label.sizeToFit()
        label.frame.origin = NSPoint(x: 12, y: 10)
        label.autoresizingMask = [.maxXMargin, .maxYMargin]
        view.addSubview(label)
    }

    /// One flat-shaded triangle soup (each corner its own vertex, the triangle's normal).
    private static func geometry(_ mesh: Mesh) -> SCNGeometry {
        let n = mesh.triangleCount
        var normals = [Float](repeating: 0, count: n * 9)
        mesh.xyz.withUnsafeBufferPointer { p in
            for t in 0..<n {
                let o = t * 9
                let a = SIMD3<Float>(p[o], p[o + 1], p[o + 2])
                let b = SIMD3<Float>(p[o + 3], p[o + 4], p[o + 5])
                let c = SIMD3<Float>(p[o + 6], p[o + 7], p[o + 8])
                var nrm = simd_cross(b - a, c - a)
                let len = simd_length(nrm)
                nrm = len > 0 && len.isFinite ? nrm / len : SIMD3<Float>(0, 0, 1)
                for k in 0..<3 {
                    normals[o + k * 3] = nrm.x
                    normals[o + k * 3 + 1] = nrm.y
                    normals[o + k * 3 + 2] = nrm.z
                }
            }
        }
        func source(_ values: [Float], _ semantic: SCNGeometrySource.Semantic) -> SCNGeometrySource {
            let data = values.withUnsafeBufferPointer { Data(buffer: $0) }
            return SCNGeometrySource(data: data, semantic: semantic, vectorCount: n * 3, usesFloatComponents: true,
                                     componentsPerVector: 3, bytesPerComponent: 4, dataOffset: 0, dataStride: 12)
        }
        let indices = (0..<UInt32(n * 3)).map { $0 }
        let element = SCNGeometryElement(data: indices.withUnsafeBufferPointer { Data(buffer: $0) },
                                         primitiveType: .triangles, primitiveCount: n, bytesPerIndex: 4)
        let geo = SCNGeometry(sources: [source(mesh.xyz, .vertex), source(normals, .normal)], elements: [element])
        let mat = SCNMaterial()
        mat.lightingModel = .blinn
        mat.diffuse.contents = modelBlue
        mat.specular.contents = NSColor(white: 0.25, alpha: 1)
        mat.isDoubleSided = true
        geo.materials = [mat]
        return geo
    }
}

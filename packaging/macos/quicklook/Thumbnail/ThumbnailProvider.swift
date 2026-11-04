// PrintView3D Quick Look thumbnails: the icons Finder shows for 3MF, STL, G-code, FreeCAD,
// OBJ and PLY files. macOS runs this in its own sandboxed helper, so a broken file can never
// hurt Finder. The pictures come from Shared/Pictures.swift.

import AppKit
import QuickLookThumbnailing

@objc(PV3DThumbnailProvider)
final class ThumbnailProvider: QLThumbnailProvider {
    override func provideThumbnail(for request: QLFileThumbnailRequest,
                                   _ handler: @escaping (QLThumbnailReply?, Error?) -> Void) {
        let box = request.maximumSize
        let px = Int((max(box.width, box.height) * max(request.scale, 1)).rounded(.up))
        guard let image = Pictures.thumbnail(url: request.fileURL, maxPixels: px) else {
            handler(nil, PV3DError.unreadable)
            return
        }
        let w = CGFloat(image.width), h = CGFloat(image.height)
        let f = min(box.width / w, box.height / h)
        let size = CGSize(width: max(1, (w * f).rounded()), height: max(1, (h * f).rounded()))
        let reply = QLThumbnailReply(contextSize: size, drawing: { ctx -> Bool in
            ctx.interpolationQuality = .high
            ctx.draw(image, in: CGRect(origin: .zero, size: size))
            return true
        })
        handler(reply, nil)
    }
}

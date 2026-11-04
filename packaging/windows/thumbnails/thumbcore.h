// PrintView3D thumbnails - the part that does not depend on Windows.
//
// Finds the preview picture saved inside 3MF, FreeCAD (.FCStd) and G-code files
// (the same rules as PrintView3D itself), and draws STL models.
// Used by the Windows File Explorer thumbnail provider (provider.cpp), the macOS
// Quick Look extensions (packaging/macos/quicklook) and tested on any system with
// core_test.cpp.

#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace pv3d {

// Random-access view of a file (Explorer hands us a stream, the tests a buffer).
struct Source {
    virtual ~Source() = default;
    virtual uint64_t size() = 0;
    virtual bool read(uint64_t offset, void* buf, size_t len) = 0;
};

struct MemorySource : Source {
    const uint8_t* p;
    size_t n;
    MemorySource(const uint8_t* p_, size_t n_) : p(p_), n(n_) {}
    uint64_t size() override { return n; }
    bool read(uint64_t off, void* buf, size_t len) override;
};

enum class Kind { Unknown, Zip, Gcode, Stl };

// Look at the first bytes: zip (3MF / FCStd), G-code text, or STL.
Kind detect(Source& src);

// The embedded preview picture (PNG or JPEG bytes) of a 3MF / FCStd file.
bool zip_thumbnail(Source& src, std::vector<uint8_t>& image);

// The largest embedded preview picture of a G-code file.
bool gcode_thumbnail(Source& src, std::vector<uint8_t>& image);

// Draw an STL model, seen from the front-left above (like PrintView3D's "Iso" view),
// into size x size RGBA pixels (transparent background).
bool render_stl(Source& src, int size, std::vector<uint8_t>& rgba);

// Draw triangles (9 floats each: x, y, z of the three corners) the same way as render_stl.
bool render_triangles(const float* xyz, size_t triangles, int size, std::vector<uint8_t>& rgba);

// The triangles of an STL file, 9 floats each (very large files are thinned out to
// at most 4 million triangles, as for drawing).
bool stl_triangles(Source& src, std::vector<float>& xyz);

// The names of the files inside a zip (3MF / FCStd).
bool zip_names(Source& src, std::vector<std::string>& names);

// One file from inside a zip (name compared without case), at most max_size bytes.
bool zip_read(Source& src, const std::string& name, std::vector<uint8_t>& out, uint64_t max_size);

// Base64 (as in G-code thumbnails); invalid characters are skipped.
std::vector<uint8_t> base64_decode(const std::string& text);

}  // namespace pv3d

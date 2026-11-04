// PrintView3D thumbnails - see thumbcore.h.
// Everything here must be safe on broken or hostile files: all reads are
// bounds-checked and sizes are limited, because this code runs for every file
// File Explorer shows.

#include "thumbcore.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>

extern "C" {
#include "tinf/tinf.h"
}

namespace pv3d {

namespace {
const uint64_t kMaxImage = 20u << 20;     // embedded picture: at most 20 MB
const uint64_t kMaxStl = 512u << 20;      // STL: at most 512 MB is read
const size_t kGcodeHead = 4u << 20;       // G-code thumbnails are near the top
const uint32_t kMaxTriangles = 4000000;   // draw at most 4 M triangles
const float kMaxCoord = 1e15f;            // larger (or NaN/inf) coordinates count as 0, so the
                                          // projection below can never overflow to infinity
const uint64_t kMaxPixelTests = 600000000u;  // drawing budget: a hostile STL of millions of
                                             // huge triangles stops here instead of keeping
                                             // Explorer busy for minutes

uint16_t le16(const uint8_t* p) { return uint16_t(p[0] | (p[1] << 8)); }
uint32_t le32(const uint8_t* p) { return uint32_t(p[0]) | (uint32_t(p[1]) << 8) | (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24); }
uint64_t le64(const uint8_t* p) { return uint64_t(le32(p)) | (uint64_t(le32(p + 4)) << 32); }

std::string lower(std::string s) {
    for (auto& c : s) c = char(std::tolower(static_cast<unsigned char>(c)));
    return s;
}

bool is_image(const std::vector<uint8_t>& d) {
    static const uint8_t png[8] = {0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'};
    return (d.size() > 8 && std::memcmp(d.data(), png, 8) == 0) ||
           (d.size() > 3 && d[0] == 0xff && d[1] == 0xd8 && d[2] == 0xff);
}

bool ends_with(const std::string& s, const char* suf) {
    size_t n = std::strlen(suf);
    return s.size() >= n && s.compare(s.size() - n, n, suf) == 0;
}
}  // namespace

bool MemorySource::read(uint64_t off, void* buf, size_t len) {
    if (off > n || len > n - off) return false;
    std::memcpy(buf, p + off, len);
    return true;
}

// ------------------------------------------------------------------ detect
Kind detect(Source& src) {
    uint64_t n = src.size();
    if (n < 4) return Kind::Unknown;
    uint8_t head[512] = {0};
    size_t got = size_t(std::min<uint64_t>(n, sizeof head));
    if (!src.read(0, head, got)) return Kind::Unknown;
    if (head[0] == 'P' && head[1] == 'K' && head[2] == 3 && head[3] == 4) return Kind::Zip;
    // Binary STL: 80-byte header, triangle count, 50 bytes per triangle.
    if (n >= 84) {
        uint8_t c[4];
        if (src.read(80, c, 4) && 84 + uint64_t(le32(c)) * 50 == n) return Kind::Stl;
    }
    std::string text(reinterpret_cast<char*>(head), got);
    std::string l = lower(text);
    if (l.compare(0, 5, "solid") == 0) return Kind::Stl;     // ASCII STL
    // G-code: comment lines and G/M commands.
    if (l.find(";") != std::string::npos || l.find("g1 ") != std::string::npos ||
        l.find("g28") != std::string::npos || l.find("m10") != std::string::npos)
        return Kind::Gcode;
    return Kind::Unknown;
}

// --------------------------------------------------------------------- zip
namespace {
struct ZipEntry {
    std::string name;
    uint16_t method = 0;
    uint64_t csize = 0, usize = 0, local = 0;
};

bool read_central_directory(Source& src, std::vector<ZipEntry>& out) {
    uint64_t n = src.size();
    if (n < 22) return false;
    // End-of-central-directory record: in the last 64 KB + 22 bytes.
    uint64_t tail = std::min<uint64_t>(n, 65536 + 22);
    std::vector<uint8_t> t(static_cast<size_t>(tail));
    if (!src.read(n - tail, t.data(), t.size())) return false;
    int64_t eocd = -1;
    for (int64_t i = int64_t(t.size()) - 22; i >= 0; --i)
        if (le32(&t[size_t(i)]) == 0x06054b50) { eocd = i; break; }
    if (eocd < 0) return false;
    const uint8_t* e = &t[size_t(eocd)];
    uint64_t count = le16(e + 10), cd_size = le32(e + 12), cd_off = le32(e + 16);
    // Zip64 (large 3MF projects): the locator sits just before the EOCD record.
    if ((cd_off == 0xffffffffu || count == 0xffff) && eocd >= 20 && le32(e - 20) == 0x07064b50) {
        uint64_t z64 = le64(e - 20 + 8);
        uint8_t r[56];
        if (!src.read(z64, r, sizeof r) || le32(r) != 0x06064b50) return false;
        count = le64(r + 32);
        cd_size = le64(r + 40);
        cd_off = le64(r + 48);
    }
    if (cd_size > (64u << 20) || cd_off > n || cd_size > n - cd_off || count > 200000) return false;
    std::vector<uint8_t> cd(static_cast<size_t>(cd_size));
    if (!src.read(cd_off, cd.data(), cd.size())) return false;
    size_t p = 0;
    for (uint64_t i = 0; i < count && p + 46 <= cd.size(); ++i) {
        const uint8_t* h = &cd[p];
        if (le32(h) != 0x02014b50) break;
        ZipEntry z;
        z.method = le16(h + 10);
        z.csize = le32(h + 20);
        z.usize = le32(h + 24);
        uint16_t nl = le16(h + 28), xl = le16(h + 30), cl = le16(h + 32);
        z.local = le32(h + 42);
        if (p + 46 + size_t(nl) + xl + cl > cd.size()) break;
        z.name.assign(reinterpret_cast<const char*>(h + 46), nl);
        // Zip64 extra field: replaces the fields that are 0xFFFFFFFF, in this order.
        const uint8_t* x = h + 46 + nl;
        for (size_t k = 0; k + 4 <= xl;) {
            uint16_t id = le16(x + k), sz = le16(x + k + 2);
            if (k + 4 + sz > xl) break;
            if (id == 0x0001) {
                const uint8_t* v = x + k + 4;
                size_t q = 0;
                if (z.usize == 0xffffffffu && q + 8 <= sz) { z.usize = le64(v + q); q += 8; }
                if (z.csize == 0xffffffffu && q + 8 <= sz) { z.csize = le64(v + q); q += 8; }
                if (z.local == 0xffffffffu && q + 8 <= sz) { z.local = le64(v + q); q += 8; }
            }
            k += 4 + size_t(sz);
        }
        out.push_back(std::move(z));
        p += 46 + size_t(nl) + xl + cl;
    }
    return !out.empty();
}

bool extract(Source& src, const ZipEntry& z, std::vector<uint8_t>& out, uint64_t max_size = kMaxImage) {
    if (z.usize > max_size || z.csize > max_size || max_size > 0xffffffffu) return false;
    uint8_t lh[30];
    if (!src.read(z.local, lh, sizeof lh) || le32(lh) != 0x04034b50) return false;
    uint64_t data = z.local + 30 + le16(lh + 26) + le16(lh + 28);
    std::vector<uint8_t> comp(static_cast<size_t>(z.csize));
    if (!src.read(data, comp.data(), comp.size())) return false;
    if (z.method == 0) {
        out.swap(comp);
        return true;
    }
    if (z.method != 8) return false;
    out.assign(size_t(z.usize), 0);
    unsigned int len = unsigned(out.size());
    if (tinf_uncompress(out.data(), &len, comp.data(), unsigned(comp.size())) != TINF_OK) return false;
    out.resize(len);
    return true;
}
}  // namespace

bool zip_thumbnail(Source& src, std::vector<uint8_t>& image) {
    std::vector<ZipEntry> entries;
    if (!read_central_directory(src, entries)) return false;
    // Same order as PrintView3D: the slicer's plate picture first, then any picture
    // in Metadata/ (3MF) or thumbnails/ (FreeCAD).
    const char* preferred[] = {"metadata/plate_1.png", "metadata/thumbnail.png", "metadata/top_1.png"};
    for (const char* want : preferred)
        for (const auto& z : entries)
            if (lower(z.name) == want && extract(src, z, image) && is_image(image)) return true;
    for (const auto& z : entries) {
        std::string l = lower(z.name);
        if ((l.rfind("metadata/", 0) == 0 || l.rfind("thumbnails/", 0) == 0) &&
            (ends_with(l, ".png") || ends_with(l, ".jpg") || ends_with(l, ".jpeg")) &&
            extract(src, z, image) && is_image(image))
            return true;
    }
    return false;
}

bool zip_names(Source& src, std::vector<std::string>& names) {
    std::vector<ZipEntry> entries;
    if (!read_central_directory(src, entries)) return false;
    for (const auto& z : entries) names.push_back(z.name);
    return true;
}

bool zip_read(Source& src, const std::string& name, std::vector<uint8_t>& out, uint64_t max_size) {
    std::vector<ZipEntry> entries;
    if (!read_central_directory(src, entries)) return false;
    std::string want = lower(name);
    while (!want.empty() && want[0] == '/') want.erase(0, 1);
    for (const auto& z : entries)
        if (lower(z.name) == want) return extract(src, z, out, max_size);
    return false;
}

// ------------------------------------------------------------------ G-code
std::vector<uint8_t> base64_decode(const std::string& s) {
    static int8_t map[256];
    static bool init = false;
    if (!init) {
        std::memset(map, -1, sizeof map);
        const char* a = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        for (int i = 0; a[i]; ++i) map[uint8_t(a[i])] = int8_t(i);
        init = true;
    }
    std::vector<uint8_t> out;
    out.reserve(s.size() * 3 / 4);
    uint32_t acc = 0;
    int bits = 0;
    for (unsigned char c : s) {
        if (c == '=') break;
        int v = map[c];
        if (v < 0) continue;
        acc = (acc << 6) | uint32_t(v);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            out.push_back(uint8_t((acc >> bits) & 0xff));
        }
    }
    return out;
}

bool gcode_thumbnail(Source& src, std::vector<uint8_t>& image) {
    size_t n = size_t(std::min<uint64_t>(src.size(), kGcodeHead));
    std::string text(n, '\0');
    if (n == 0 || !src.read(0, &text[0], n)) return false;
    // Blocks like  "; thumbnail begin 300x300 12345" ... "; thumbnail end"
    // (also thumbnail_PNG / thumbnail_JPG / png / jpg, as PrintView3D reads them).
    static const char* words[] = {"thumbnail_png", "thumbnail_jpg", "thumbnail", "png", "jpeg", "jpg"};
    long best_area = -1;
    size_t pos = 0;
    std::string word, buf;
    long area = 0;
    bool inside = false;
    while (pos < n) {
        size_t end = text.find('\n', pos);
        if (end == std::string::npos) end = n;
        std::string line = text.substr(pos, end - pos);
        pos = end + 1;
        size_t sc = line.find(';');
        if (sc == std::string::npos) continue;
        std::string c = line.substr(sc + 1);
        size_t a = c.find_first_not_of(" \t");
        if (a == std::string::npos) continue;
        c = c.substr(a);
        while (!c.empty() && (c.back() == '\r' || c.back() == ' ')) c.pop_back();
        std::string lc = lower(c);
        if (inside) {
            if (lc.rfind(word + " end", 0) == 0) {
                std::vector<uint8_t> d = base64_decode(buf);
                if (is_image(d) && area > best_area) {
                    best_area = area;
                    image.swap(d);
                }
                inside = false;
                buf.clear();
            } else {
                buf += c;
                if (buf.size() > kMaxImage * 2) { inside = false; buf.clear(); }
            }
            continue;
        }
        for (const char* w : words) {
            std::string b = std::string(w) + " begin";
            if (lc.rfind(b, 0) == 0) {
                int wdt = 0, hgt = 0;
                const char* p = lc.c_str() + b.size();
                while (*p == ' ') ++p;
                wdt = std::atoi(p);
                while (*p && *p != 'x' && *p != '*' && *p != ' ') ++p;
                if (*p) ++p;
                hgt = std::atoi(p);
                area = long(std::max(wdt, 1)) * long(std::max(hgt, 1));
                word = w;
                inside = true;
                buf.clear();
                break;
            }
        }
    }
    return best_area >= 0;
}

// --------------------------------------------------------------------- STL
namespace {
struct V3 { float x, y, z; };

bool load_stl(Source& src, std::vector<V3>& tri) {
    uint64_t n = src.size();
    if (n < 15 || n > kMaxStl) return false;
    uint8_t c[4];
    if (n >= 84 && src.read(80, c, 4) && 84 + uint64_t(le32(c)) * 50 == n) {
        uint32_t count = le32(c);
        const uint32_t kMax = kMaxTriangles;
        uint32_t step = count > kMax ? (count + kMax - 1) / kMax : 1;
        std::vector<uint8_t> rec(50);
        const size_t chunk = 20000;
        std::vector<uint8_t> blk(chunk * 50);
        tri.reserve(size_t(count / step) * 3);
        for (uint32_t i = 0; i < count; i += uint32_t(chunk)) {
            uint32_t m = std::min<uint32_t>(uint32_t(chunk), count - i);
            if (!src.read(84 + uint64_t(i) * 50, blk.data(), size_t(m) * 50)) return false;
            for (uint32_t k = 0; k < m; ++k) {
                if ((i + k) % step) continue;
                const uint8_t* r = &blk[size_t(k) * 50 + 12];
                for (int v = 0; v < 3; ++v) {
                    V3 p;
                    std::memcpy(&p, r + v * 12, 12);
                    tri.push_back(p);
                }
            }
        }
        return !tri.empty();
    }
    // ASCII STL: "vertex x y z" lines.
    std::string text(size_t(n), '\0');
    if (!src.read(0, &text[0], text.size())) return false;
    size_t p = 0;
    while ((p = text.find("vertex", p)) != std::string::npos) {
        p += 6;
        char* e = nullptr;
        V3 v;
        v.x = std::strtof(text.c_str() + p, &e);
        v.y = std::strtof(e, &e);
        v.z = std::strtof(e, &e);
        p = size_t(e - text.c_str());
        tri.push_back(v);
        if (tri.size() >= size_t(kMaxTriangles) * 3) break;
    }
    tri.resize(tri.size() - tri.size() % 3);
    return !tri.empty();
}

bool render_v3(std::vector<V3>& t, int size, std::vector<uint8_t>& rgba);
}  // namespace

bool render_stl(Source& src, int size, std::vector<uint8_t>& rgba) {
    if (size < 16 || size > 2048) return false;
    std::vector<V3> t;
    if (!load_stl(src, t)) return false;
    return render_v3(t, size, rgba);
}

bool stl_triangles(Source& src, std::vector<float>& xyz) {
    std::vector<V3> t;
    if (!load_stl(src, t)) return false;
    xyz.resize(t.size() * 3);
    std::memcpy(xyz.data(), t.data(), xyz.size() * sizeof(float));
    return true;
}

bool render_triangles(const float* xyz, size_t triangles, int size, std::vector<uint8_t>& rgba) {
    if (size < 16 || size > 2048 || !xyz || triangles == 0) return false;
    size_t step = triangles > kMaxTriangles ? (triangles + kMaxTriangles - 1) / kMaxTriangles : 1;
    std::vector<V3> t;
    t.reserve(triangles / step * 3);
    for (size_t i = 0; i < triangles; i += step)
        for (int v = 0; v < 3; ++v) {
            const float* p = xyz + i * 9 + v * 3;
            t.push_back({p[0], p[1], p[2]});
        }
    return render_v3(t, size, rgba);
}

namespace {
bool render_v3(std::vector<V3>& t, int size, std::vector<uint8_t>& rgba) {
    if (size < 16 || size > 2048 || t.empty()) return false;

    // View like PrintView3D's Iso camera: turned 45 degrees, looking down ~30 degrees.
    const float az = 0.7853982f, el = 0.5235988f;
    const float ca = std::cos(az), sa = std::sin(az), ce = std::cos(el), se = std::sin(el);
    float minx = 1e30f, maxx = -1e30f, miny = 1e30f, maxy = -1e30f;
    for (auto& p : t) {
        if (!(std::fabs(p.x) <= kMaxCoord && std::fabs(p.y) <= kMaxCoord && std::fabs(p.z) <= kMaxCoord))
            p = {0, 0, 0};                        // NaN, infinity or absurdly far away
        float x = ca * p.x - sa * p.y;            // screen right
        float d = sa * p.x + ca * p.y;            // into the screen (horizontal)
        float y = ce * p.z + se * d;              // screen up
        float z = -se * p.z + ce * d;             // depth (larger = further away)
        p = {x, y, z};
        minx = std::min(minx, x); maxx = std::max(maxx, x);
        miny = std::min(miny, y); maxy = std::max(maxy, y);
    }
    const int S = size * 2;                       // draw twice as large, then smooth
    float span = std::max(maxx - minx, maxy - miny);
    if (!(span > 0) || !std::isfinite(span)) return false;
    float scale = (S * 0.92f) / span;
    float ox = (S - (maxx - minx) * scale) * 0.5f, oy = (S - (maxy - miny) * scale) * 0.5f;

    std::vector<float> depth(size_t(S) * S, 1e30f);
    std::vector<uint8_t> shade(size_t(S) * S, 0);
    std::vector<uint8_t> hit(size_t(S) * S, 0);
    const float lx = -0.35f, ly = 0.55f, lz = -0.76f;   // light from top-left, toward the viewer
    uint64_t pixel_tests = 0;
    for (size_t i = 0; i + 2 < t.size() && pixel_tests < kMaxPixelTests; i += 3) {
        V3 a = t[i], b = t[i + 1], c = t[i + 2];
        float ax = (a.x - minx) * scale + ox, ay = S - ((a.y - miny) * scale + oy);
        float bx = (b.x - minx) * scale + ox, by = S - ((b.y - miny) * scale + oy);
        float cx = (c.x - minx) * scale + ox, cy = S - ((c.y - miny) * scale + oy);
        // Normal in view space for the shading (both sides lit).
        float ux = b.x - a.x, uy = b.y - a.y, uz = b.z - a.z;
        float vx = c.x - a.x, vy = c.y - a.y, vz = c.z - a.z;
        float nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
        float nl = std::sqrt(nx * nx + ny * ny + nz * nz);
        if (!(nl > 0)) continue;
        // Key light from the top-left plus a soft fill from the right, so no side goes black.
        float key = std::fabs((nx * lx + ny * ly + nz * lz) / nl);
        float fill = std::fabs((nx * 0.70f + ny * 0.20f + nz * -0.68f) / nl);
        uint8_t s = uint8_t(std::min(255.0f, 70.0f + 150.0f * key + 55.0f * fill));
        float area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
        if (std::fabs(area) < 1e-12f) continue;
        int x0 = std::max(0, int(std::floor(std::min({ax, bx, cx}))));
        int x1 = std::min(S - 1, int(std::ceil(std::max({ax, bx, cx}))));
        int y0 = std::max(0, int(std::floor(std::min({ay, by, cy}))));
        int y1 = std::min(S - 1, int(std::ceil(std::max({ay, by, cy}))));
        if (x1 < x0 || y1 < y0) continue;
        pixel_tests += uint64_t(x1 - x0 + 1) * uint64_t(y1 - y0 + 1);
        for (int y = y0; y <= y1; ++y) {
            float py = y + 0.5f;
            for (int x = x0; x <= x1; ++x) {
                float px = x + 0.5f;
                float w0 = ((bx - px) * (cy - py) - (by - py) * (cx - px)) / area;
                float w1 = ((cx - px) * (ay - py) - (cy - py) * (ax - px)) / area;
                float w2 = 1.0f - w0 - w1;
                if (w0 < 0 || w1 < 0 || w2 < 0) continue;
                float z = w0 * a.z + w1 * b.z + w2 * c.z;
                size_t k = size_t(y) * S + x;
                if (z < depth[k]) {
                    depth[k] = z;
                    shade[k] = s;
                    hit[k] = 1;
                }
            }
        }
    }
    // Down to the requested size (2x2 average) in PrintView3D's model blue.
    const float base[3] = {74, 163, 223};
    rgba.assign(size_t(size) * size * 4, 0);
    for (int y = 0; y < size; ++y)
        for (int x = 0; x < size; ++x) {
            float r = 0, g = 0, bl = 0, al = 0;
            for (int dy = 0; dy < 2; ++dy)
                for (int dx = 0; dx < 2; ++dx) {
                    size_t k = size_t(y * 2 + dy) * S + (x * 2 + dx);
                    if (!hit[k]) continue;
                    float f = shade[k] / 255.0f;
                    r += base[0] * f; g += base[1] * f; bl += base[2] * f; al += 1;
                }
            if (al == 0) continue;
            uint8_t* o = &rgba[(size_t(y) * size + x) * 4];
            o[0] = uint8_t(r / al); o[1] = uint8_t(g / al); o[2] = uint8_t(bl / al);
            o[3] = uint8_t(255.0f * al / 4.0f);
        }
    return true;
}
}  // namespace

}  // namespace pv3d

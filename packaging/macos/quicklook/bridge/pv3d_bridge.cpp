// See pv3d_bridge.h. No C++ exception may reach Swift, so every function catches them all
// (in practice only std::bad_alloc on an absurd file).

#include "pv3d_bridge.h"

#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "thumbcore.h"

namespace {

template <typename T>
int hand_over(const std::vector<T>& v, pv3d_buffer* out) {
    if (!out || v.empty()) return 0;
    size_t bytes = v.size() * sizeof(T);
    void* p = std::malloc(bytes);
    if (!p) return 0;
    std::memcpy(p, v.data(), bytes);
    out->data = p;
    out->size = bytes;
    return 1;
}

template <typename F>
int guarded(pv3d_buffer* out, F&& f) {
    if (!out) return 0;
    out->data = nullptr;
    out->size = 0;
    try {
        return f();
    } catch (...) {
        pv3d_buffer_free(out);
        return 0;
    }
}

}  // namespace

extern "C" {

int pv3d_zip_picture(const uint8_t* file, size_t size, pv3d_buffer* out) {
    return guarded(out, [&] {
        if (!file) return 0;
        pv3d::MemorySource src(file, size);
        std::vector<uint8_t> img;
        return pv3d::zip_thumbnail(src, img) ? hand_over(img, out) : 0;
    });
}

int pv3d_gcode_picture(const uint8_t* file, size_t size, pv3d_buffer* out) {
    return guarded(out, [&] {
        if (!file) return 0;
        pv3d::MemorySource src(file, size);
        std::vector<uint8_t> img;
        return pv3d::gcode_thumbnail(src, img) ? hand_over(img, out) : 0;
    });
}

int pv3d_render_stl(const uint8_t* file, size_t size, int px, pv3d_buffer* rgba) {
    return guarded(rgba, [&] {
        if (!file) return 0;
        pv3d::MemorySource src(file, size);
        std::vector<uint8_t> pixels;
        return pv3d::render_stl(src, px, pixels) ? hand_over(pixels, rgba) : 0;
    });
}

int pv3d_render_triangles(const float* xyz, size_t triangles, int px, pv3d_buffer* rgba) {
    return guarded(rgba, [&] {
        std::vector<uint8_t> pixels;
        return pv3d::render_triangles(xyz, triangles, px, pixels) ? hand_over(pixels, rgba) : 0;
    });
}

int pv3d_stl_triangles(const uint8_t* file, size_t size, pv3d_buffer* xyz) {
    return guarded(xyz, [&] {
        if (!file) return 0;
        pv3d::MemorySource src(file, size);
        std::vector<float> v;
        return pv3d::stl_triangles(src, v) ? hand_over(v, xyz) : 0;
    });
}

int pv3d_zip_names(const uint8_t* file, size_t size, pv3d_buffer* out) {
    return guarded(out, [&] {
        if (!file) return 0;
        pv3d::MemorySource src(file, size);
        std::vector<std::string> names;
        if (!pv3d::zip_names(src, names)) return 0;
        std::string all;
        for (const auto& n : names) {
            all += n;
            all += '\n';
        }
        return hand_over(std::vector<char>(all.begin(), all.end()), out);
    });
}

int pv3d_zip_read(const uint8_t* file, size_t size, const char* name, uint64_t max_size, pv3d_buffer* out) {
    return guarded(out, [&] {
        if (!file || !name) return 0;
        pv3d::MemorySource src(file, size);
        std::vector<uint8_t> data;
        return pv3d::zip_read(src, name, data, max_size) ? hand_over(data, out) : 0;
    });
}

void pv3d_buffer_free(pv3d_buffer* buf) {
    if (!buf) return;
    std::free(buf->data);
    buf->data = nullptr;
    buf->size = 0;
}

}  // extern "C"

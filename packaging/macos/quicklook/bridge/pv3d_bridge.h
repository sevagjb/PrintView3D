// PrintView3D Quick Look: plain C functions around thumbcore (the C++ code that also makes
// the Windows File Explorer thumbnails), so the Swift extensions can use it.
//
// Every function takes the whole file as bytes (the extensions map the file into memory),
// returns 1 on success and 0 otherwise, and never throws. Results are handed back in a
// pv3d_buffer that the caller releases with pv3d_buffer_free (Swift: Data(bytesNoCopy:...,
// deallocator: .free) takes it over instead).

#ifndef PV3D_BRIDGE_H
#define PV3D_BRIDGE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct pv3d_buffer {
    void* data;   // malloc'ed
    size_t size;  // in bytes
} pv3d_buffer;

// The preview picture saved in a 3MF / FreeCAD file (PNG or JPEG bytes).
int pv3d_zip_picture(const uint8_t* file, size_t size, pv3d_buffer* out);

// The largest preview picture saved in a G-code file (PNG or JPEG bytes).
int pv3d_gcode_picture(const uint8_t* file, size_t size, pv3d_buffer* out);

// An STL model drawn into px x px RGBA pixels (not premultiplied; transparent background).
int pv3d_render_stl(const uint8_t* file, size_t size, int px, pv3d_buffer* rgba);

// Triangles (9 floats each) drawn the same way as pv3d_render_stl.
int pv3d_render_triangles(const float* xyz, size_t triangles, int px, pv3d_buffer* rgba);

// The triangles of an STL file as floats, 9 per triangle.
int pv3d_stl_triangles(const uint8_t* file, size_t size, pv3d_buffer* xyz);

// The names of the files inside a zip, separated by '\n'.
int pv3d_zip_names(const uint8_t* file, size_t size, pv3d_buffer* out);

// One file from inside a zip (name compared without case), at most max_size bytes.
int pv3d_zip_read(const uint8_t* file, size_t size, const char* name, uint64_t max_size, pv3d_buffer* out);

void pv3d_buffer_free(pv3d_buffer* buf);

#ifdef __cplusplus
}
#endif

#endif

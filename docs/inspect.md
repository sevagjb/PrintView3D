# Look inside your models

Hollow walls, hidden parts, channels, screw holes: the **View** button in the toolbar lets you look
inside a model before you print it. It works for STL, 3MF, OBJ and the other model formats
(G-code has its layer slider for this). *New in PrintView3D 0.25.*

<video class="pv-video" src="assets/inside/clip-facing.mp4" poster="assets/inside/clip-facing.jpg"
       autoplay loop muted playsinline preload="metadata"
       aria-label="A pump housing turning through an upright cut: the chamber, impeller, pocket and outlet channel come into view"></video>

## Clip facing you

An upright cut that always faces you and hides the part of the model in front of it.
**Turn the view and the model turns through the cut**; move (pan) the view and it slides across,
as if you held the model up to a scanner. For a cut straight from the front or the side, click
that face on the view cube.

The slider in the side panel moves the cut nearer or further. The inside of the walls the cut
lays open is drawn in red, so on a solid part you see the cut face.

![The cut and its slider in the side panel](assets/inside/clip-facing.png)

## Clip from the top

Hides everything above a height, like the layer slider does for G-code. Move the slider in the
side panel to go down through the model, layer by layer.

<video class="pv-video" src="assets/inside/clip-top.mp4" poster="assets/inside/clip-top.jpg"
       autoplay loop muted playsinline preload="metadata"
       aria-label="A cut moving down through the pump housing and back up"></video>

## See what the cut takes away

What a cut hides stays as a white, see-through **ghost** with outlined edges, and the **cutting
plane** shows as a faint sheet the size of the model, so you see what the cut takes away and where.
Under the sliders, **Show the cut-away part** and **Show the cutting plane** turn each on or off
(both on at first; your choice is remembered). In **Settings → Viewer**, **Cut-away part** and
**Cutting plane** each have a Fainter … Stronger slider, and the 3D view changes while you drag.
*New in PrintView3D 0.26.*

## Both cuts at once

<kbd>C</kbd> and <kbd>V</kbd> each turn their own cut on and off, so both can be on together: the
model then keeps only what both cuts keep, a corner cut away. The side panel has a slider for each,
**Height** and **Depth**. What the cuts hide still shows as one even, see-through ghost, and each
cutting plane stops where the other cut is. **Turn off** in the side panel ends both cuts; the same
key again ends just that one. *New in PrintView3D 0.27.*

## X-ray

The parts become see-through, so parts inside other parts, cavities, channels and screw holes
show, from every side.

<video class="pv-video" src="assets/inside/xray.mp4" poster="assets/inside/xray.jpg"
       autoplay loop muted playsinline preload="metadata"
       aria-label="The pump housing see-through, turning: the impeller and channels inside"></video>

The options work together, for example X-ray with a cut:

![X-ray and clip from the top together](assets/inside/xray-clip.png)

## Wireframe

The triangles of the mesh: to see how fine a model is, or to spot broken geometry.

![The pump housing as a wireframe](assets/inside/wireframe.png)

## The size of every object

The **Objects** list shows each object's size (X × Y × Z) next to its name; the size of the
whole model is in **Details**. Untick an object to hide it.

![The Objects list with each object's size](assets/inside/objects.png)

## Keys

| Key | |
|---|---|
| <kbd>W</kbd> | Wireframe on / off |
| <kbd>X</kbd> | X-ray on / off |
| <kbd>C</kbd> | Clip from the top on / off |
| <kbd>V</kbd> | Clip facing you on / off |
| <kbd>R</kbd> | Reset view: wireframe, X-ray and the cuts off, model fitted |

The options stay on when you open the next model.

## Try it yourself

The pump housing on this page is
[`examples/demo_housing.3mf`](https://github.com/sevagjb/PrintView3D/raw/main/examples/demo_housing.3mf)
in the source code: download it and open it in PrintView3D.

These features were suggested by [@covrig](https://github.com/covrig)
([#59](https://github.com/sevagjb/PrintView3D/issues/59),
[#60](https://github.com/sevagjb/PrintView3D/issues/60)). Have an idea too?
[Open an issue](https://github.com/sevagjb/PrintView3D/issues/new/choose).

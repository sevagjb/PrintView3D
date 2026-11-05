# Look inside your models

Hollow walls, hidden parts, channels, screw holes: the **View** button in the toolbar lets you look
inside a model before you print it. It works for STL, 3MF, OBJ and the other model formats
(G-code has its layer slider for this). The button opens a **View** section in the side panel with
every option as a button: Wireframe, X-ray, Clip from the top and Clip facing you. The controls of a
cut (its slider, the cut-away part, the cutting plane and Freeze) appear in the same section while
the cut is on, and the section ends with **Reset view** and **Close**. In a narrow side panel the
buttons get a smaller font; the panel never gets so narrow that an icon or a letter has to go.
*New in PrintView3D 0.25.*

<video class="pv-video" src="assets/inside/clip-facing.mp4" poster="assets/inside/clip-facing.jpg"
       autoplay loop muted playsinline preload="metadata"
       aria-label="A pump housing turning through an upright cut: the chamber, impeller, pocket and outlet channel come into view"></video>

## Clip facing you

An upright cut that always faces you and hides the part of the model in front of it.
**Turn the view and the model turns through the cut**; move (pan) the view and it slides across,
as if you held the model up to a scanner. For a cut straight from the front or the side, click
that face on the view cube.

The slider in the side panel moves the cut nearer or further; **Depth** shows how far the cut is
into the model, out of the model's depth in that direction. **Freeze the cutting plane** (in the
View section) keeps the cut where it is, so you can turn and move the model without the cut turning
along. The inside of the walls the cut lays open is drawn in red, so on a solid part you see the cut
face.

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

## Measure

The **Measure** button next to **View** (or <kbd>M</kbd>) opens the Measure section. Choose what to
measure with the buttons in it:

- **Distance**: click two points. The line follows the mouse and the distance is written next to
  it. Tick **Show ΔX ΔY ΔZ** to write the distance along each axis under every distance, handy for
  "how tall from here to there".
- **Angle**: click a point on one side, the corner, then a point on the other side.
- **Circle**: click three points on the edge of a circle or hole to read its diameter and radius.

How to use the chosen tool is written at the bottom of the 3D view while Measure is on. A click places a point, a drag still turns the view, so you can turn the model between points.
Finished measurements stay on screen with their value written next to them, and the next click
starts another; **Clear** removes them all. Drag a placed point to move it. **Snapping** (on at
every start) jumps to the nearest corner, the middle of an edge or a point on an edge. **Dotted line**
draws the lines as dots. How thick the lines are is a slider in Settings (Viewer). Values that would overlap, such as concentric circles, are stacked above each
other.

## Colours and the side panel

The **Objects** list comes first in the side panel and the **Details** last; click *Details* to fold
them away (the choice is remembered). At the top you see the file type and size. Click the colour
box of an object to pick another colour for that object alone; right-click it to go back to the
colour from the file. Colours you pick are not saved: they are back to normal after you restart.

## Distances on the grid

**Settings → Viewer → Show distances (mm) along the grid** (off by default) writes small numbers in
millimetres along the build plate, on its major grid lines: every 50 mm on a normal plate, thinned
to every 100 or 250 mm on a big one so a few readable numbers remain. They sit just outside the two
edges nearest to you, in the grid's own colour, stay upright whichever way you look, and hide when
you look from under the plate. With the endless grid they follow the area around the model.
**Spacing of the numbers** chooses another spacing, from 5 to 100 mm (for example 10 mm), instead
of the automatic one.

## Keys

| Key | |
|---|---|
| <kbd>W</kbd> | Wireframe on / off |
| <kbd>X</kbd> | X-ray on / off |
| <kbd>C</kbd> | Clip from the top on / off |
| <kbd>V</kbd> | Clip facing you on / off |
<<<<<<< HEAD
| <kbd>R</kbd> | Reset view: wireframe, X-ray and the cuts off, model fitted (measurements stay) |
=======
| <kbd>M</kbd> | Measure on / off |
>>>>>>> 4add7bf (Add Measure tool: distance, angle and circle, snapping, dotted lines, translations)

The options stay on when you open the next model.

## Try it yourself

The pump housing on this page is
[`examples/demo_housing.3mf`](https://github.com/sevagjb/PrintView3D/raw/main/examples/demo_housing.3mf)
in the source code: download it and open it in PrintView3D.

These features were suggested by [@covrig](https://github.com/covrig)
([#59](https://github.com/sevagjb/PrintView3D/issues/59),
[#60](https://github.com/sevagjb/PrintView3D/issues/60)). Have an idea too?
[Open an issue](https://github.com/sevagjb/PrintView3D/issues/new/choose).

# FreeCAD, STEP en andere formaten

## FreeCAD-bestanden {#freecad-files}

Open een FreeCAD-document (`.FCStd`) met **Openen** of sleep het naar het venster
(PrintView3D neemt de dubbelklik niet over van FreeCAD).
Het is alleen om te bekijken; er verandert niets in het bestand.

- **Met FreeCAD geïnstalleerd** (gratis, [freecad.org](https://www.freecad.org/downloads.php)) zie je het
  model in 3D zoals FreeCAD het toont: alleen zichtbare bodies en solids, zonder schetsen, verborgen objecten
  of hulpvlakken. PrintView3D start FreeCAD onzichtbaar op de achtergrond om de vormen om te zetten (de eerste
  keer een paar seconden; daarna wordt het onthouden tot het bestand verandert).
  De grote knop wordt **Openen in FreeCAD**, en het pijltje ▾ stuurt het zichtbare model als STL naar je
  slicer.
  **STL exporteren** (`Ctrl+E`) bewaart de zichtbare solids als STL-bestanden: alles in één bestand, of
  één bestand per solid (dezelfde keuzes als bij een 3MF-project). Dit werkt ook voor STEP-bestanden.
- **Zonder FreeCAD** zie je de voorbeeldafbeelding uit het bestand, de FreeCAD-versie en de zichtbare
  objecten, met een knop om FreeCAD te downloaden.

FreeCAD wordt automatisch gevonden op de gebruikelijke plekken (Windows-installer, Linux-pakketten, Snap,
Flatpak, AppImage). Staat het ergens anders, kies het dan in **Instellingen → FreeCAD**.

Omdat FreeCAD zelf het bestand opent, verdient een FreeCAD- of STEP-bestand hetzelfde vertrouwen als wanneer je
het in FreeCAD opent: open bestanden van mensen en sites die je vertrouwt.

<table>
<tr>
<td width="50%"><img src="../screenshot-freecad.png" alt="Een FreeCAD-beugel in 3D"><br><sub>Met FreeCAD geïnstalleerd: de beugel in 3D.</sub></td>
<td width="50%"><img src="../screenshot-freecad-preview.png" alt="Hetzelfde bestand zonder FreeCAD: de voorbeeldafbeelding"><br><sub>Zonder FreeCAD: de voorbeeldafbeelding uit het bestand.</sub></td>
</tr>
</table>

## STEP-bestanden {#step-files}

STEP (`.step`, `.stp`) is het gangbare formaat om CAD-modellen tussen programma's uit te wisselen. Het bewaart
exacte vormen (gebogen oppervlakken), geen driehoeken, dus PrintView3D gebruikt **FreeCAD** om er een mesh van
te maken, op dezelfde manier als bij [FreeCAD-bestanden](#freecad-files): onzichtbaar op de achtergrond, de
eerste keer een paar seconden, daarna onthouden tot het bestand verandert.

- **Onderdelen:** de onderdelen van een samenstelling staan apart in de lijst met hun namen uit het bestand, en
  kunnen verborgen worden. (Geeft de import van FreeCAD iets onverwachts, dan toont PrintView3D in plaats
  daarvan elke solid, zodat de vorm altijd klopt.)
- **Zonder FreeCAD** zie je toch de gegevens uit het bestand (STEP-versie, het CAD-programma waarmee het gemaakt
  is, auteur, organisatie, datum) en een knop om FreeCAD te downloaden.
- **Naar de slicer sturen:** OrcaSlicer, PrusaSlicer en Bambu Studio openen STEP-bestanden zelf en krijgen het
  bestand zoals het is (ook zonder FreeCAD). Andere slicers krijgen de zichtbare onderdelen als STL, en daarvoor
  is FreeCAD nodig.
- STEP-bestanden worden toegevoegd aan **Openen met**, maar PrintView3D maakt zichzelf nooit hun standaard-app.

## Andere 3D-formaten {#other-3d-formats}

| Formaat | Wat er gelezen wordt | Naar je slicer als |
|---|---|---|
| **OBJ** (`.obj`) | Objecten (`o`) of groepen (`g`) als losse objecten; kleuren uit het `.mtl`-bestand ernaast, of hoekpuntkleuren. | De `.obj` zelf |
| **PLY** (`.ply`) | Tekst en binair; hoekpunt- of vlakkleuren. Puntenwolken (zonder vlakken) kunnen niet getoond worden. | STL |
| **OFF** (`.off`) | Tekstbestanden (ook COFF), met hoekpunt- of vlakkleuren. | STL |
| **glTF / GLB** (`.gltf`, `.glb`) | Elk object in de scène op zijn plek, met zijn materiaalkleur of hoekpuntkleuren. | STL |

- **Maten:** OBJ, PLY en OFF hebben geen eenheden; PrintView3D leest de getallen als millimeters, net als
  slicers. Is een model heel klein, dan is het bestand waarschijnlijk in meters gemaakt; je slicer kan het
  schalen. glTF is altijd in meters en wordt in millimeters getoond (met Z omhoog, zoals op een printer).
- **Niet gelezen:** texturen (afbeeldingen op het model), animaties, en glTF-bestanden die met Draco of
  meshoptimizer zijn gecomprimeerd (PrintView3D zegt dat; exporteer ze opnieuw zonder compressie).
- Deze soorten worden toegevoegd aan **Openen met**, maar PrintView3D maakt zichzelf nooit hun standaard-app.

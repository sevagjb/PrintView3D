---
hide:
  - navigation
---

# PrintView3D

<p class="pv-lead">Een snelle, gratis viewer voor <b>STL</b>-, <b>3MF</b>-, <b>G-code</b>-, <b>FreeCAD</b>-, <b>STEP</b>-,
<b>OBJ</b>-, <b>PLY</b>- en <b>glTF</b>-bestanden op <b>Windows</b>, <b>Linux</b> en <b>macOS</b>, met één knop
die het bestand in <b>je eigen slicer</b> opent.</p>

[Downloaden :material-download:](https://github.com/sevagjb/PrintView3D/releases/latest){ .md-button .md-button--primary }
[Zo installeer je het](install.md){ .md-button }
[Broncode op GitHub :material-github:](https://github.com/sevagjb/PrintView3D){ .md-button }

![PrintView3D met een gesliceerde vaas, de laagschuif op 60 %](screenshot-gcode.png)

Microsoft is gestopt met de app **3D Viewer**, en Linux heeft nooit een goede gehad. PrintView3D vult dat
gat, gemaakt voor mensen die 3D-printen: het toont modellen *en* gesliceerde G-code, geeft de afmetingen,
printtijd en het filamentverbruik, en stuurt het bestand met één klik naar Creality Print, OrcaSlicer,
Bambu Studio, PrusaSlicer, Cura en andere. Ontwerp je in FreeCAD? Open het `.FCStd`-bestand en stuur het
direct als model naar je slicer, zonder eerst een STL te exporteren.

## Mogelijkheden

| | |
|---|---|
| **STL** | Een vloeiend belicht model op een printplaat, met afmetingen, aantal driehoeken en volume. |
| **3MF** | Elk object op de plaat, ook projecten uit Creality Print, OrcaSlicer en Bambu Studio. Toon of verberg elk object, bekijk de printer- en filamentinstellingen van het project en de miniatuur. Is het project al gesliceerd, dan zie je de printbanen zonder opnieuw te slicen. **STL exporteren**: bewaar de objecten als gewone STL-bestanden, samen of één per object. |
| **G-code** | Printbanen gekleurd per soort (wanden, vulling, boven/onder, support, bruggen, verplaatsingen…), een laagschuif, "Alleen deze laag tonen", printtijd, filamentverbruik en de voorbeeldafbeelding van de slicer. |
| **FreeCAD** | Open `.FCStd`-documenten om ze te bekijken: in 3D, precies zoals FreeCAD ze toont (alleen zichtbare bodies), met één klik om ze in FreeCAD te openen of als STL naar je slicer te sturen. Gebruikt je geïnstalleerde FreeCAD; zonder FreeCAD zie je nog steeds de voorbeeldafbeelding. [Meer](cad.md#freecad-files). |
| **STEP** | Open CAD-bestanden `.step` / `.stp`: in 3D met hulp van je geïnstalleerde FreeCAD (op de achtergrond omgezet en daarna onthouden), met het CAD-programma, de auteur en de datum uit het bestand. OrcaSlicer, PrusaSlicer en Bambu Studio krijgen het STEP-bestand zelf; andere slicers een STL. [Meer](cad.md#step-files). |
| **OBJ, PLY, OFF, glTF / GLB** | Andere gangbare 3D-formaten, met de kleuren uit het bestand (texturen worden niet getoond). Objecten in OBJ en scènes in glTF worden als losse objecten getoond. OBJ gaat zoals het is naar je slicer; PLY, OFF en glTF worden als STL verstuurd, omdat niet elke slicer ze leest. [Meer](cad.md#other-3d-formats). |
| **ZIP-bestanden** | Open een gedownload modelpakket (Printables, Thingiverse, …) direct. Alleen de 3D-bestanden worden gebruikt; afbeeldingen, documenten en links worden overgeslagen. Kies een model uit de lijst, of **toon alles** naast elkaar; stuur één model of alle modellen naar je slicer. [Meer](use.md#zip-files). |
| **Openen in je slicer** | Eén klik (of `Ctrl+P`) opent het huidige bestand in je slicer. Geïnstalleerde slicers worden automatisch gevonden. |
| **Standaard-app** | Optioneel: laat PrintView3D `.stl`-, `.3mf`- en `.gcode`-bestanden openen als je erop dubbelklikt. Volledig terug te draaien. |
| **Jouw taal** | English, العربية (Arabisch, van rechts naar links), Nederlands, Deutsch, Français, Español en Română; altijd te wisselen in Instellingen, zonder herstart. [Help vertalen](contribute.md#translations). |
| **Thema's** | Automatisch (volgt je systeem), Donker, Grijs, Grafiet (warm, rustig voor de ogen) of Licht, voor het venster en de 3D-weergave. Wissel met één klik op het palet-icoon of met `Ctrl+T`. De kleuren van de printbanen blijven in elk thema hetzelfde. |
| **Miniaturen** | Windows Verkenner toont voorbeelden van 3MF-, STL-, G-code- en FreeCAD-bestanden (geïnstalleerd met PrintView3D, optioneel). |
| **Updates** | **Controleren op updates** in Instellingen, of één keer per dag als je dat toestaat. Op Windows downloadt, controleert en installeert één klik de nieuwe versie. De versie in de hoek krijgt een rode stip als er een update klaarstaat. [Wat er verstuurd wordt](use.md#updates-and-privacy). |
| **Eén venster** | Een bestand waarop je dubbelklikt terwijl PrintView3D open is, verschijnt in dat venster in plaats van in een nieuw venster. Liever een venster per bestand? **Instellingen → Bestanden → Elk bestand in een nieuw venster openen**. |
| **Prettig in gebruik** | Camera zoals in een slicer, slepen en neerzetten, recente bestanden, schermafbeeldingen. |

<table>
<tr>
<td width="50%"><img src="screenshot-3mf.png" alt="Een 3MF-plaat met vier objecten"><br><sub>3MF-project: elk object in de lijst, elk kan verborgen worden.</sub></td>
<td width="50%"><img src="screenshot-layer.png" alt="Eén G-code-laag van boven gezien"><br><sub>"Alleen deze laag tonen": wanden en vulling van één laag.</sub></td>
</tr>
<tr>
<td width="50%"><img src="screenshot-model.png" alt="Een STL-model op de printplaat"><br><sub>STL-model met afmetingen en volume.</sub></td>
<td width="50%"><img src="screenshot-slicer-menu.png" alt="De slicerknop met zijn menu"><br><sub>Het pijltje ▾ stuurt het bestand één keer naar een andere slicer.</sub></td>
</tr>
</table>

## Ondersteunde slicers

Worden automatisch gevonden als ze geïnstalleerd zijn:

**Creality Print · OrcaSlicer · Bambu Studio · PrusaSlicer · UltiMaker Cura · Elegoo Slicer · Anycubic Slicer Next**

Elke andere slicer werkt ook: kies hem als **Ander programma** in Instellingen.

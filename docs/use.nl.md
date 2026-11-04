# PrintView3D gebruiken

**Een bestand openen:** dubbelklik erop (als PrintView3D het standaardprogramma is), sleep het naar het venster,
gebruik **Openen**, of kies het uit **Recent**. Probeer de bestanden in [`examples/`](https://github.com/sevagjb/PrintView3D/blob/main/examples) om te beginnen.

**Start:** de knop met het huisje (`Ctrl+W`) sluit het open bestand en gaat terug naar de startpagina,
met je recente bestanden. Het geeft ook het geheugen terug dat het bestand gebruikte; dat maakt vooral
verschil na een grote G-code of ZIP.

**Eén venster:** een bestand waarop je dubbelklikt terwijl PrintView3D al open is, verschijnt in dat venster,
dat naar voren komt. Wil je elk bestand in een eigen venster (om twee modellen naast elkaar te vergelijken),
vink dan **Instellingen → Bestanden → Elk bestand in een nieuw venster openen** aan. PrintView3D starten
vanuit het Startmenu of programmamenu, zonder bestand, opent altijd een nieuw venster.

## Muis {#mouse}

| Handeling | Wat het doet |
|---|---|
| **Slepen met links** | Draaien. Druk *op het model* om precies om dat punt te draaien; druk op een lege plek om om het midden van het model te draaien. De plaat blijft altijd waterpas. |
| **Slepen met rechts** (of met de middelste knop, of Shift + links) | Verschuiven |
| **Muiswiel** | In- en uitzoomen naar de muisaanwijzer |

Kijk je van onderen? De plaat gaat opzij, zodat je de onderkant van het onderdeel ziet.

## Toetsenbord {#keyboard}

Dezelfde lijst staat in het programma onder **Instellingen → Over → Toetsenbord en muis**.

| Toets | Actie |
|---|---|
| `Ctrl+O` | Een bestand openen |
| `Ctrl+W` | Het bestand sluiten (terug naar de startpagina) |
| `Ctrl+P` | Het bestand in je standaardslicer openen |
| `Ctrl+E` | STL exporteren (3MF-projecten, FreeCAD- en STEP-bestanden) |
| `Ctrl+T` | Volgend thema (Donker → Grijs → Grafiet → Licht) |
| `F` · `1` · `2` · `3` · `4` | Passend · Iso · Boven · Voor · Rechts |
| `W` · `X` · `C` · `V` | Draadmodel · Röntgen · Van boven afsnijden · Afsnijden vanaf jouw kant, aan / uit (modellen) |
| `R` | Weergave herstellen: draadmodel, röntgen en de sneden uit, model passend (modellen) |
| `↑` / `↓` | Volgende / vorige laag (G-code), of het vorige / volgende bestand in een ZIP |
| `Page Up` / `Page Down` | 10 lagen omhoog / omlaag |
| `Home` / `End` | Eerste / laatste laag |

## Weergave: draadmodel, röntgen en afsnijden {#view-wireframe-x-ray-and-clip}

De knop **Weergave** in de werkbalk verandert hoe een model getekend wordt (STL, 3MF, OBJ en de
andere modelformaten; G-code heeft daarvoor de laagschuifregelaar):

- **Draadmodel** (`W`): de driehoeken van het mesh, om te zien hoe fijn het is of kapotte geometrie te vinden.
- **Röntgen** (`X`): de onderdelen worden doorzichtig, zodat onderdelen in andere onderdelen,
  holtes en holle wanden zichtbaar worden.
- **Van boven afsnijden** (`C`): verbergt alles boven een hoogte. Een schuifregelaar in het
  zijpaneel verschuift de snede; de binnenkant van de wanden die de snede openlegt is rood.
  **Uitzetten** of `C` toont het hele model weer.
- **Afsnijden vanaf jouw kant** (`V`): een rechtopstaande snede die altijd naar je toe gericht is en
  het deel van het model ervoor verbergt. Draai de weergave en het model draait door de snede;
  verschuif (pan) de weergave en het schuift erlangs, alsof je het model voor een scanner houdt.
  Voor een snede van voren of van opzij klik je dat vlak op de weergavekubus aan. De schuifregelaar
  zet de snede dichterbij of verder weg. Eén snede tegelijk: `C` en `V` wisselen ertussen.
- **Weergave herstellen** (`R`): zet alles hierboven uit en past het model in beeld, zoals **Passend**,
  in één keer.

De opties blijven aan als je het volgende model opent, en werken samen (bijvoorbeeld röntgen en afsnijden).

## Je slicer kiezen {#choosing-your-slicer}

![Het venster Instellingen](screenshot-settings.png)

**Instellingen → Slicer → Standaardslicer.** Bij elke slicer staat *geïnstalleerd* of *niet gevonden*. Staat
de jouwe op een ongebruikelijke plek, klik dan op **Bladeren…** en kies het programmabestand. Voor een slicer
die niet in de lijst staat kies je **Ander programma…**, geef je hem een naam en kies je zijn `.exe`.

De groene knop krijgt de bijpassende naam ("Openen in OrcaSlicer"). Het kleine pijltje **▾** ernaast toont je
andere geïnstalleerde slicers, om een bestand één keer in een daarvan te openen.

## STL exporteren uit 3MF {#export-stl-from-3mf}

Met een 3MF-project open bewaart **STL exporteren** in de werkbalk (`Ctrl+E`) de objecten als gewone
STL-bestanden, bijvoorbeeld om een model te delen of te openen in een programma dat geen 3MF leest.

- Een venster toont elk object met zijn naam en aantal driehoeken, allemaal aangevinkt; vink uit wat je niet
  nodig hebt.
- **Het pijltje naast de knop** biedt elke manier direct: *Alle objecten als één STL*, *Eén STL per object*
  en *Objecten kiezen…* (het venster). Wat een klik doet, staat vetgedrukt.
- **Wat een klik doet** (en `Ctrl+E`) kies je in **Instellingen → Bestanden → STL exporteren**: de lijst
  met objecten tonen (standaard), alles opslaan als één STL, of één STL per object opslaan.
  *Wijzigen wat een klik doet…* onderaan het menu van het pijltje opent die instelling.
- **Eén gecombineerde STL**: de aangevinkte objecten in één bestand, op hun plek op de plaat.
- **Eén STL per object**: elk bestand krijgt de naam van zijn object en komt in een map die je kiest
  (PrintView3D vraagt het voordat het bestaande bestanden vervangt).
- Een bestand met maar één object gaat altijd direct naar het venster Opslaan.
- **Alleen de pure vorm:** modifiers, negatieve onderdelen en support-blokkers / -afdwingers worden
  weggelaten (zoals vastgelegd door Creality Print, OrcaSlicer, Bambu Studio en PrusaSlicer), en ook kleuren,
  materialen en printinstellingen. Maten zijn in millimeters; de bestanden zijn binaire STL.

## ZIP-bestanden {#zip-files}

Gedownloade modellen komen vaak als ZIP. Open die net als elk ander bestand (**Openen…** of sleep het naar het
venster); uitpakken hoeft niet.

<table>
<tr>
<td width="50%"><img src="../screenshot-zip-showall.png" alt="Vier modellen uit een ZIP naast elkaar, met de lijst van bestanden"><br><sub><b>Alles naast elkaar tonen</b>: vink elk model aan of uit; de G-code opent apart.</sub></td>
<td width="50%"><img src="../screenshot-zip-gcode.png" alt="De gesliceerde G-code uit dezelfde ZIP, met de lijst van bestanden"><br><sub>Klik op een bestand in de lijst, of gebruik ↑ / ↓: hier de gesliceerde G-code uit dezelfde ZIP.</sub></td>
</tr>
</table>

- **Alleen de 3D-bestanden worden gebruikt**: STL, 3MF, OBJ, PLY, OFF, glTF/GLB, STEP, FreeCAD en G-code.
  Afbeeldingen, pdf's, leesmij-bestanden, weblinks, ZIP's in de ZIP en de verborgen map `__MACOSX` worden
  overgeslagen, en het paneel zegt hoeveel.
- **Een ZIP met één 3D-bestand** opent precies zoals dat bestand.
- **Meer bestanden** staan in het zijpaneel met een gekleurd label voor hun soort (STL, 3MF, G-code, …) en
  een korte uitleg per soort. Het eerste bestand wordt getoond; klik op een ander, of gebruik **↑ / ↓**, om te
  wisselen.
- **Alles naast elkaar tonen** zet de modellen naast elkaar: tot drie op een rij, daarna een raster (vier als
  2 × 2, zes als 3 × 2, negen als 3 × 3, …), op afstand volgens hun echte grootte. Vink modellen uit in
  **Objecten** om ze te verbergen. G-code-, STEP- en FreeCAD-bestanden worden één voor één geopend.
- **Openen in slicer** stuurt het model dat je bekijkt; bij Alles tonen de aangevinkte modellen. Het pijltje
  naast de knop heeft **Alle modellen uit de ZIP versturen**.
- Een slicer opent een **3MF als eigen project**, en kan een 3MF dus niet samen met andere bestanden openen. Als
  er een 3MF tussen de modellen zit, vraagt PrintView3D wat je wilt sturen: het 3MF-project (met zijn platen
  en instellingen), de andere modellen op één plaat, of **alles als STL** (de objecten van het project worden
  een gewone STL, zodat alle modellen op één plaat komen).

    <img src="../screenshot-zip-send.png" alt="Het venster Naar slicer sturen: het 3MF-project, de andere modellen, of alles als STL" width="520">

De 3D-bestanden worden uitgepakt in de eigen cachemap van PrintView3D (slicers hebben echte bestanden nodig);
de groottes worden eerst gecontroleerd, zodat een beschadigde of kwaadaardige ZIP je schijf niet kan vullen.
Bestanden uit ZIP's die langer dan een dag geleden geopend zijn, worden automatisch opgeruimd.

## Taal {#language}

**Instellingen → Taal** zet het hele programma meteen om, ook de bestandsvensters en standaardknoppen. Engels
is de standaard; *Automatisch* volgt de taal van je systeem. Arabisch gebruikt een opmaak van rechts naar links;
maten gebruiken altijd westerse cijfers (0.20 mm).
Een fout of ontbrekend woord? De link op die pagina leidt naar [Zo vertaal je](TRANSLATING.md).

## Thema's {#themes}

Klik op het **palet-icoon** rechts in de werkbalk om een thema te kiezen, of druk op **`Ctrl+T`** voor het
volgende. Dezelfde keuze staat in **Instellingen → Uiterlijk → Thema**.

- **Automatisch** volgt de donker/licht-instelling van Windows of je Linux-bureaublad (en wisselt mee als die
  verandert).
- **Donker**, **Grijs**, **Grafiet** (een warme, donkerbruine tint die rustig is voor de ogen) of **Licht**.

Het wisselen gaat meteen; de 3D-achtergrond, de plaat en het raster veranderen mee, terwijl de kleuren van de
G-code en het model gelijk blijven, zodat ze altijd overeenkomen met je slicer.

![Het themamenu in de werkbalk](screenshot-theme-menu.png)

![Dezelfde G-code in de thema's Donker, Grijs, Grafiet en Licht](screenshot-themes.png)

### Venstertransparantie (Windows 11) {#window-transparency-windows-11}

**Instellingen → Uiterlijk → Venstertransparantie** laat de werkbalk, het zijpaneel en de statusbalk zien wat
achter het venster ligt, in elk thema:

- **Mica**: een zachte tint van je bureaubladachtergrond (zoals in Verkenner).
- **Acrylic**: matglas dat het bureaublad en andere vensters erachter vervaagt.
- **Uit** (standaard): dicht, zoals voorheen.

De 3D-weergave blijft altijd dicht. Het werkt na een herstart: als je op OK klikt, vraagt PrintView3D
**Nu herstarten** (het sluit en opent opnieuw, met hetzelfde bestand) of **Later**. Windows tekent het effect
zelf, toont een effen kleur als het venster niet actief is, en zet het uit als *Transparantie-effecten* uit
staan in Windows Instellingen of in de batterijbesparing. Windows 10 en andere systemen houden het gewone
uiterlijk.

## Updates {#updates}

**Instellingen → Updates** toont je versie en heeft **Nu controleren op updates**. Je kunt ook
**Automatisch controleren op updates (één keer per dag)** aanzetten; PrintView3D vraagt één keer of je dat
wilt, en je kunt het daar altijd wijzigen.

Is er een nieuwe versie, dan toont de versie rechtsonder een **rode stip** (`● v0.10.0 → 0.11.0`), en
*Updates* in Instellingen ook. Klik erop om **Wat is er nieuw** te zien, en daarna:

- **Windows (geïnstalleerd met Setup.exe): Update installeren.** PrintView3D downloadt de nieuwe installer,
  controleert de SHA-256-vingerafdruk tegen die van GitHub, installeert hem (zonder vragen, je instellingen
  blijven bewaard) en start de nieuwe versie.
- **Linux (AppImage) en de draagbare Windows-zip: Update downloaden** opent de pagina van de nieuwe versie;
  download het nieuwe bestand en vervang het oude.
- **Deze versie overslaan** verbergt die versie; de volgende wordt weer getoond.

Na een update toont de eerste start één keer **Wat is er nieuw** voor de versie die je nu hebt, hoe je ook
bijgewerkt hebt (installer, winget, zip of AppImage). Het komt uit het wijzigingslogboek dat bij het programma
zit, dus er is geen verbinding voor nodig. Na een nieuwe installatie verschijnt het niet.

![Instellingen → Updates als er een nieuwe versie is](screenshot-updates.png)

### Updates en privacy {#updates-and-privacy}

PrintView3D werkt offline. Het maakt **alleen** verbinding met internet voor updates, en alleen als je op
*Nu controleren op updates* klikt of de dagelijkse controle hebt aangezet:

| | |
|---|---|
| **Waarmee verbinding wordt gemaakt** | `api.github.com` (om naar de nieuwste versie van dit project te vragen) en, als je op *Update installeren* klikt, de download van `github.com` |
| **Hoe vaak** | Hooguit één keer per dag (automatische controle), of als je op *Nu controleren op updates* klikt |
| **Wat er verstuurd wordt** | Alleen de vraag naar de nieuwste versie, met de naam en versie van het programma (`PrintView3D/0.10.0`). Geen persoonlijke gegevens, geen bestanden, geen gebruiksstatistieken, geen ID. |
| **Wat GitHub ziet** | Zoals bij elke website: je IP-adres. Zie de [privacyverklaring van GitHub](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement). |
| **Uitzetten** | Instellingen → Updates → vink *Automatisch controleren op updates* uit. Daarna wordt nergens meer verbinding mee gemaakt. |

## Soepeler draaien op laptops {#smoother-rotation-on-laptops}

Veel laptops hebben twee grafische chips en laten programma's standaard op de langzaamste draaien.
**Instellingen → Weergave → Grafische kaart** toont welke PrintView3D gebruikt. Staat er *Intel*, vink dan
**De krachtige videokaart gebruiken** aan en klik op OK; kies **Nu herstarten** (of **Later**, dan wisselt het
de volgende keer dat je PrintView3D start).

## Opmerkingen en beperkingen {#notes-and-limits}

- Windows 10/11 en Linux (x86-64) worden verpakt en getest. De Mac-versies (Apple silicon en Intel, macOS 14.4+)
  zijn in [bèta](install.md#macos). Linux op ARM (Raspberry Pi enz.) wordt nog niet verpakt.
- Een 3MF-*project* dat in een slicer van het ene merk is opgeslagen, kan zijn printer- en printinstellingen
  verliezen als het in een slicer van een ander merk wordt geopend. Het model zelf laadt gewoon; zo gedragen
  de slicers zich.
- Binaire G-code (`.bgcode`) wordt nog niet ondersteund.
- Miniaturen in Verkenner zijn er voor 3MF-, STL-, G-code- en FreeCAD-bestanden; nog niet voor OBJ, PLY, OFF en
  glTF.
- FreeCAD-documenten hebben een geïnstalleerde FreeCAD nodig voor de 3D-weergave (PrintView3D bevat de
  geometrie-engine van FreeCAD niet). Heel oude of heel nieuwe FreeCAD-versies openen elkaars bestanden soms
  niet.

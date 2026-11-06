# In je modellen kijken

Holle wanden, verborgen onderdelen, kanalen, schroefgaten: met de knop **Weergave** in de werkbalk kijk
je in een model voordat je het print. Het werkt voor STL, 3MF, OBJ en de andere modelformaten (G-code
heeft hiervoor de laagschuifregelaar). De knop opent het onderdeel **Weergave** in het zijpaneel, met
elke optie als knop: Draadmodel, Röntgen, Van boven afsnijden en Afsnijden vanaf jouw kant. De
instellingen van een snede (de schuif, het weggesneden deel, het snijvlak en bevriezen) verschijnen
daar zolang de snede aan staat, en het onderdeel eindigt met **Weergave herstellen** en **Sluiten**.
Een knop die aan staat is donkerder, zodat je meteen ziet wat actief is.
*Nieuw in PrintView3D 0.25; het onderdeel Weergave is nieuw in 0.28.*

<video class="pv-video" src="../assets/inside/clip-facing.mp4" poster="../assets/inside/clip-facing.jpg"
       autoplay loop muted playsinline preload="metadata"
       aria-label="Een pomphuis draait door een rechtopstaande snede: de kamer, de waaier, de holte en het uitlaatkanaal worden zichtbaar"></video>

## Afsnijden vanaf jouw kant

Een rechtopstaande snede die altijd naar je toe gericht is en het deel van het model ervoor verbergt.
**Draai de weergave en het model draait door de snede**; verschuif (pan) de weergave en het schuift
erlangs, alsof je het model voor een scanner houdt. Voor een snede recht van voren of van opzij klik je
dat vlak op de weergavekubus aan.

De schuifregelaar in het zijpaneel zet de snede dichterbij of verder weg; **Diepte** toont hoe ver de
snede in het model zit, van de totale diepte van het model in die richting. **Snijvlak bevriezen**
houdt de snede op haar plaats, zodat je het model kunt draaien en verschuiven zonder dat de snede
meedraait. De binnenkant van de wanden die de snede openlegt is rood, dus bij een massief onderdeel zie
je het snijvlak.

![De snede en de schuifregelaar in het zijpaneel](assets/inside/clip-facing.nl.png)

## Van boven afsnijden

Verbergt alles boven een hoogte, zoals de laagschuifregelaar dat bij G-code doet. Schuif de regelaar in
het zijpaneel om laag voor laag door het model omlaag te gaan.

<video class="pv-video" src="../assets/inside/clip-top.mp4" poster="../assets/inside/clip-top.jpg"
       autoplay loop muted playsinline preload="metadata"
       aria-label="Een snede gaat omlaag door het pomphuis en weer omhoog"></video>

## Zie wat de snede wegneemt

Wat een snede verbergt blijft zichtbaar als een witte, doorzichtige **schim** met omlijnde randen,
en het **snijvlak** verschijnt als een vaag vlak zo groot als het model, zodat je ziet wat de snede
wegneemt en waar. Onder de schuiven zetten **Weggesneden deel tonen** en **Snijvlak tonen** elk aan
of uit (eerst allebei aan; je keuze wordt onthouden). In **Instellingen → Weergave** hebben
**Weggesneden deel** en **Snijvlak** elk een schuif Vager … Sterker, en de 3D-weergave verandert
terwijl je sleept. *Nieuw in PrintView3D 0.26.*

## Beide sneden tegelijk

<kbd>T</kbd> en <kbd>Y</kbd> zetten elk hun eigen snede aan en uit, dus beide kunnen tegelijk aan
staan: het model houdt dan alleen over wat beide sneden overlaten, een hoek eruit gesneden. Het
zijpaneel heeft voor elk een schuif, **Hoogte** en **Diepte**. Wat de sneden verbergen blijft
zichtbaar als één gelijkmatige, doorzichtige schim, en elk snijvlak stopt waar de andere snede is.
**Weergave herstellen** zet beide sneden uit; dezelfde toets (of knop) nog eens alleen die ene.
*Nieuw in PrintView3D 0.27.*

## Röntgen

De onderdelen worden doorzichtig, zodat onderdelen in andere onderdelen, holtes, kanalen en schroefgaten
zichtbaar worden, van alle kanten.

<video class="pv-video" src="../assets/inside/xray.mp4" poster="../assets/inside/xray.jpg"
       autoplay loop muted playsinline preload="metadata"
       aria-label="Het pomphuis doorzichtig en draaiend: de waaier en de kanalen erbinnen"></video>

De opties werken samen, bijvoorbeeld röntgen met een snede:

![Röntgen en van boven afsnijden samen](assets/inside/xray-clip.nl.png)

## Draadmodel

De driehoeken van het mesh: om te zien hoe fijn een model is, of om kapotte geometrie te vinden.

![Het pomphuis als draadmodel](assets/inside/wireframe.png)

## De maat van elk object

De lijst **Objecten** toont van elk object de maat (X × Y × Z) naast de naam; de maat van het hele model
staat bij **Details**. Vink een object uit om het te verbergen.

![De lijst Objecten met de maat van elk object](assets/inside/objects.nl.png)

## Meten

De knop **Meten** naast **Weergave** (of <kbd>M</kbd>) opent het onderdeel Meten. Kies met de knoppen
daarin wat je meet:

- **Afstand**: klik op twee punten. De lijn volgt de muis en de afstand staat ernaast. Vink
  **ΔX ΔY ΔZ tonen** aan om onder elke afstand de afstand langs elke as te schrijven, handig voor
  "hoe hoog van hier tot daar".
- **Hoek**: klik op een punt op de ene zijde, de hoek, en dan een punt op de andere zijde.
- **Cirkel**: klik op drie punten op de rand van een cirkel of gat voor de diameter en de straal.

Zolang Meten aan staat, staat onderaan de 3D-weergave hoe het gekozen gereedschap werkt. Een klik zet
een punt, slepen draait nog steeds de weergave, zodat je het model tussen de punten kunt draaien.
Voltooide metingen blijven staan met hun waarde ernaast, en de volgende klik begint een nieuwe;
**Wissen** haalt ze allemaal weg. Sleep een geplaatst punt om het te verplaatsen. **Magnetisch
uitlijnen** (bij elke start aan) springt naar de dichtstbijzijnde hoek, het midden van een rand of een
punt op een rand. **Stippellijn** tekent de lijnen gestippeld. Hoe dik de lijnen zijn, stel je in bij
**Instellingen → Weergave** (**Meetlijnen**). Waarden die elkaar zouden overlappen, zoals bij
concentrische cirkels, komen boven elkaar te staan. **Weergave herstellen** laat je metingen staan.
*Nieuw in PrintView3D 0.28.*

![Een afstand met ΔX ΔY ΔZ, een rechte hoek en de diameter van de inlaat, gemeten op het pomphuis](assets/inside/measure.nl.png)

## Kleuren en het zijpaneel

De lijst **Objecten** staat bovenaan in het zijpaneel en **Details** onderaan; klik op *Details* om ze
in te klappen (de keuze wordt onthouden). Bovenaan zie je het bestandstype en de grootte. Klik op het
kleurvak van een object om alleen dat object een andere kleur te geven; rechtsklik zet de kleur uit het
bestand terug. Gekozen kleuren worden niet opgeslagen: na een herstart is alles weer zoals het was.
*Nieuw in PrintView3D 0.28.*

![Het huis en de waaier in zelfgekozen kleuren, met röntgen](assets/inside/colors.nl.png)

## Afstanden op het raster

**Instellingen → Weergave → Afstanden (mm) langs het raster tonen** (standaard uit) schrijft kleine
getallen in millimeters langs de printplaat, op de hoofdlijnen van het raster: elke 50 mm bij een
gewone plaat, minder bij een grote plaat zodat er een paar leesbare getallen overblijven. Ze staan net
buiten de twee randen die het dichtst bij je zijn, in de kleur van het raster, blijven rechtop hoe je
ook kijkt, en verdwijnen als je van onder de plaat kijkt. Bij het oneindige raster volgen ze het gebied
rond het model. **Afstand tussen de getallen** kiest een andere afstand, van 5 tot 100 mm, in plaats
van de automatische. *Nieuw in PrintView3D 0.28.*

![Afstanden in millimeters langs de randen van de printplaat](assets/inside/grid-numbers.png)

## Toetsen

| Toets | |
|---|---|
| <kbd>W</kbd> | Draadmodel aan / uit |
| <kbd>X</kbd> | Röntgen aan / uit |
| <kbd>T</kbd> | Van boven afsnijden aan / uit |
| <kbd>Y</kbd> | Afsnijden vanaf jouw kant aan / uit |
| <kbd>R</kbd> | Weergave herstellen: draadmodel, röntgen en de sneden uit, model passend (metingen blijven) |
| <kbd>M</kbd> | Meten aan / uit |

De opties blijven aan als je het volgende model opent.

## Probeer het zelf

Het pomphuis op deze pagina is
[`examples/demo_housing.3mf`](https://github.com/sevagjb/PrintView3D/raw/main/examples/demo_housing.3mf)
in de broncode: download het en open het in PrintView3D.

Deze functies zijn voorgesteld door [@covrig](https://github.com/covrig), die ook Meten, het onderdeel
Weergave, de objectkleuren en de getallen op het raster heeft gebouwd
([#59](https://github.com/sevagjb/PrintView3D/issues/59),
[#60](https://github.com/sevagjb/PrintView3D/issues/60)). Heb je ook een idee?
[Open een issue](https://github.com/sevagjb/PrintView3D/issues/new/choose).

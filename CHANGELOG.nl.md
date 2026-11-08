# Changelog

## 0.30.1
- **Opgelost: G-code van Creality Print had geen voorbeeldafbeelding**, op de startpagina en in het
  zijpaneel. Creality Print schrijft de grootte van de afbeelding als `300*300` of `300 300`, en dat
  werd niet herkend.
- **ZIP-bestanden krijgen een voorbeeld** op de startpagina: de foto of render van de maker die erin
  zit, en anders de afbeelding van de eerste 3MF of G-code erin. Alleen die ene afbeelding wordt
  gelezen.
- **Opgelost: bestandsnamen op de startpagina**: een lange naam zonder spaties werd afgekapt aan de
  rand van het voorbeeldkaartje in plaats van door te lopen op een tweede regel, en een `&` in een
  naam verscheen als onderstreepte letter in de lijst met recente bestanden en het menu Recent.
- **Instellingen → Weergave** staat nu in vier vakken: **Printplaat**, **Meten, weergave en
  controleren** (was *Overig*), het nieuwe **Startpagina**, en **Grafische kaart**. Met
  **Startpagina** zet je het voorbeeldkaartje uit; dan wordt geen enkel bestand gelezen tot je het
  opent (handig bij een trage netwerkschijf).

## 0.30.0
- **Kies je werkbalk** (**Instellingen → Werkbalk**, ook **☰ → Werkbalk aanpassen…** of klik met rechts
  op de werkbalk): verberg de knoppen die je niet gebruikt: Start, Openen, Controleren, Weergave,
  Meten, Schermafbeelding, Thema en Instellingen. Het **☰**-menu, Openen in slicer, STL exporteren,
  Plaat en Passend blijven altijd staan. De volgorde verandert nooit, verborgen knoppen houden hun
  toets, en het **☰**-menu heeft nu ook Controleren, Weergave, Meten en het themamenu.
  [Bekijk hoe het werkt](https://sevagjb.github.io/PrintView3D/nl/use.html#toolbar-buttons).
- **Kortere weergaveknoppen** (zelfde pagina): toon Plaat, Controleren, Weergave, Meten en Passend als
  *Plaat (P)*, *Plaat*, *P* of alleen pictogrammen, en voeg ze desgewenst samen tot één aaneengesloten
  groep. Elke wijziging is meteen te zien; **OK** houdt hem, **Annuleren** gaat terug.
- **Werkbalkknoppen lichten op onder de muis**: het vlak vult zich met de hoofdkleur van het thema
  (amber in Ember, cyaan in de andere thema's), net als de weergavekubus. Het tandwiel van Instellingen
  is nu oranje in Ember, net als Schermafbeelding en Thema ernaast.
- **Website**: de schermafbeeldingen volgen het thema van de website (Licht, Donker of Ember).
- **Onder de motorkap**: ongebruikte code verwijderd.

## 0.29.1
- **Opgelost**: bij **Model controleren** konden overhangen die in of onder het model verborgen zitten
  erdoorheen zichtbaar zijn, op sommige grafische kaarten meer dan op andere. Van onderen worden ze
  precies zo gekleurd als eerst.
- **Instellingen blokkeert het hoofdvenster niet meer**: je kunt het model blijven draaien en bekijken
  terwijl het open is. Nog eens openen haalt het open venster naar voren.
- **Muisaanwijzers** laten zien wat de muis doet: draaiende pijlen bij draaien, vier pijlen bij
  verschuiven (pannen) en een vergrootglas bij zoomen.
- **Schermafbeeldingen direct in een map** (**Instellingen → Bestanden → Schermafbeeldingen**, standaard
  uit): elke afbeelding wordt meteen opgeslagen, genoemd naar het bestand en de tijd, zonder te vragen
  waar.
- **Instellingen → Weergave** staat nu in drie vakken: **Printplaat**, **Overig** en **Grafische kaart**.
- **Met dank aan [@covrig](https://github.com/covrig)** voor het vinden van de fout en het bouwen van dit
  alles in [#82](https://github.com/sevagjb/PrintView3D/pull/82).

## 0.29.0
- **Controleren voor het printen** (`C`, de nieuwe knop **Controleren** tussen Plaat en Weergave):
  het onderdeel **Model controleren** kleurt wat bij het printen problemen kan geven, met een aantal
  per controle: **Overhangen** steiler dan een hoek die je kiest (standaard 45°), **Dunne wanden**
  dunner dan je nozzle (standaard 0,4 mm, op de achtergrond gecontroleerd) en **Meshproblemen**:
  gaten, verwarde (non-manifold) randen, binnenstebuiten gekeerde vlakken en kleine losse delen. Een
  rode stip markeert de gevonden problemen, en de kleuren volgen de sneden en de objecten die je
  verbergt.
- **Millimeter of inch** (**Instellingen → Taal en eenheden → Lengtes in**): afmetingen, metingen,
  sneden, het raster en de plaat volgen het allemaal. Bestanden veranderen niet.
- **Je eigen sneltoetsen** (**Instellingen → Toetsenbord en muis**): geef elke actie van het
  hoofdvenster een andere toets, of geen. Toetsen die het systeem gebruikt worden geweigerd, met de
  reden erbij, en **Standaardwaarden herstellen** zet ze allemaal terug. Knoppen en tooltips tonen hun
  toets, en veranderen mee als je die wijzigt.
- **Nieuwe toetsen**: `C` Controleren, `V` het onderdeel Weergave, `P` de plaat, `S` Instellingen,
  `L` snede vastzetten, `D` · `A` · `O` een afstand, hoek of cirkel meten, `K` haalt alle metingen
  weg, `Ctrl+Shift+S` slaat een schermafbeelding op. **Van boven afsnijden** is nu `T` en
  **Afsnijden vanaf jouw kant** `Y` (dat waren `C` en `V`); in Instellingen kun je ze terugzetten.
- **Map openen…** (in het menu **☰**): zet de 3D-bestanden van een map in het zijpaneel; ga erdoor
  met `↑` / `↓` of een klik. **Openen…** heet nu **Bestand of ZIP openen…**.
- **Meten in het model**: met een snede aan springt Meten ook naar de omtrek van de snede, zodat je
  wanden en gaten in het model kunt meten.
- **Snede vastzetten** (`L`) vervangt *Snijvlak bevriezen*. Zolang de snede vanaf jouw kant niet vastzit,
  waarschuwt het onderdeel Meten je, want punten die op de snede gemeten zijn blijven achter als de
  weergave draait.
- **De sneden in de 3D-weergave slepen** (**Instellingen → Weergave**, standaard uit): elk snijvlak
  krijgt een ronde greep; sleep eraan en de snede en haar schuif gaan mee.
- **Het raster**: kies de afstand van de fijne en de hoofdlijnen (of laat het op Automatisch); de
  schaalgetallen tellen vanaf de linkervoorhoek van de plaat (0), dus geen negatieve getallen meer, en
  ze volgen de zoom. Nieuw in **Instellingen → Weergave**: **de X-, Y- en Z-as op de printplaat**, en
  beide snijvlakken heel tekenen als beide sneden aan staan.
- **Startpagina**: houd de muis boven een recent bestand en je ziet de voorbeeldafbeelding, de naam en
  de map.
- **Instellingen**: een tandwielknop in de werkbalk, een knop **Toepassen** die opslaat zonder te
  sluiten, en het venster opent weer op de pagina die je het laatst gebruikte.
- **Verder veranderd**: **Passend** (`F`) past alleen de camera aan; **Weergave herstellen** en het
  sluiten van het onderdeel Weergave zetten ook de weergave-opties uit. De opties van Weergave en
  Meten zijn aan/uit-knoppen. Tooltips verschijnen sneller en blijven binnen het venster.
- **Opgelost**: het raster van de plaat dat door het model heen te zien was (uitgezoomd, na
  Controleren of van onderen gezien); de lijn waar de twee snijvlakken elkaar raken blijft nu binnen
  de vlakken; een ander bestand openen of **Alles naast elkaar tonen** wist nu metingen en sneden.
- **Met dank aan [@covrig](https://github.com/covrig)**, die dit allemaal heeft gebouwd in [#80](https://github.com/sevagjb/PrintView3D/pull/80).

## 0.28.0
- **Meten** ([#59](https://github.com/sevagjb/PrintView3D/issues/59), `M`, de nieuwe knop naast **Weergave**): **Afstand** (met
  **ΔX ΔY ΔZ tonen** voor de afstand langs elke as), **Hoek** en **Cirkel** (diameter en straal). Een
  klik zet een punt, slepen draait nog steeds de weergave, en een geplaatst punt kun je verslepen.
  Punten springen naar hoeken, het midden van een rand en randen. Bij elke meting staat de waarde,
  meerdere metingen kunnen blijven staan, en **Wissen** haalt ze weg. Desgewenst stippellijnen, en een
  schuif voor de dikte van de **Meetlijnen** in **Instellingen → Weergave**.
- **Het onderdeel Weergave**: de knop **Weergave** opent een onderdeel in het zijpaneel met elke optie
  als knop, en een knop die aan staat is donkerder. De schuiven en vinkjes van het afsnijden horen erbij,
  met **Weergave herstellen** en **Sluiten** onderaan. Nieuw: **Snijvlak bevriezen** houdt de snede
  van Afsnijden vanaf jouw kant op haar plaats terwijl je het model draait en verschuift, en **Diepte**
  toont nu hoe ver de snede in het model zit, bijvoorbeeld *Diepte 22,0 van 44,0 mm*.
- **Objectkleuren**: klik op het kleurvak van een object in de lijst **Objecten** om het een andere
  kleur te geven; rechtsklik zet de kleur uit het bestand terug. Niet opgeslagen.
- **Een overzichtelijker zijpaneel**: **Objecten** bovenaan, **Details** onderaan en inklapbaar, en het
  bestandstype en de grootte bovenaan.
- **Afstanden op het raster** ([#69](https://github.com/sevagjb/PrintView3D/issues/69)): **Instellingen → Weergave → Afstanden (mm) langs het
  raster tonen** (standaard uit) schrijft millimeters langs de printplaat, met een automatische of een
  zelfgekozen afstand.
- **Hints in de 3D-weergave**: hoe het gekozen meetgereedschap werkt, en hoe je het model door een snede
  haalt, staat nu onderaan de 3D-weergave.
- **Nieuwe pictogrammen** voor Plaat, Weergave, Meten en Passend; Passend staat nu direct na Meten.
- **Met dank aan [@covrig](https://github.com/covrig)**, die dit allemaal heeft gebouwd in [#77](https://github.com/sevagjb/PrintView3D/pull/77): zijn eerste
  pull request voor PrintView3D.

## 0.27.0
- **Beide sneden tegelijk** ([#70](https://github.com/sevagjb/PrintView3D/issues/70)): **Van boven afsnijden** (`C`) en **Afsnijden vanaf jouw kant** (`V`)
  kunnen nu samen aan, voor een hoek eruit gesneden. Elke toets zet zijn eigen snede aan en uit, en het
  zijpaneel heeft voor elk een schuif, **Hoogte** en **Diepte**. Het weggesneden deel blijft één
  gelijkmatige schim, nooit donkerder waar de sneden elkaar overlappen, en elk snijvlak stopt waar de
  andere snede is. **Uitzetten** en **Weergave herstellen** zetten beide uit.
- **Met dank aan [@covrig](https://github.com/covrig)** voor het idee en de vraag om een gelijkmatige schim.

## 0.26.0
- **Zie wat een snede wegneemt** ([#66](https://github.com/sevagjb/PrintView3D/issues/66)): bij **Van boven afsnijden** of **Afsnijden vanaf jouw kant**
  blijft het deel dat de snede verbergt zichtbaar als een witte, doorzichtige schim met omlijnde randen,
  en het snijvlak verschijnt als een vaag vlak zo groot als het model. Twee vinkjes onder de schuif zetten
  elk aan of uit, en **Instellingen → Weergave** heeft voor elk een schuif Vager … Sterker.
- **Weergave herstellen** (`R`, in het menu **Weergave**): zet draadmodel, röntgen en de sneden uit en
  past het model in beeld, in één keer.
- **Een rustigere werkbalk**: **Recent** staat in het menu **☰** en op de startpagina; Start en Openen blijven.
- **macOS: Quick Look** (bèta, [#68](https://github.com/sevagjb/PrintView3D/issues/68)): de Finder toont miniaturen van 3MF-, STL-, G-code-, FreeCAD-, OBJ-
  en PLY-bestanden, en de spatiebalk toont STL-, 3MF-, OBJ- en PLY-modellen in 3D.
  [Zo zet je het aan](https://sevagjb.github.io/PrintView3D/nl/install.html).
- **Met dank aan [@covrig](https://github.com/covrig)** voor de ideeën voor de schim, de werkbalk en Weergave herstellen en al het
  testen, en aan [@bmorgenthaler](https://github.com/bmorgenthaler) voor het idee van Quick Look.

## 0.25.1
- **Opgelost**: de ronde knop van de afsnij- en laagschuif werd aan de boven- en onderkant afgesneden
  ([#66](https://github.com/sevagjb/PrintView3D/issues/66)); hij is nu een hele cirkel, in elk thema.
- **Website**: in het thema Ember kleuren de tabbladen bovenaan blauwgroen als je ze aanwijst, net
  als de knoppen.
- **Met dank aan [@covrig](https://github.com/covrig)** voor het opmerken van de schuif.

## 0.25.0
- **In je modellen kijken: de knop Weergave** ([#60](https://github.com/sevagjb/PrintView3D/issues/60)), voor modellen (STL, 3MF, OBJ, …; G-code houdt
  de laagschuif): **Draadmodel** (`W`), **Röntgen** (`X`, doorzichtig), **Van boven afsnijden** (`C`)
  met een hoogteschuif in het zijpaneel, en **Afsnijden vanaf jouw kant** (`V`): een rechtopstaande
  snede die altijd naar je toe gericht is. Draai de weergave en het model draait door de snede;
  verschuif (pan) de weergave en het model schuift erlangs. De wanden die een snede openlegt zijn rood.
  De opties werken samen en blijven aan voor het volgende model. [Bekijk het in actie](https://sevagjb.github.io/PrintView3D/nl/inspect.html).
- **De maat van elk object** ([#59](https://github.com/sevagjb/PrintView3D/issues/59)): de lijst **Objecten** toont van elk object de maat (X × Y × Z)
  naast de naam; het aantal driehoeken staat in de tooltip.
- **Opgelost**: het zijpaneel kon links worden afgesneden in het Arabisch, en bij lange woorden of grote
  letters in het Nederlands, Duits en Roemeens.
- **Nederlands en Arabisch** zijn nu helemaal nagekeken door een moedertaalspreker.
- **Website**: een nieuwe pagina, [In je modellen kijken](https://sevagjb.github.io/PrintView3D/nl/inspect.html),
  met korte video's, en een keuze uit Licht, Donker en Ember, zoals in het programma.
- **Met dank aan [@covrig](https://github.com/covrig)** voor beide ideeën en voor het testen op Windows.

## 0.24.0
- **Plaatmenu, voor modellen groter dan de plaat** ([#61](https://github.com/sevagjb/PrintView3D/issues/61)): de knop **Plaat** heeft een klein pijltje
  met vier keuzes, ook in **Instellingen → Weergave → Printplaat**:
  **Plaat van de printer (uit het bestand)**, de standaard; **Meegroeien met het model**: de plaat van de
  printer, alleen groter als het model erbuiten steekt; **Eigen formaat…**: je eigen breedte × diepte in mm;
  **Oneindig raster**: een eindeloze vloer die in de verte vervaagt. Een klik op de knop zelf toont of
  verbergt de plaat nog steeds, en je keuze wordt onthouden.
- **Objecten hoger in het paneel** ([#62](https://github.com/sevagjb/PrintView3D/issues/62)): het vak **Objecten** staat nu direct onder de afbeelding, vóór
  **Details**. Lange details, zoals de beschrijving van een MakerWorld- of Printables-project, tonen hun
  eerste 4 regels en een link **Meer tonen**. Met meer dan 10 objecten scrolt de lijst in zijn eigen vak.
- **Voorbeeldafbeelding inklappen** ([#62](https://github.com/sevagjb/PrintView3D/issues/62)): een klik op **▾ Voorbeeldafbeelding** boven de afbeelding
  klapt hem in en weer uit; zo blijft het ook bij de volgende bestanden.
- **Zelf bouwen** vraagt nu Python 3.12 tot 3.14: de bouwscripts zeggen dat duidelijk en vervangen een
  `.venv` die met een oudere Python is gemaakt. Ze installeren ook alleen de delen van Qt die PrintView3D
  gebruikt (PySide6-Essentials), zo'n 175 MB minder downloaden.
- **Met dank aan [@covrig](https://github.com/covrig)** voor beide ideeën, het snelle testen op Windows en de bouwoplossingen.

## 0.23.0
- **Weergavekubus in een nieuw jasje**: doorzichtige vlakken, dunne randen en een gestippelde ring.
  Het deel onder de muis licht op in de hoofdkleur van het thema (amber in Ember, cyaan in de andere thema's).
- **Pijlen en Startweergave op de weergavekubus**: met de muis boven de kubus draaien ◀ ▶ het model naar de
  volgende stand van 45° en kantelen ▲ ▼ het 45° richting **Boven** of **Onder**; **Startweergave** (het huisje) gaat terug
  naar de passende Iso-weergave. Weergavewissels draaien nu vloeiend in plaats van te springen; een klik
  of sleepbeweging stopt het draaien.
- **Een nog rustigere werkbalk**: met de weergavekubus aan zit Iso ook op de kubus (Startweergave), dus de
  werkbalk houdt **Passend** en **Plaat**. De toets `1` werkt nog steeds, en Iso komt samen met Boven,
  Voor en Rechts terug wanneer de kubus wordt uitgeschakeld in **Instellingen → Weergave**.
- **Wat is er nieuw in het menu**: **Menu → Wat is er nieuw** toont op elk moment de notities van deze
  versie, met een knop naar alle wijzigingen op GitHub.
- **Wat is er nieuw in het Arabisch en Nederlands**: de notities worden in je eigen taal getoond waar ze
  vertaald zijn, anders in het Engels. Vertalers: zie [docs/TRANSLATING.md](docs/TRANSLATING.md).
- **Opgelost**: een dubbelklik in de 3D-weergave (bijvoorbeeld twee snelle klikken op de weergavekubus)
  kon de muisbediening uitschakelen: de weergavekubus werkte niet meer en draaien voelde anders aan
  totdat PrintView3D opnieuw werd gestart.

## 0.22.0
- **Thema's: vier stijlen, elk licht en donker.** Kies **Standaard**, **Grijs**, **Grafiet** of
  **Ember**, en **Licht**, **Donker** of **Systeem** (volgt je computer en schakelt mee).
  Nieuw zijn Grijs en Grafiet overdag. **Instellingen → Uiterlijk** heeft een Licht / Donker / Systeem-kiezer en
  een afbeeldingskaart voor elke stijl; het paletmenu in de werkbalk vermeldt de stijlen en vervolgens de modi.
  `Ctrl+T` gaat naar de volgende stijl, de nieuwe `Ctrl+Shift+T` schakelt tussen licht en donker.
  Het thema dat je nu gebruikt blijft behouden. [Details](README.md#themes).
- **Weergavekubus** in de rechterbovenhoek van de 3D-weergave: klik op een vlak om het model vanaf die kant te bekijken
  (nu ook van achteren, links en van onderen), sleep de kubus om te draaien, sleep de ring eronder om te draaien
  zonder te kantelen. Schakel deze uit in **Instellingen → Viewer** als je deze niet wilt gebruiken.
- **Een rustigere werkbalk**: Boven, Voor en Rechts staan nu op de weergavekubus, dus de werkbalk behoudt Passend, Iso
  en Bouwplaat. De toetsen `2` `3` `4` werken nog steeds, en de knoppen komen terug wanneer de kubus wordt uitgeschakeld.
- **Ember Licht**: STL exporteren en de weergaveknoppen zijn gevuld met diep cyaan/donkerblauw, met witte tekst.
- **Venstertransparantie** (Windows 11) wordt gekozen met hetzelfde type kiezer: Uit, Mica of Acryl.
- **Opgelost**: na de weergave Boven kon het draaien van het model ervoor zorgen dat het verdween totdat op een weergaveknop werd gedrukt.

## 0.21.2
- **De eerste start toont PrintView3D zelf**, zonder vragen eroverheen. *Controleren op updates?*
  wordt gevraagd bij de tweede start en het GitHub-sterbericht verschijnt eenmalig bij de derde start. Er verandert niets
  voor mensen die bijwerken vanaf een oudere versie.
- **Linux: licht thema wanneer de desktop geen donkere instelling heeft.** Met *Automatisch* (de standaardinstelling voor nieuwe
  installaties) leest PrintView3D nu ook de GNOME-, GTK- en KDE-instellingen wanneer Qt het niet kan bepalen; als geen van
  hen 'donker' aangeeft, start het in het licht. Windows en macOS zijn ongewijzigd.
- **Linux: de AppImage kan zichzelf bijwerken** met [AppImageUpdate](https://github.com/AppImageCommunity/AppImageUpdate)
  en vergelijkbare tools: het bevat update-informatie, en elke release heeft een
  `PrintView3D-x86_64.AppImage.zsync` naast de AppImage, zodat alleen de gewijzigde onderdelen worden gedownload.

## 0.21.1
- **Nieuwe taal: Română (Roemeens)**, kies deze in **Instellingen → Taal**. Vertaald en beoordeeld
  door een moedertaalspreker. Met dank aan [@munteancd](https://github.com/munteancd)!

## 0.21.0
- **Startknop**: het pictogram van het huisje naast *Openen* (ook in het menu, `Ctrl+W`) sluit het bestand en
  gaat terug naar de startpagina met je recente bestanden. Het geheugen dat door het bestand werd gebruikt, wordt vrijgegeven.
- **Nieuwe thema's: Ember Licht en Ember Donker**, in crème, oranje en cyaan.
- **Kies een thema via een afbeelding**: **Instellingen → Uiterlijk** toont een kaart met een kleine afbeelding van
  PrintView3D in elk thema. Klik op een thema om het direct te zien; *OK* behoudt het, *Annuleren* gaat terug.
  Het themamenu in de werkbalk toont een kleur naast elk thema, en `Ctrl+T` doorloopt ze alle zes.
  [Details](README.md#themes).

## 0.20.0
- **STL exporteren uit FreeCAD en STEP-bestanden**: zodra FreeCAD het bestand in 3D heeft getoond, slaat **STL exporteren**
  (`Ctrl+E`) de solids op als gewone STL-bestanden, net zoals het doet voor 3MF-projecten: alles in één bestand,
  of één bestand per solid.
- **De knop STL exporteren heeft een pijl** (zoals *Openen in slicer*) met alle opties tegelijk:
  *Alle objecten als één STL*, *Eén STL per object* en *Objecten kiezen…*.
  [Details](README.md#export-stl-from-3mf).
- **Kies wat een klik doet** in **Instellingen → Bestanden → STL exporteren**: toon de lijst met objecten
  (zoals voorheen), sla alles op als één STL, of sla één STL per object op. `Ctrl+E` doet hetzelfde.
- **macOS**: het drukken op **OK** in Instellingen sloeg niets op en toonde een foutmelding; opgelost.

## 0.19.2
- **macOS voor Intel Macs** (beta): `PrintView3D-macOS-Intel.dmg`, naast de Apple silicon-versie.
  Beide vereisen **macOS 14.4 (Sonoma) of nieuwer**; de build controleert dit nu voor elk bestand in de app,
  en start de app op een echte macOS 14 Mac
  (eerdere opmerkingen vermeldden macOS 12, wat de huidige Qt-versie niet langer ondersteunt).
- **Nederlandse** vertaling volledig beoordeeld.
- **Website** ook in het Nederlands: [sevagjb.github.io/PrintView3D](https://sevagjb.github.io/PrintView3D/nl/).
- Gebruikt weer Qt for Python (PySide6) 6.12; 0.19.1 was per ongeluk gebouwd met het oudere 6.9.

## 0.19.1
Veiligheidsupdate. Met dank aan een beoordeling van hoe PrintView3D omgaat met bestanden van het internet:
- **glTF-bestanden** kunnen PrintView3D niet langer bestanden buiten de eigen map van het model laten lezen. Een
  kwaadwillend bestand zou elk bestand op de computer kunnen noemen, of op Windows een netwerkshare, wat
  Windows contact zou laten maken met een externe server enkel door het bestand te openen.
- **Updates** worden alleen geïnstalleerd wanneer GitHub de SHA-256-vingerafdruk van het installatiebestand geeft en deze
  overeenkomt, en het installatiebestand wordt alleen gedownload van de releases van dit project op GitHub.
- **3MF- en FreeCAD-bestanden** krijgen dezelfde bescherming als ZIP-bestanden: een onderdeel dat zou uitpakken tot veel
  meer gegevens dan een 3D-bestand nodig heeft, wordt geweigerd in plaats van het geheugen te vullen.
- **ZIP-bestanden**: namen die Windows niet kan gebruiken (met `:`, `CON`, …) worden veilig gemaakt bij het uitpakken,
  en een gedeeltelijk uitgepakt bestand wordt verwijderd wanneer het uitpakken mislukt.
- **Verkenner-miniaturen**: STL-bestanden met absurde coördinaten of miljoenen reusachtige driehoeken
  kunnen de Verkenner niet langer bezighouden.
- **Linux**: de menu-ingang werkt ook wanneer de map van het programma `$`, `%` of `\` in de naam heeft.
- Nieuw: [SECURITY.md](SECURITY.md) legt uit hoe je een beveiligingsprobleem privé kunt melden.

## 0.19.0
- **ZIP-bestanden openen**: open een gedownload modelpakket (Printables, Thingiverse, …) zoals elk ander
  bestand, zonder het eerst uit te pakken. Alleen de 3D-bestanden worden gebruikt (STL, 3MF, OBJ, PLY, OFF, glTF,
  STEP, FreeCAD en G-code); afbeeldingen, documenten, links en andere bestanden worden overgeslagen. Een ZIP met één
  3D-bestand opent net zoals dat bestand. [Details](README.md#zip-files).
- **De bestanden in een ZIP** worden in het zijpaneel vermeld met een gekleurd label voor hun type en een
  korte uitleg van elk type. Klik op een bestand, of gebruik **↑ / ↓**, om te wisselen.
- **Toon alles naast elkaar** plaatst de modellen van een ZIP naast elkaar: tot drie op één rij,
  vervolgens een raster (vier als 2 × 2, zes als 3 × 2, …), gespatieerd op hun werkelijke grootte. Vink een model uit om het te verbergen.
  G-code-, STEP- en FreeCAD-bestanden openen één voor één.
- **Meerdere modellen verzenden**: Openen in slicer verzendt de aangevinkte modellen, en de pijl ernaast heeft
  **Stuur alle modellen in de ZIP**. Een slicer opent een 3MF als een op zichzelf staand project, dus wanneer een 3MF zich
  onder hen bevindt, vraagt PrintView3D wat er verzonden moet worden: het 3MF-project, de andere modellen, of alles als STL
  op één bouwplaat.
- **Nieuwe werkbalk**: Menu, Openen en Recent als pictogrammen aan de linkerkant; Schermafbeelding en Thema aan de rechterkant.
  Het menu bevat Openen, Recent, Schermafbeelding, Instellingen, Updates en Over. **Openen in slicer** toont een 3D-printerpictogram
  en **STL exporteren** een exportpictogram. De pictogrammen volgen het thema.
- **Instellingen → Over → Toetsenbord en muis** vermeldt elke snelkoppeling en muisbesturing.
- Lange bestand- en objectnamen maken het zijpaneel niet langer breder dan het venster.
- macOS: snelkoppelingen worden getoond als ⌘ (bijvoorbeeld ⌘O) in tooltips en op de pagina Over.

## 0.18.0
- **Vertalingen worden alleen op GitHub gemaakt.** Gehoste Weblate wordt niet langer gebruikt: de README-badge
  en de Weblate-instellingsgids zijn verdwenen. Nieuwe stap-voor-stap gids voor vertalers,
  [docs/TRANSLATING.md](docs/TRANSLATING.md): corrigeer een woord rechtstreeks in de browser en stuur het als een
  pull request, of gebruik Qt Linguist voor groter werk.
- **Instellingen → Taal** linkt nu rechtstreeks naar die gids.
- **Bedankt voor het installeren**: bij de allereerste start van een nieuwe installatie nodigt een kort bericht
  je uit om PrintView3D een ster te geven op GitHub. Het verschijnt eenmalig en nooit meer, waar je ook op klikt;
  mensen die bijwerken vanaf een oudere versie zien dit niet. **Instellingen → Over** behoudt de link.
- **Wat is er nieuw na een update**: de eerste start na het bijwerken toont wat er is gewijzigd sinds de
  versie die je had, eenmalig. Het werkt ongeacht hoe je hebt bijgewerkt (installatieprogramma, winget, zip of
  AppImage) en offline, vanuit de changelog die in het programma is meegeleverd. Een schone installatie slaat dit over.

## 0.17.0
- **STL exporteren uit 3MF** (werkbalkknop **STL exporteren**, `Ctrl+E`, getoond voor 3MF-bestanden): een venster
  vermeldt elk object met de naam en het aantal driehoeken, allemaal aangevinkt. Sla ze op als **één gecombineerde STL**
  of **één STL per object**, elk bestand vernoemd naar het object, in een map die je kiest (PrintView3D vraagt
  bevestiging voordat bestaande bestanden worden overschreven). Een 3MF met een enkel object gaat rechtstreeks naar het opslagvenster.
  De STL bevat alleen de ruwe geometrie: geen modificaties, negatieve onderdelen, of support blockers/enforcers
  (zoals vastgelegd door Creality Print, OrcaSlicer, Bambu Studio en PrusaSlicer), en geen kleuren,
  materialen of printinstellingen. Afmetingen in millimeters, opgeslagen als binaire STL.
- 3MF-objecten die geen naam hebben in het model zelf, nemen nu hun naam over uit de objectinstellingen van de slicer
  (Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer) in plaats van "Object 1", "Object 2".
- **Nu opnieuw opstarten / Later**: het wijzigen van **Venstertransparantie** (Instellingen → Uiterlijk) of **Gebruik de
  krachtige grafische kaart** (Instellingen → Viewer) wordt pas van kracht na een herstart, dus OK vraagt nu
  **Nu opnieuw opstarten** of **Later**. Nu opnieuw opstarten sluit PrintView3D en opent het opnieuw met hetzelfde
  bestand; Later bewaart het voor de volgende start. Het terugzetten naar wat momenteel draait vraagt niets.
- **Eén venster**: een bestand waarop je dubbelklikt (of opent met "Openen met") terwijl PrintView3D open is, wordt
  getoond in dat venster, dat naar de voorgrond komt, in plaats van in een tweede venster. Nieuwe optie
  **Instellingen → Bestanden → Elk bestand in een nieuw venster openen** voor het oude gedrag. Het starten van
  PrintView3D zonder bestand opent nog steeds een nieuw venster; `--new-window` op de opdrachtregel opent
  een bestand eenmalig in een nieuw venster. (macOS deed dit al.)
- Projectbeschrijving: een bestand dat vanuit FreeCAD is geopend, kan rechtstreeks als model naar je slicer worden gestuurd.

## 0.16.1
- **De titelbalk volgt het thema** (Windows): PrintView3D vertelt Qt nu of het thema licht
  of donker is. Voorheen volgde Qt de eigen donkere modus van Windows en overschreef de onze, dus met Windows in donkere modus
  behield het lichte thema een donkere titelbalk, en met transparantie aan een donkere achtergrond achter donkere tekst.

## 0.16.0
- **Venstertransparantie: Uit, Mica of Acryl** (Instellingen → Uiterlijk, Windows 11). Nieuw: **Acryl**,
  matglas dat alles vervaagt wat zich achter het venster bevindt (bureaublad, andere vensters). Mica blijft de
  rustige optie, een zachte tint van de achtergrond. De Mica-schakelaar uit 0.15 blijft behouden.
- **Leesbaar op elke achtergrond**: met Mica of Acryl krijgen de werkbalk, het zijpaneel en de statusbalk een
  gematteerde laag in de kleur van het thema, het sterkst in het lichte thema, en de grijze labels en vakkoppen
  zijn daar iets donkerder.
- Met transparantie aan kon het overschakelen naar het lichte thema (of terug naar donker) de titelbalk en de Mica-achtergrond
  donker laten totdat het venster werd weggeklikt of van grootte veranderde, waardoor het zijpaneel donkere tekst op een donkere achtergrond toonde. Het venster tekent het frame en de achtergrond nu direct opnieuw.

## 0.15.1
- **Opgelost: Instellingen werden zwart met Windows-transparantie (Mica) aan.** De Mica-stijlregels bereikten
  elk venster dat bij het hoofdvenster hoort, inclusief dialoogvensters; ze noemen nu alleen het eigen hoofdvenster van de
  werkbalk, het zijpaneel en de statusbalk, zodat Instellingen en de andere dialoogvensters dekkend blijven.
- **Het thema verandert live in Instellingen**: het kiezen van Licht, Donker, Grijs of Grafiet schakelt het hele
  programma direct om, net zoals de werkbalkknop doet. OK behoudt het; Annuleren, Esc of het kruisje zet het
  thema terug van toen Instellingen werd geopend.
- Over Mica zelf: Windows tekent het als een zachte, vrijwel dekkende tint van de achtergrond, niet als transparant
  glas, dus in veel opstellingen ziet het er bijna uit als het normale thema. Voor het testen van andere Windows 11-achtergronden
  is er een verborgen startoptie `--backdrop mica-alt` (sterkere tint) of `--backdrop acrylic`
  (vervaging van wat zich achter het venster bevindt).

## 0.15.0
- **Windows 11-transparantie (Mica)**: nieuwe schakelaar in Instellingen → Uiterlijk. De werkbalk, het zijpaneel
  en de statusbalk nemen een zachte tint van de bureaubladachtergrond aan, in de donkere of lichte variant die past bij
  het thema; de 3D-weergave blijft dekkend. Alleen Windows 11 (standaard uit, wordt van kracht na een herstart);
  Windows schakelt het zelf uit wanneer "Transparantie-effecten" uit staan, in de batterijbesparingsmodus, en toont een
  egale kleur wanneer het venster niet actief is.

## 0.14.3
- De "v" van de versie in de rechteronderhoek is vetgedrukt.
- Opmerking over de groene stip: direct na een update verschijnt deze nu meteen, van de controle die de
  update vond (0.14.1 registreerde nog niet dat de controle GitHub bereikte, dus 0.14.2 toonde geen stip tot de
  volgende controle). Updates worden nog steeds maximaal één keer per dag gecontroleerd, zoals beloofd.

## 0.14.2
- **Versiebadge** (rechtsonder): een **groene stip** wanneer een controle in de afgelopen twee weken heeft uitgewezen dat
  PrintView3D up-to-date is, de rode stip wanneer er een update beschikbaar is, geen stip wanneer er niet is
  gecontroleerd. De badge heeft nu een knopachtige rand die bij elk thema past.
- Instellingen → Updates geeft dit aan wanneer de laatste controle GitHub niet kon bereiken, in plaats van "up-to-date".
- Windows: na een update met één klik start de nieuwe versie helemaal aan het einde van de installatie en
  ververst het taakbalkpictogram, zodat de taakbalk direct na het bijwerken geen generiek pictogram meer zou moeten tonen.

## 0.14.1
- Opgelost: op Windows toonde de taakbalk een generiek pictogram voor PrintView3D (ook wanneer vastgezet). PrintView3D
  geeft zichzelf een Windows App ID, en de taakbalk neemt het pictogram van een snelkoppeling met diezelfde ID; de
  snelkoppelingen van het installatieprogramma bevatten dit nu, en het venster zelf vertelt Windows het pictogram, de naam en hoe het
  opnieuw moet worden gestart (dus vastzetten werkt ook met de draagbare zip). Het vensterpictogram is er nu in elke grootte.
  Als een oude vastgezette snelkoppeling nog steeds het generieke pictogram toont, maak deze dan los en zet PrintView3D opnieuw vast.

## 0.14.0
- **STEP-bestanden openen** (`.step`, `.stp`) ([#15](https://github.com/sevagjb/PrintView3D/issues/15)).
  - In 3D getoond via je geïnstalleerde FreeCAD, net als FreeCAD-documenten: op de achtergrond geconverteerd,
    en vervolgens onthouden. Assemblage-onderdelen worden vermeld met hun naam en kunnen worden verborgen.
  - De details uit het bestand worden altijd getoond, ook zonder FreeCAD: STEP-versie (AP203/214/242),
    CAD-programma, auteur, organisatie en datum.
  - **Verzenden naar slicer:** het STEP-bestand zelf naar OrcaSlicer, PrusaSlicer en Bambu Studio; een STL van de
    zichtbare onderdelen naar andere slicers. *Openen in FreeCAD* staat in het slicermenu.
  - Toegevoegd aan "Openen met" op Windows, Linux en macOS (nooit de standaard-app gemaakt).

## 0.13.0
- **Meer 3D-formaten openen**: OBJ, PLY, OFF en glTF / GLB ([#14](https://github.com/sevagjb/PrintView3D/issues/14)).
  - Kleuren die in het bestand zijn opgeslagen worden getoond: OBJ-materialen (`.mtl`) en vertex-kleuren, PLY- en OFF
    vertex- of vlakkleuren, glTF-materiaal en vertex-kleuren. Textures worden niet getoond.
  - OBJ-objecten/groepen en de objecten van een glTF-scène worden afzonderlijk vermeld en kunnen worden verborgen.
  - glTF wordt omgezet van meters naar millimeters en Z-omhoog gedraaid, zodat het op de plaat staat.
  - **Verzenden naar slicer**: OBJ zoals het is; PLY, OFF en glTF als STL (alleen de zichtbare objecten).
  - Toegevoegd aan "Openen met" op Windows, Linux en macOS (nooit de standaard-app gemaakt).
- Een opmerking in de details wanneer een model kleiner is dan 1 mm (meestal een bestand gemaakt in meters).

## 0.12.0
- **Miniaturen in Windows Verkenner** voor 3MF-, STL-, G-code- en FreeCAD-bestanden ([#13](https://github.com/sevagjb/PrintView3D/issues/13)).
  3MF, G-code en FreeCAD tonen de voorbeeld-afbeelding die in het bestand is opgeslagen; STL-modellen worden getekend.
  Geïnstalleerd met PrintView3D (optie in het installatieprogramma, geen beheerdersrechten nodig), verwijderd bij de-installatie.
  Het draait in het afzonderlijke helperproces van Windows, dus een beschadigd bestand kan de Verkenner nooit beïnvloeden.

## 0.11.0
- **macOS (beta)** voor Apple silicon Macs (M1 en nieuwer), macOS 12+: `PrintView3D-macOS-AppleSilicon.dmg`,
  automatisch gebouwd bij elke release. Gratis, zonder betaald Apple-account: de eerste start vereist
  één keer *Toch openen* in Systeeminstellingen → Privacy en beveiliging (stappen in de README).
- Finder: *Openen met → PrintView3D* voor .stl, .3mf, .gcode en .FCStd; bestanden die vanuit Finder worden geopend of
  op het Dock-pictogram worden neergezet, openen in het venster.
- Slicers die in /Applications zijn geïnstalleerd worden automatisch gevonden op de Mac.

## 0.10.1
- Opgelost: in Instellingen op Windows was de markering van de geselecteerde pagina in de zijbalk hoger dan
  de rij en bedekte de aangrenzende vermeldingen, en de tekst sprong wanneer de muis wegbewoog.
  De rijen hebben nu een vaste hoogte, zodat markering en tekst altijd goed uitlijnen.

## 0.10.0
- **Updates**: Instellingen → Updates toont je versie met **Nu controleren op updates**, en een
  automatische controle (maximaal één keer per dag) die je op elk moment kunt in- of uitschakelen. PrintView3D vraagt
  één keer of er automatisch gecontroleerd moet worden.
- Wanneer er een nieuwe versie bestaat, toont de **versie in de rechteronderhoek** een rode stip
  (`● v0.10.0 → 0.11.0`); klik erop voor *Wat is er nieuw*, *Update installeren* en *Deze versie overslaan*.
- **Windows: update met één klik.** PrintView3D downloadt het nieuwe installatiebestand, controleert de SHA-256-vingerafdruk,
  installeert het (instellingen blijven behouden) en start de nieuwe versie. Linux en de draagbare zip
  openen de downloadpagina.
- **Instellingen heeft een zijbalk**: Taal · Uiterlijk · Slicer · FreeCAD · Bestanden · Viewer · Updates ·
  Over, één pagina voor elk. De knop Over op de werkbalk opent de pagina Over.
- README: "Updates en privacy" legt precies uit met wat er contact wordt opgenomen en verzonden (alleen GitHub, alleen de
  versievraag).

## 0.9.0
- **FreeCAD-documenten (.FCStd)**: open ze om ze te bekijken. Met FreeCAD geïnstalleerd wordt het model
  in 3D getoond precies zoals FreeCAD het weergeeft: zichtbare bodies en solids, geen schetsen, verborgen
  objecten, referentievlakken of functies binnen een PartDesign Body. FreeCAD draait onzichtbaar op de
  achtergrond; het resultaat wordt gecacht totdat het bestand verandert.
- Zonder FreeCAD: de voorbeeld-afbeelding van het bestand, de FreeCAD-versie en zichtbare objecten, met een
  knop "FreeCAD downloaden".
- Voor FreeCAD-bestanden is de hoofdknop **Openen in FreeCAD**; de pijl ▾ stuurt het zichtbare model
  naar elke geïnstalleerde slicer als STL.
- Instellingen → FreeCAD: automatisch gevonden (Windows, Linux-pakketten, Snap, Flatpak, AppImage) of
  kies zelf het programma.
- Voorbeeldbestand `examples/demo_bracket.FCStd`.

## 0.8.0
- **Windows-installatiebestand** `PrintView3D-Setup.exe`: Volgende → Installeren → Voltooien, geen beheerdersrechten,
  Startmenu- (en optionele bureaublad) snelkoppeling, "Openen met" voor .stl/.3mf/.gcode, vermeld in
  Windows-instellingen → Apps voor de-installatie. Het uitvoeren van een nieuwer installatiebestand werkt bij en behoudt instellingen.
  De zip blijft beschikbaar als de draagbare versie.
- De tekst van de werkbalkknop is vetgedrukt.
- De Windows-bestandseigenschappen tonen nu altijd de huidige versie.
- README: sectie "Code signing policy" (gratis ondertekening via SignPath Foundation aangevraagd).

## 0.7.0
- **Grafiet**-thema: een warme, donkere houtskoolkleur die zacht is voor de ogen.
- **Themapictogram** (◐) aan het rechteruiteinde van de werkbalk: één klik opent het themamenu.
- **`Ctrl+T`** stapt naar het volgende thema (Donker → Grijs → Grafiet → Licht).
- Werkbalkknoppen zien er nu uit als knoppen (rand en vulling) in elk thema; een actieve schakelaar
  (Bouwplaat) krijgt een cyaan/donkerblauwe omtrek.

## 0.6.0
- **Thema's**: Automatisch (volgt de donkere/lichte instelling van het systeem, ook tijdens het gebruik), Donker,
  Grijs en Licht. Kies in Instellingen → Uiterlijk; de omschakeling is direct.
- De 3D-weergave volgt het thema (achtergrond, bouwplaat, raster, aslabels). G-code-feature en
  modelkleuren blijven gelijk in elk thema, en de lichte achtergronden zijn lichtgrijs zodat witte
  en gele gereedschapspaden zichtbaar blijven.
- Nieuwe installaties gebruiken *Automatisch*; bestaande installaties behouden de donkere uitstraling totdat je deze wijzigt.
- Nieuwe opdrachtregeloptie `--theme` (bijv. `--theme light`).

## 0.5.0
- **Talen**: Engels, Arabisch, Nederlands, Duits, Frans en Spaans. Kies in Instellingen →
  Taal; de omschakeling is direct (geen herstart nodig), en een openstaand bestand behoudt de weergave, laag en filters.
- **Arabisch** gebruikt een van-rechts-naar-links lay-out. Metingen blijven in westerse cijfers en in leesvolgorde.
- Getallen volgen de taal (bijv. `0,20 mm` in het Nederlands/Duits/Frans/Spaans).
- Eigen teksten van Qt (bestandsdialoogvensters, OK/Annuleren) zijn ook vertaald.
- Nieuwe opdrachtregeloptie `--lang` (bijv. `--lang ar`).
- Vertaalworkflow gereed voor Weblate: `tools/i18n.py` (bijwerken / compileren / controleren / statistieken / nieuw),
  opmerkingen voor vertalers, tests die de bestanden gesynchroniseerd houden. Gids: `docs/WEBLATE.md`.
- De niet-Engelse vertalingen zijn eerste concepten die wachten op beoordeling door moedertaalsprekers.

## 0.4.0
- **Linux-ondersteuning**: een AppImage uit één bestand dat draait op de meeste distributies (Ubuntu 22.04+,
  Debian 12+, Fedora 36+, Mint, Arch, …), automatisch gebouwd en getest.
- Slicers op Linux worden automatisch gevonden als AppImages (`~/Applications`, `~/Downloads`, `/opt`…),
  Flatpaks, Snaps, distributiepakketten en menu-ingangen.
- Linux-desktopintegratie: toepassingen-menu-ingang, "Openen met" en standaard-app voor STL, 3MF en
  G-code (Instellingen → Registreren & standaard maken), met een tip om de toegewezen GPU te gebruiken.
- Wayland-desktops worden ondersteund (PrintView3D draait automatisch via XWayland).
- Slicers die vanuit PrintView3D worden gestart krijgen een schone omgeving, zodat de eigen bibliotheken van de verpakte app er niet mee kunnen conflicteren.
- Nieuwe opdrachtregelopties `--register` en `--send-to-slicer [id]`; instellingen volgen de XDG- /
  macOS-conventies.
- macOS: code is gereed; een Mac-build is op verzoek beschikbaar.

## 0.3.0
- Kies je slicer: Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer, UltiMaker Cura,
  Elegoo Slicer, Anycubic Slicer Next, of elk ander programma (Aangepast). Geïnstalleerde slicers worden
  automatisch gedetecteerd.
- De knop toont de gekozen slicer ("Openen in OrcaSlicer"); de pijl ▾ opent het bestand eenmalig in
  een andere geïnstalleerde slicer, zonder de standaardinstelling te wijzigen.
- Als er geen standaard is gekozen, wordt de eerst geïnstalleerde slicer gebruikt in plaats van een foutmelding te tonen.
- Instellingen uit eerdere versies (pad naar Creality Print) worden automatisch overgenomen.
- Tests zijn niet langer afhankelijk van welke slicers zijn geïnstalleerd op de build-pc.
- Demobestanden in `examples/`, nieuwe README met schermafbeeldingen en een stap-voor-stap bouwhandleiding.

## 0.2.1
- Rotatie volgt de muis zonder vertraging: muisbewegingen worden samengevoegd tot één hertekening per
  frame in plaats van één hertekening per muisevent (muizen met een hoge responssnelheid overspoelden de renderer).
- Druk op het model en sleep: het draait om het exacte punt onder de cursor.
  Druk op een lege ruimte: het draait om het middelpunt van het model. Geen zwervend draaipunt meer na het zoomen.
- Van onderen worden het oppervlak van de plaat en het fijne raster verborgen (omtrek en hoofdlijnen van het raster blijven staan),
  in plaats van te vertrouwen op transparantie, wat sommige grafische stuurprogramma's niet correct tekenden.

## 0.2.0
- Nieuwe camera in slicer-stijl: slepen met de linkermuisknop draait rond met Z altijd omhoog (geen tuimelen/rollen),
  slepen met de rechter-/middelste muisknop verschuift, het muiswiel zoomt richting de cursor.
- G-code-lijnen worden in een lichtere modus getekend tijdens het draaien, voor een vloeiendere beweging.
- Bouwplaat wordt doorzichtig wanneer deze van onderen wordt bekeken, zodat de onderkant van het onderdeel zichtbaar is.
- Raster flikkert niet langer tegen het ondervlak van het model.
- Instellingen > Grafisch toont welke GPU wordt gebruikt en kan PrintView3D omschakelen naar de
  krachtige GPU op laptops met twee GPU's. Over toont de GPU ook.

## 0.1.1
- Opgelost: 3MF-bestanden die niet-gedeclareerde XML-naamruimte-voorvoegsels gebruiken (bijv. `p:`) mislukten met
  "ParseError: unbound prefix". Ze worden nu gerepareerd tijdens het laden.

## 0.1.0 — eerste versie
- Bekijk STL (binair + ASCII), 3MF (incl. Creality Print / OrcaSlicer projecten met meerdere bestanden) en G-code
- G-code: laagschuifregelaar, "alleen deze laag", kleuring van functies en filters, verplaatsingsbewegingen, bogen (G2/G3)
- Leest printtijd, filamentgebruik, printer, bedgrootte en de ingesloten miniatuur uit G-code
- 3MF: zichtbaarheid per object, projectinstellingen, miniatuur en voorbeeld van geslicede platen die in het project zijn opgeslagen
- Knop "Openen in Creality Print" (Ctrl+P) met automatische detectie van de installatie
- Instellingen: registreren als de standaard-app voor .stl / .3mf / .gcode (per gebruiker, omkeerbaar)
- Slepen & neerzetten, recente bestanden, schermafbeeldingen, donker thema
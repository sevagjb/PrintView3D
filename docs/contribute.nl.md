# Vertalen en meedoen

## Vertalingen {#translations}

| Taal | Status |
|---|---|
| English | Brontaal |
| العربية Arabisch | Compleet, nagekeken door een moedertaalspreker |
| Nederlands | Compleet, nagekeken |
| Deutsch | Compleet, moet nog nagekeken worden door een moedertaalspreker |
| Français | Compleet, moet nog nagekeken worden door een moedertaalspreker |
| Español | Compleet, moet nog nagekeken worden door een moedertaalspreker |
| Română (Roemeens) | Compleet, nagekeken door een moedertaalspreker |

**Spreek je een van deze talen? Of wil je PrintView3D in jouw taal?** Je hulp is heel welkom: één fout woord
opmerken helpt al. Vertalingen worden hier op GitHub gemaakt: pas het bestand voor jouw taal aan in
[`translations/`](https://github.com/sevagjb/PrintView3D/tree/main/translations) en open een pull request, alles
in de browser. Stap voor stap: **[Zo vertaal je](TRANSLATING.md)** (in het Engels).
Niet vertaalde teksten verschijnen gewoon in het Engels, dus een taal kan stap voor stap worden toegevoegd.

### Deze website in jouw taal {#this-website-in-your-language}

Elke pagina van deze website is een Markdown-bestand in [`docs/`](https://github.com/sevagjb/PrintView3D/tree/main/docs):
`install.md` is Engels, `install.nl.md` Nederlands. Om een pagina te vertalen kopieer je hem met de code van je
taal vóór `.md` (bijvoorbeeld `install.de.md`), vertaal je de tekst en open je een pull request (een nieuwe taal
wordt dan aan het taalmenu van de site toegevoegd). Laat de opdrachten, bestandsnamen en de labels `{#...}` achter
de koppen zoals ze zijn. Pagina's die nog niet vertaald zijn, worden in het Engels getoond, dus één pagina
tegelijk is prima.

## Meedoen {#contributing}

Foutmeldingen, ideeën en pull requests zijn welkom; zie [CONTRIBUTING.md](https://github.com/sevagjb/PrintView3D/blob/main/CONTRIBUTING.md).
Ontbreekt jouw slicer? Meestal is dat één regel in `SLICERS` in
[`src/printview3d/slicer.py`](https://github.com/sevagjb/PrintView3D/blob/main/src/printview3d/slicer.py).

## Beleid voor ondertekening {#code-signing-policy}

De Windows-versies worden automatisch uit deze repository gebouwd door
[GitHub Actions](https://github.com/sevagjb/PrintView3D/blob/main/.github/workflows/build.yml); er worden geen
programmabestanden met de hand gebouwd of geüpload.

*Status: gratis ondertekening voor opensourceprojecten is aangevraagd. Na goedkeuring:*
Gratis ondertekening van code door [SignPath.io](https://about.signpath.io/), certificaat van de
[SignPath Foundation](https://signpath.org/).

| Rol | Leden |
|---|---|
| Committers en reviewers | [sevagjb](https://github.com/sevagjb) |
| Goedkeurders | [sevagjb](https://github.com/sevagjb) |

Elke ondertekening wordt met de hand goedgekeurd door een goedkeurder. Bijdragen van anderen worden nagekeken
voordat ze worden samengevoegd.

**Privacy:** dit programma stuurt geen informatie naar andere systemen in het netwerk, tenzij de gebruiker of
degene die het installeert of beheert daar uitdrukkelijk om vraagt. PrintView3D werkt volledig offline; het
opent alleen je bestanden en start de slicer die je kiest. De enige verbinding die het ooit maakt is de controle
op updates, en alleen als je erom vraagt of de dagelijkse controle hebt aangezet; zie
[Updates en privacy](use.md#updates-and-privacy).

## Licentie {#license}

[MIT](https://github.com/sevagjb/PrintView3D/blob/main/LICENSE). Vrij te gebruiken, aan te passen en te delen.
Gemaakt met [Qt for Python](https://doc.qt.io/qtforpython/), [PyVista](https://pyvista.org) en
[VTK](https://vtk.org).

## Beveiliging {#security}

Een beveiligingsprobleem gevonden? Meld het alsjeblieft privé, zie [SECURITY.md](https://github.com/sevagjb/PrintView3D/blob/main/SECURITY.md).

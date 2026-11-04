# Installeren

Je hebt **geen** Python of iets anders nodig om PrintView3D te gebruiken. Kies je systeem:

| Systeem | Download | |
|---|---|---|
| **Windows 10 / 11** | `PrintView3D-Setup.exe` (of de draagbare `PrintView3D-windows.zip`) | [Uitleg](#windows) |
| **Linux** (64-bit, x86-64) | `PrintView3D-x86_64.AppImage` | [Uitleg](#linux) |
| **macOS 14.4+** (Apple silicon: M1 en nieuwer), bèta | `PrintView3D-macOS-AppleSilicon.dmg` | [Uitleg](#macos) |
| **macOS 14.4+** (Intel), bèta | `PrintView3D-macOS-Intel.dmg` | [Uitleg](#macos) |

Alle downloads staan op de pagina van de **[nieuwste versie](https://github.com/sevagjb/PrintView3D/releases/latest)**.

## Windows {#windows}

1. Ga naar de **[nieuwste versie](https://github.com/sevagjb/PrintView3D/releases/latest)** en download **`PrintView3D-Setup.exe`**.
2. Dubbelklik erop en klik op **Next → Install → Finish**.
    - Het wordt alleen voor jouw gebruikersaccount geïnstalleerd, dus je hebt **geen beheerderswachtwoord**
      nodig.
    - Voegt PrintView3D toe aan het Startmenu (snelkoppeling op het bureaublad optioneel) en aan "Openen met"
      voor `.stl`-, `.3mf`- en `.gcode`-bestanden.
3. PrintView3D start. Klaar.

**Voorbeelden in Verkenner:** de installer toont ook **miniaturen van 3MF-, STL-, G-code- en
FreeCAD-bestanden** in Verkenner (je kunt dit tijdens de installatie uitvinken). 3MF, G-code en FreeCAD tonen
de voorbeeldafbeelding die je slicer of FreeCAD heeft opgeslagen; STL-bestanden worden getekend. Verschijnen de
miniaturen niet meteen, zet de mapweergave dan op *Grote pictogrammen*, of meld je af en weer aan. (Staan de
Verkenner-invoegtoepassingen van PowerToys aan, dan blijft PowerToys de miniaturen van STL en G-code tonen.)

**Bijwerken:** download de nieuwe `PrintView3D-Setup.exe` en start hem. Hij vervangt de oude versie en houdt
je instellingen.

> **"Windows heeft uw pc beschermd"?** De versies zijn nog niet digitaal ondertekend (gratis ondertekening
> via de SignPath Foundation is aangevraagd, zie [Beleid voor ondertekening](contribute.md#code-signing-policy)),
> dus Windows SmartScreen kan de eerste keer waarschuwen. Klik op **Meer informatie → Toch uitvoeren**. Alle
> broncode staat in de repository, en elke versie wordt automatisch uit die code gebouwd door
> [GitHub Actions](https://github.com/sevagjb/PrintView3D/actions).

**Draagbare versie:** download `PrintView3D-windows.zip`, pak het uit en start `PrintView3D.exe`. Er wordt
niets geïnstalleerd. (`install_windows.bat` in de zip werkt ook nog.)

### Als standaardprogramma voor 3D-bestanden instellen (optioneel)

1. Klik in PrintView3D op **Instellingen**.
2. Open de pagina **Bestanden** en klik op **Registreren en als standaard kiezen…**.
3. Windows Instellingen opent. Kies **PrintView3D** voor `.stl`, `.3mf` en `.gcode`.

Windows wil dat je deze laatste stap zelf bevestigt; geen enkel programma mag dat ongemerkt doen.
**Registratie verwijderen** op dezelfde plek maakt alles ongedaan.

### Verwijderen

**Windows Instellingen → Apps → Geïnstalleerde apps → PrintView3D → Verwijderen**. Dit verwijdert het
programma, de snelkoppelingen en de bestandskoppelingen, en vraagt of je ook je instellingen wilt wissen.
(Draagbare versie: start `uninstall_windows.bat` uit de uitgepakte map.)

## Linux {#linux}

PrintView3D voor Linux is één **AppImage**-bestand: het bevat alles wat het nodig heeft en werkt op de meeste
distributies zonder pakketten te installeren: Ubuntu 22.04 of nieuwer, Linux Mint 21+, Debian 12+,
Fedora 36+, openSUSE Tumbleweed, Arch, Manjaro, Pop!_OS, elementary OS, Zorin OS en andere.

1. Download **`PrintView3D-x86_64.AppImage`** van de **[nieuwste versie](https://github.com/sevagjb/PrintView3D/releases/latest)**.
2. Maak het uitvoerbaar: klik er met rechts op → **Eigenschappen → Rechten → Uitvoeren als programma
   toestaan**, of in een terminal:
   ```bash
   chmod +x PrintView3D-x86_64.AppImage
   ```
3. Dubbelklik erop, of start `./PrintView3D-x86_64.AppImage`.

**Toevoegen aan je programmamenu** (optioneel, aanbevolen): open in PrintView3D **Instellingen → Bestanden**
en klik op **Registreren en standaard maken**. PrintView3D staat dan in je programmamenu en in "Openen met",
en opent `.stl`-, `.3mf`- en `.gcode`-bestanden met een dubbelklik. Op Linux werkt dit meteen;
**Registratie verwijderen** maakt het ongedaan.

Tip: zet de AppImage eerst op een vaste plek, zoals `~/Applications`, want de menu-ingang verwijst naar de
plek waar het bestand staat. Of laat het script alles doen:

```bash
./install_linux.sh PrintView3D-x86_64.AppImage     # copies to ~/Applications + adds the menu entry
./uninstall_linux.sh                               # removes it again
```

(De twee scripts staan in de [broncode](https://github.com/sevagjb/PrintView3D/archive/refs/heads/main.zip).)

**Slicers op Linux** worden automatisch gevonden als ze als AppImage zijn geïnstalleerd (in `~/Applications`,
`~/Downloads`, `~/Desktop`, `~/bin`, `/opt`…), als **Flatpak** of **Snap**, uit de pakketten van je
distributie, of in `/opt`. Anders kies je hem één keer met **Bladeren…** in Instellingen.

<details markdown>
<summary><b>Problemen oplossen op Linux</b></summary>

| Probleem | Oplossing |
|---|---|
| Er gebeurt niets / "AppImages require FUSE" | Installeer FUSE: `sudo apt install libfuse2` (Ubuntu/Debian), `sudo dnf install fuse fuse-libs` (Fedora). Of start het zonder FUSE: `./PrintView3D-x86_64.AppImage --appimage-extract-and-run` |
| `GLIBC_2.35 not found` | Je distributie is ouder dan Ubuntu 22.04 / Debian 12. Bouw het dan zelf uit de broncode ([Zelf bouwen](build.md)). |
| Het venster opent, maar de 3D-weergave blijft zwart | Controleer of je grafische driver geïnstalleerd is (Mesa of de NVIDIA-driver). Zet in een virtuele machine 3D-versnelling aan. |
| Wayland-bureaublad | Ondersteund. PrintView3D draait automatisch via XWayland, omdat de 3D-weergave dat nodig heeft. |
| Traag draaien op een laptop met twee GPU's | Start PrintView3D na **Registreren** vanuit het programmamenu (de menu-ingang vraagt om de snelle GPU), of gebruik de optie *Starten met speciale grafische kaart* van je bureaublad. |

</details>

## macOS {#macos}

> **Bèta.** De Mac-versie wordt automatisch gebouwd en gecontroleerd, maar is nog niet door veel mensen op
> echte Macs geprobeerd. [Laat ons weten hoe het werkt](https://github.com/sevagjb/PrintView3D/issues/new?template=mac_build.md):
> je Mac-model, de macOS-versie en alles wat niet klopt.

Voor **macOS 14.4 (Sonoma) of nieuwer**, in twee versies; kies die voor jouw Mac
(Apple-menu → **Over deze Mac**: *Chip* betekent Apple silicon, *Processor* betekent Intel):

| Jouw Mac | Download |
|---|---|
| **Apple silicon** (M1, M2, M3, M4 en nieuwer) | `PrintView3D-macOS-AppleSilicon.dmg` |
| **Intel** (2018 en nieuwer, de Macs waarop macOS 14 draait) | `PrintView3D-macOS-Intel.dmg` |

1. Download van de **[nieuwste versie](https://github.com/sevagjb/PrintView3D/releases/latest)** de `.dmg` voor jouw Mac.
2. Open hem en sleep **PrintView3D** naar **Apps**.
3. Start PrintView3D vanuit Apps. **De eerste keer** zegt macOS dat het de app *niet kan verifiëren*.
   Klik op **Gereed** (niet op "Verplaats naar prullenmand").
4. Open **Systeeminstellingen → Privacy en beveiliging**, scrol naar *Beveiliging* en klik op
   **Open toch** naast PrintView3D. Bevestig met je wachtwoord of Touch ID.

Daarna opent het gewoon.

> **Waarom deze extra stap?** Apple slaat hem alleen over voor apps van ontwikkelaars die Apple elk jaar
> betalen voor een certificaat en "notarisatie". PrintView3D is gratis en heeft daar geen budget voor, dus
> het is ondertekend zonder Apple-account. Het programma is dezelfde opensourcecode als op Windows en Linux,
> automatisch gebouwd door [GitHub Actions](https://github.com/sevagjb/PrintView3D/actions). (Rechtsklik →
> Open werkt hiervoor niet meer op macOS 15 en nieuwer; gebruik Open toch zoals hierboven.)

**Bestanden openen met PrintView3D:** klik in Finder met rechts op een `.stl`-, `.3mf`-, `.gcode`- of
`.FCStd`-bestand → **Open met → PrintView3D**. Als standaard instellen: klik met rechts op het bestand →
**Toon info** → *Open met:* **PrintView3D** → **Wijzig alle…**.

**Slicers** in Apps (Creality Print, OrcaSlicer, Bambu Studio, PrusaSlicer, Cura, …) worden automatisch
gevonden. **Updates:** *Update downloaden* opent de pagina van de nieuwe versie; sleep die naar Apps om de oude
te vervangen. Oudere Macs waarop macOS 14 niet draait:
[laat het ons weten](https://github.com/sevagjb/PrintView3D/issues/new?template=mac_build.md) als je daar een
versie voor nodig hebt.


### Quick Look (voorvertoningen in Finder) {#quick-look}

PrintView3D voegt Quick Look-ondersteuning toe voor 3D-printbestanden (bèta):

- **Miniaturen in Finder** voor 3MF-, STL-, G-code-, FreeCAD-, OBJ- en PLY-bestanden. 3MF-, G-code- en
  FreeCAD-bestanden tonen de afbeelding die je slicer of FreeCAD erin heeft opgeslagen; STL-bestanden (en
  3MF-bestanden zonder afbeelding) worden getekend, net als op Windows.
- **Voorvertoning met de spatiebalk:** selecteer een bestand en druk op de spatiebalk. STL-, 3MF-, OBJ- en
  PLY-modellen worden in 3D getoond (sleep om te draaien, scrol of knijp om te zoomen), met hun afmetingen in
  millimeters. G-code- en FreeCAD-bestanden tonen hun opgeslagen afbeelding. Voor al het andere (lagen,
  objecten, instellingen) open je het bestand in PrintView3D.

Dit werkt zodra PrintView3D in **Apps** staat en één keer is gestart (stap 1–4 hierboven). Verschijnen er
geen voorvertoningen, open dan **Systeeminstellingen → Algemeen → Inlogonderdelen en extensies**, klik bij
**Quick Look** op ⓘ en zet **PrintView3D** aan. Finder bewaart oude miniaturen een tijdje; bestanden die je
daarna kopieert of opslaat, tonen de nieuwe. STEP-bestanden krijgen geen voorvertoning: om ze te lezen is
FreeCAD nodig, en dat kan Quick Look niet gebruiken. Biedt een andere app (een slicer, FreeCAD) ook
voorvertoningen voor een van deze bestandstypen, dan kan macOS die van die app gebruiken.

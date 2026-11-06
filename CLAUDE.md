# Kritzelei wird Schrift

Aus handgezeichneten Zeichenvorlagen (3 Bögen A/B/C, je 7 × 7 Kästchen,
147 Zeichen) wird eine FontForge-Datei (`*.sfd`).
Code, Kommentare, Ausgaben und Commit-Nachrichten sind **deutsch**.

## Pipeline

1. `Kritzelei-Bilder-Vorbereitung.py`: Fotos entzerren (ArUco-Randmarken)
   → `Kritzelei-Bilder-Vorbereitung/`
2. `Kritzelei-Bilder-Fehlersuche.py`: Kästchenerkennung prüfen (Markierungsbild)
3. `Kritzelei-wird-Schrift-Scan2SVG.py`: Kästchen ausschneiden → Strichbreite angleichen
   (Standard 0.75, `--strichbreite-anpassen 0` = aus) → JPG → PPM → potrace → SVG → Font
4. `Kritzelei-wird-Schrift-SVG2Font.py`: nur SVG-Ordner → Font (ohne Rasterbilder,
   daher z. B. kein `--strichbreite-anpassen`)
5. `Kritzelei-wird-Schrift-Schnitte.py`: überarbeitete Regular-Datei → Italic, Bold,
   Bold-Italic. Bewusst nicht Teil des normalen Laufs, damit Korrekturen nur einmal anfallen.
6. `Kritzelei-wird-Schrift-Export.py`: sfd-Dateien eines Ordners → OTF, TTF, WOFF2, UFO
   (`<Ordner>/export/`), optional ZIP zum Weitergeben mit `template/LIESMICH.md`.

`Kritzelei-Oberflaeche.py` (CustomTkinter) führt durch diese Schritte und startet dafür
die Skripte als Unterprozesse; neue CLI-Optionen dort ggf. in `auftrag.py` und im
Formular ergänzen.

Die Skripte sind dünne CLI-Hüllen, die Arbeit steckt in `kritzelei/`:

| Modul | Aufgabe | FontForge nötig |
|---|---|---|
| `dateien.py` | Bilddateien eines Ordners als Bögen (`jpg`, `jpeg`, `png`), für Skripte und Oberfläche | nein |
| `glyphen.py` | Belegung der Kästchen, Beschriftungen, Höhenklassen, Ziellinien (`EM`, `metriken`, `klassenhoehen`) | nein |
| `bild.py` | Entzerren (ArUco-Randmarken) | nein |
| `raster.py` | Kästchen über das Soll-Raster finden, Kontrollbild | nein |
| `strich.py` | Strichbreite messen/angleichen (`--strichbreite-anpassen`, Standard 0.75) | nein |
| `vektor.py` | Ausschneiden, potrace | nein |
| `font.py` | Font aufbauen, Größenanpassung je Höhenklasse, abgeleitete Zeichen | ja |
| `symbole.py` | eingebettete Zeichen (Pfote, `.notdef`, Hände) | ja |
| `schnitte.py` | Italic, Bold, Bold-Italic ableiten oder nur kennzeichnen | ja |
| `export.py` | Formate erzeugen (`fontforge` lazy), ZIP packen und Hinweistext füllen ohne FontForge | nur `exportieren` |
| `auftrag.py` | Einstellungen der Oberfläche → Skriptaufrufe (ohne Tk testbar) | nein |
| `oberflaeche.py` | Fenster (CustomTkinter), Schritte, Dialoge, Prozesse, Protokoll | nein |
| `schriftprobe.py` | SFD → OTF als Unterprozess, Text setzen mit Pillow | nur `otf_erzeugen` |

`fontforge` nur lazy importieren (wie `font_bauen` in Scan2SVG), damit die
Raster-Schritte und Tests ohne FontForge laufen.

## Testen

```bash
python3 -m pytest -q tests
```

~55 s; Font-, Schnitt- und Export-Tests brauchen `python3-fontforge` und `potrace`, die
Fenster-Tests CustomTkinter und öffnen teils kurz ein sichtbares Fenster. Kompletter Lauf mit
den Beispielbögen (Ausgabe in ein Scratch-Verzeichnis, nicht nach `Output/`):

```bash
python3 Kritzelei-wird-Schrift-Scan2SVG.py -s Kritzelei-Bilder-Vorbereitung -o /tmp/k -n K --rmppm
```

Ausgaben knapp halten (`-q`, `| tail`, `| grep -v "^Program root"` – FontForge
druckt beim Import „Program root: /usr“).

## Stolperfallen

- **Glyphennamen**: `HOEHENKLASSEN` nutzt FontForge-/AGL-Namen (`exclam`, `uni203D`,
  `uniFB00`), die Belegung dagegen Zeichen + Codepoint. Codepoints ≥ `PRIVATE_SCHWELLE`
  sind Platzhalter, dort gilt der Name (`c_k.liga`, `a.ss01`).
- **`fontforge.nameFromUnicode` segfaultet**, wenn im selben Prozess vorher ein Font
  geschlossen wurde (z. B. in pytest nach dem Font-Test). Für Namen `fontTools.agl`
  bevorzugen (siehe `strich._glyphenname`).
- **Skalierung**: FontForge skaliert ein importiertes SVG auf die em-Höhe
  (2048 / Ausschnitthöhe in px); danach skaliert `_groessen_anpassen` jedes Zeichen
  einer Höhenklasse exakt auf die Zielhöhe. Zeichen ohne Klasse (G, J, ẞ, ſ,
  Satzzeichen) behalten die Import-Größe.
- Abgeleitete Zeichen (¡ ¿ ⸘ 🄯 ¹ ² ³) entstehen erst nach der Größenanpassung
  und haben bewusst keine Höhenklasse.
- **`fontforge` kann `fontforge-nox` sein** (ohne Oberfläche, beendet sich sofort). Die
  GUI läuft ggf. nur als Flatpak `org.fontforge.FontForge`, siehe `auftrag.befehl_fontforge`.
- **Python**: Die Pakete liegen beim System-Python, in Terminals ist evtl. eine virtuelle
  Umgebung aktiv. Im Zweifel `/usr/bin/python3` aufrufen.
- **Oberfläche prüfen wie `main()`**: Fenster erst `withdraw()`, dann aufbauen, dann
  `deiconify()`. Ein von Anfang an sichtbares Fenster verhält sich anders und hat schon
  einen Fehler verdeckt.
- **Ablauf in der Oberfläche**: Knöpfe ohne Pfeil bleiben auf der Seite, nur Knöpfe mit Pfeil
  wechseln sie; nach Erfolg erscheint „Weiter“ (`_schritt_knoepfe`, `_schritt_stand`). Keine
  automatischen Sprünge nach einer Aktion einbauen.
- **Dialoge**: Rückfragen und Fehler über `_frage`/`_fehler` (Klasse `Dialog`, in Tests ersetzbar),
  Ordner und Dateien über `zenity` oder `kdialog` (`auftrag.befehl_waehler`), Tk nur als Rückfallebene.
- **Rundungen**: CustomTkinter zeichnet sie unter Linux als Schriftzeichen. Sie treffen die Kanten nur
  bei manchen Radien sauber (7, 10, 12, 20, 22, 25, 27), siehe `RADIUS_*` in `oberflaeche.py`.
- **Textkante**: Große Buchstaben haben Vorlauf. Überschriften stehen ohne Einzug, `EINZUG_H2` und
  `EINZUG_TEXT` (über `corner_radius` von `CTkLabel`) sorgen dafür, dass kein Text links seiner
  Überschrift beginnt. Neue Beschriftungen über `Stil.text`/`klein`/`fett`/`h2` anlegen.
- **CustomTkinter**: `CTkScrollableFrame` zeigt seine Leiste immer, deshalb `Rollflaeche`.
  Jede `CTkScrollbar` erzwingt beim Zeichnen einen Layout-Lauf, deshalb entstehen die Seiten
  erst beim ersten Öffnen. `bind_all` ist auf CTk-Widgets verboten, feste `wraplength`-Werte
  sprengen schmale Fenster (siehe `_mitwachsen`).
- **Neigungswinkel**: bezieht sich auf die Regular-Datei, eine Handschrift kann schon dort
  geneigt sein. Italic = Regular minus Neigung, Bold behält den Winkel von Regular.
- `template/oberflaeche/{titel,schriftprobe}.png` sind mit der Kritzelei-Schrift gesetzt, `icon.png`
  stammt aus dem `.notdef`; alle drei ändern sich nicht von selbst mit dem Beispiel-Font.
- Die Fotos in `template/oberflaeche/doku/` nach sichtbaren Änderungen neu aufnehmen:
  `/usr/bin/python3 template/screenshots.py` (öffnet kurz das Fenster).
- **Kerning im UFO**: FontForge schreibt es nach `features.fea`, nicht nach `kerning.plist`.
- `index.htm` wird mit pandoc aus `README.md` erzeugt – Inhaltliches in der README ändern.
- Neue CLI-Optionen auch in der README (Optionsliste) und ggf. „Aufbau des Codes“ dokumentieren.
- `Output/Kritzelei` ist der eingecheckte Beispiel-Font mit allen vier Schnitten; nur bewusst neu
  erzeugen, dann auch `Kritzelei-Web-Test/webfont.woff2` und die Fotos prüfen. `Output/*/export/` und
  `Output/*.zip` sind erzeugt und von Git ausgenommen.
- **Hints**: `schnitte._hints_erneuern` berechnet sie je Schnitt neu; fontforge kennt kein `clearHints`.

# Kritzelei wird Schrift

Aus handgezeichneten Zeichenvorlagen (3 Bögen A/B/C, je 7 × 7 Kästchen,
Vorlage Version 2 = 147 Zeichen) wird eine FontForge-Datei (`*.sfd`).
Code, Kommentare, Ausgaben und Commit-Nachrichten sind **deutsch**.

## Pipeline

1. `Kritzelei-Bilder-Vorbereitung.py`: Fotos entzerren (ArUco-Randmarken)
   → `Kritzelei-Bilder-Vorbereitung/`
2. `Kritzelei-Bilder-Fehlersuche.py`: Kästchenerkennung prüfen (Markierungsbild)
3. `Kritzelei-wird-Schrift-Scan2SVG.py`: Kästchen ausschneiden → (optional Strichbreite
   angleichen) → JPG → PPM → potrace → SVG → Font
4. `Kritzelei-wird-Schrift-SVG2Font.py`: nur SVG-Ordner → Font (ohne Rasterbilder,
   daher z. B. kein `--breite-anpassen`)

Die Skripte sind dünne CLI-Hüllen, die Arbeit steckt in `kritzelei/`:

| Modul | Aufgabe | FontForge nötig |
|---|---|---|
| `glyphen.py` | Belegung der Kästchen, Höhenklassen, Ziellinien (`EM`, `metriken`, `klassenhoehen`) | nein |
| `bild.py` | Entzerren, Kästchen über Konturen (`--erkennung kontur`) | nein |
| `raster.py` | Kästchen über Soll-Raster (`--erkennung raster`, Standard bei V2) | nein |
| `strich.py` | Strichbreite messen/angleichen (`--breite-anpassen`) | nein |
| `vektor.py` | Ausschneiden, `--skel`, potrace | nein |
| `font.py` | Font aufbauen, Größenanpassung je Höhenklasse, abgeleitete Zeichen | ja |
| `symbole.py` | eingebettete Zeichen (Pfote, `.notdef`, Hände) | ja |

`fontforge` nur lazy importieren (wie `font_bauen` in Scan2SVG), damit die
Raster-Schritte und Tests ohne FontForge laufen.

## Testen

```bash
python3 -m pytest -q tests
```

~7 s; der Font-Test braucht `python3-fontforge` und `potrace`. Kompletter Lauf mit
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
- `index.htm` wird mit pandoc aus `README.md` erzeugt – Inhaltliches in der README ändern.
- Neue CLI-Optionen auch in der README (Optionsliste) und ggf. „Aufbau des Codes“ dokumentieren.
- `Output/Kritzelei` ist der eingecheckte Beispiel-Font; nur bewusst neu erzeugen.

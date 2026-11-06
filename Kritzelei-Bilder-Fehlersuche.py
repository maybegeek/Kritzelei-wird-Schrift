#!/usr/bin/env python3
"""Kontrolle der Kästchenerkennung.

Zeigt für jeden vorbereiteten Bogen, was erkannt wurde – mit genau
derselben Erkennung, die ``Kritzelei-wird-Schrift-Scan2SVG.py`` verwendet.
Weiter mit einer beliebigen Taste (z. B. ESC).

  blau   = Soll-Raster der Vorlage
  grün   = gefundener Rahmen (orange: Lage geschätzt)
  rot    = Ausschnitt, der zur Glyphe wird

    python3 Kritzelei-Bilder-Fehlersuche.py -s Kritzelei-Bilder-Vorbereitung
"""

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kritzelei import raster  # noqa: E402
from kritzelei.dateien import bilder_finden  # noqa: E402
from kritzelei.glyphen import BELEGUNG, KAESTCHEN_PRO_BLATT, beschriftung, kaestchen_bezeichnung  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kontrolle der Kästchenerkennung.")
    ap.add_argument("-s", "--scans", required=True, type=Path, help="Ordner der vorbereiteten Bögen.")
    ap.add_argument("--speichern", type=Path,
                    help="Markierte Bilder in diesen Ordner schreiben statt anzeigen.")
    args = ap.parse_args(argv)

    if args.speichern:
        args.speichern.mkdir(parents=True, exist_ok=True)

    alles_gut = True
    for blatt_index, datei in enumerate(bilder_finden(args.scans)[:3]):
        bild = cv2.imread(str(datei))
        start = blatt_index * KAESTCHEN_PRO_BLATT
        anzahl = max(0, min(KAESTCHEN_PRO_BLATT, len(BELEGUNG) - start))
        erkennung = raster.erkennen(bild, anzahl)
        ok = not erkennung.warnungen
        print(f"{datei.name}: {anzahl} Kästchen, {len(erkennung.warnungen)} unsicher – {'ok' if ok else 'PRÜFEN'}")
        for index, text in erkennung.warnungen:
            print(f"  {kaestchen_bezeichnung(start + index)}: {text}")
        texte = [beschriftung(BELEGUNG[start + i][0]) for i in range(anzahl)]
        markiert = raster.markieren(bild, erkennung, texte)
        alles_gut &= ok

        if args.speichern:
            cv2.imwrite(str(args.speichern / datei.name), markiert)
        else:
            cv2.imshow(datei.name, cv2.resize(markiert, None, fx=0.4, fy=0.4))
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    return 0 if alles_gut else 1


if __name__ == "__main__":
    sys.exit(main())

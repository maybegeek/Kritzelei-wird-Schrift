#!/usr/bin/env python3
"""Kontrolle der Kästchenerkennung.

Zeigt für jeden vorbereiteten Bogen, was erkannt wurde – mit genau
derselben Erkennung, die ``Kritzelei-wird-Schrift-Scan2SVG.py`` verwendet.
Weiter mit einer beliebigen Taste (z. B. ESC).

Bei ``--erkennung raster`` (Standard):
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
from kritzelei.bild import kaestchen_konturen, kaestchen_markieren  # noqa: E402
from kritzelei.glyphen import BELEGUNG, KAESTCHEN_PRO_BLATT, belegung, kaestchen_bezeichnung  # noqa: E402


def beschriftung(name: str, index: int) -> str:
    """OpenCV kann nur ASCII zeichnen – sonst die Kästchennummer."""
    if name.isascii() and name.isprintable():
        return name
    return f"#{index % KAESTCHEN_PRO_BLATT + 1}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kontrolle der Kästchenerkennung.")
    ap.add_argument("-s", "--scans", required=True, type=Path, help="Ordner der vorbereiteten Bögen.")
    ap.add_argument("-v", "--version", type=int, default=2, choices=sorted(BELEGUNG),
                    help="Version der Zeichenvorlage (Standard: 2).")
    ap.add_argument("--erkennung", choices=("raster", "kontur"),
                    help="wie bei Scan2SVG (Standard: raster bei Vorlage 2, sonst kontur).")
    ap.add_argument("-t", "--threshold", type=int, default=100,
                    help="Schwellwert, nur für --erkennung kontur (Standard: 100).")
    ap.add_argument("--speichern", type=Path,
                    help="Markierte Bilder in diesen Ordner schreiben statt anzeigen.")
    args = ap.parse_args(argv)
    verfahren = args.erkennung or ("raster" if args.version == 2 else "kontur")
    glyphen = belegung(args.version)

    if args.speichern:
        args.speichern.mkdir(parents=True, exist_ok=True)

    alles_gut = True
    for blatt_index, datei in enumerate(sorted(args.scans.glob("*.jpg"))[:3]):
        bild = cv2.imread(str(datei))
        start = blatt_index * KAESTCHEN_PRO_BLATT

        if verfahren == "raster":
            anzahl = max(0, min(KAESTCHEN_PRO_BLATT, len(glyphen) - start))
            erkennung = raster.erkennen(bild, anzahl)
            ok = not erkennung.warnungen
            print(f"{datei.name}: {anzahl} Kästchen, {len(erkennung.warnungen)} unsicher – {'ok' if ok else 'PRÜFEN'}")
            for index, text in erkennung.warnungen:
                print(f"  {kaestchen_bezeichnung(start + index, glyphen)}: {text}")
            texte = [beschriftung(glyphen[start + i][0], start + i) for i in range(anzahl)]
            markiert = raster.markieren(bild, erkennung, texte)
        else:
            konturen = kaestchen_konturen(bild, args.threshold)
            ok = len(konturen) == KAESTCHEN_PRO_BLATT
            print(f"{datei.name}: {len(konturen)} von {KAESTCHEN_PRO_BLATT} Kästchen erkannt – {'ok' if ok else 'FEHLER'}")
            markiert = kaestchen_markieren(bild, konturen)
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

#!/usr/bin/env python3
"""Kontrolle der Kästchenerkennung.

Zeigt für jeden vorbereiteten Bogen die erkannten Kästchen eingefärbt und
durchnummeriert an – mit genau derselben Erkennung, die
``Kritzelei-wird-Schrift-Scan2SVG.py`` verwendet. Weiter mit einer
beliebigen Taste (z. B. ESC).

    python3 Kritzelei-Bilder-Fehlersuche.py -s Kritzelei-Bilder-Vorbereitung
"""

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kritzelei.bild import kaestchen_konturen, kaestchen_markieren  # noqa: E402
from kritzelei.glyphen import KAESTCHEN_PRO_BLATT  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kontrolle der Kästchenerkennung.")
    ap.add_argument("-s", "--scans", required=True, type=Path, help="Ordner der vorbereiteten Bögen.")
    ap.add_argument("-t", "--threshold", type=int, default=100,
                    help="Schwellwert wie bei Scan2SVG (Standard: 100).")
    ap.add_argument("--speichern", type=Path,
                    help="Markierte Bilder in diesen Ordner schreiben statt anzeigen.")
    args = ap.parse_args(argv)

    if args.speichern:
        args.speichern.mkdir(parents=True, exist_ok=True)

    alles_gut = True
    for datei in sorted(args.scans.glob("*.jpg")):
        bild = cv2.imread(str(datei))
        konturen = kaestchen_konturen(bild, args.threshold)
        status = "ok" if len(konturen) == KAESTCHEN_PRO_BLATT else "FEHLER"
        alles_gut &= status == "ok"
        print(f"{datei.name}: {len(konturen)} von {KAESTCHEN_PRO_BLATT} Kästchen erkannt – {status}")

        markiert = kaestchen_markieren(bild, konturen)
        if args.speichern:
            cv2.imwrite(str(args.speichern / datei.name), markiert)
        else:
            cv2.imshow(datei.name, cv2.resize(markiert, None, fx=0.25, fy=0.25))
            cv2.waitKey(0)
            cv2.destroyAllWindows()
    return 0 if alles_gut else 1


if __name__ == "__main__":
    sys.exit(main())

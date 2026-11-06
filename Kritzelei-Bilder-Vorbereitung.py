#!/usr/bin/env python3
"""Fotos/Scans der Zeichenvorlage entzerren und zuschneiden.

Aufruf z. B.:

    python3 Kritzelei-Bilder-Vorbereitung.py -s Kritzelei-Bilder-Original
    python3 Kritzelei-Bilder-Vorbereitung.py -f A.jpg

Die entzerrten Bilder landen (Standard) in ``Kritzelei-Bilder-Vorbereitung``.
"""

# Author:  Christoph Pfeiffer
# Date:    Juni 2021
# License: CC (BY-NC-SA 4.0) https://creativecommons.org/licenses/by-nc-sa/4.0/

import argparse
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kritzelei.bild import MarkerFehler, entzerren  # noqa: E402
from kritzelei.dateien import BILD_ARTEN, bilder_finden  # noqa: E402

ORIGINALE = Path("Kritzelei-Bilder-Original")
VORBEREITET = Path("Kritzelei-Bilder-Vorbereitung")


def vorschau(original, entzerrt, titel: str) -> None:
    import matplotlib.pyplot as plt

    plt.suptitle(titel)
    plt.subplot(121), plt.imshow(cv2.cvtColor(original, cv2.COLOR_BGR2RGB)), plt.title("Original")
    plt.subplot(122), plt.imshow(entzerrt, cmap="gray"), plt.title("zur Weiterverarbeitung")
    plt.show()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="De-Warping der Zeichenvorlage.")
    quelle = ap.add_mutually_exclusive_group(required=True)
    quelle.add_argument("-s", "--scans", type=Path, help=f"Ordner mit den Fotos/Scans ({BILD_ARTEN}).")
    quelle.add_argument("-f", "--file",
                        help=f"Einzelner Dateiname, bezogen auf den Ordner {ORIGINALE}.")
    ap.add_argument("-o", "--output", type=Path, default=VORBEREITET,
                    help=f"Zielordner (Standard: {VORBEREITET}).")
    ap.add_argument("--ohne-vorschau", action="store_true",
                    help="Keine Vorschau-Fenster anzeigen.")
    args = ap.parse_args(argv)

    dateien = bilder_finden(args.scans) if args.scans else [ORIGINALE / args.file]
    if not dateien:
        print(f"Keine Bilddateien ({BILD_ARTEN}) in {args.scans} gefunden.", file=sys.stderr)
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    fehler = 0
    geschrieben = set()
    for datei in dateien:
        print(datei)
        # Immer .jpg: So ersetzt ein neuer Lauf das alte Ergebnis, auch bei anderer Endung der Quelle.
        ziel = args.output / f"{datei.stem}.jpg"
        if ziel in geschrieben:
            print(f"  Warnung: {datei.name} ersetzt ein Bild gleichen Namens mit anderer Endung.")
        geschrieben.add(ziel)
        original = cv2.imread(str(datei))
        if original is None:
            print("  Bild konnte nicht gelesen werden.", file=sys.stderr)
            fehler += 1
            continue
        try:
            entzerrt = entzerren(original)
        except MarkerFehler as e:
            print(f"  {e} – sind alle vier Randmarken vollständig im Bild?", file=sys.stderr)
            fehler += 1
            continue
        cv2.imwrite(str(ziel), entzerrt)
        if not args.ohne_vorschau:
            vorschau(original, entzerrt, datei.name)
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Import vorliegender SVG-Dateien und Erstellung einer FontForge-Datei (*.sfd).

Aufruf z. B.:

    python3 Kritzelei-wird-Schrift-SVG2Font.py -svg Output/Kritzelei-01 -n Kritzelei-01

Alle ``*.svg`` im Ordner werden nach Namen sortiert den Zeichen der
Vorlage zugeordnet.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kritzelei.font import font_erstellen  # noqa: E402
from kritzelei.glyphen import BELEGUNG  # noqa: E402

__author__ = "Christoph Pfeiffer"
__license__ = "CC-BY-NC-SA-4.0"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Import der SVG-Dateien in FontForge ... + magic.")
    ap.add_argument("-svg", "--svgordner", required=True, type=Path, help="Ordner der SVG-Dateien.")
    ap.add_argument("-n", "--name", required=True, help="Name der Schrift.")
    args = ap.parse_args(argv)

    svg_dateien = sorted(args.svgordner.glob("*.svg"))
    try:
        sfd = font_erstellen(svg_dateien, BELEGUNG, args.name, args.svgordner)
    except ValueError as fehler:
        print(f"Fehler: {fehler}\nDie Umwandlung wird abgebrochen.", file=sys.stderr)
        return 1
    print(f"Font gespeichert: {sfd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

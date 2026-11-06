#!/usr/bin/env python3
"""Schriftdateien in andere Formate umwandeln und als ZIP zum Weitergeben packen.

    python3 Kritzelei-wird-Schrift-Export.py -d Output/Kritzelei-01 --zip Kritzelei-01.zip

Die Formate landen in ``<ordner>/export/`` nach Zweck sortiert.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kritzelei.export import FORMATE, ExportFehler, exportieren, zip_packen  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Schriftdateien exportieren und als ZIP packen.")
    ap.add_argument("-d", "--ordner", required=True, type=Path, help="Ordner mit den *.sfd-Dateien.")
    ap.add_argument("--formate", nargs="*", choices=sorted(FORMATE), default=["otf", "woff2", "ufo"],
                    metavar="FORMAT", help="otf, ttf, woff2, ufo (Standard: otf woff2 ufo).")
    ap.add_argument("--zip", type=Path, help="Alles Wichtige als ZIP unter diesem Namen speichern.")
    args = ap.parse_args(argv)

    try:
        for datei in exportieren(args.ordner, args.formate):
            print(f"* Erzeugt: {datei}")
        if args.zip:
            print(f"* ZIP gespeichert: {zip_packen(args.ordner, args.zip, args.formate)}")
    except ExportFehler as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1
    except OSError as fehler:
        print(f"Fehler beim Schreiben: {fehler}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

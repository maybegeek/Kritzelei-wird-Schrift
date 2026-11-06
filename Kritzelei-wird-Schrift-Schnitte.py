#!/usr/bin/env python3
"""Italic, Bold und Bold-Italic aus der überarbeiteten Regular-Datei ableiten.

Erst die Regular-Datei in FontForge überarbeiten, dann:

    python3 Kritzelei-wird-Schrift-Schnitte.py -sfd Output/Kritzelei-01/Kritzelei-01-Regular.sfd

Mit ``--nur-kennzeichen`` bekommen schon vorhandene, von Hand gestaltete Dateien
nur die richtigen Metainformationen, die Umrisse bleiben unberührt.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kritzelei.schnitte import (  # noqa: E402
    NEIGUNG,
    STAERKE,
    STILE,
    SchnittFehler,
    nur_kennzeichnen,
    regular_hinweise,
    schnitte_ableiten,
    ziele,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Schriftschnitte aus der überarbeiteten Regular-Datei ableiten.")
    ap.add_argument("-sfd", "--regular", required=True, type=Path, help="Die überarbeitete Regular-Datei (*.sfd).")
    ap.add_argument("--schnitte", nargs="+", choices=sorted(STILE), default=sorted(STILE), metavar="SCHNITT",
                    help="Welche Schnitte: Italic, Bold, BoldItalic (Standard: alle).")
    ap.add_argument("--nur-kennzeichen", action="store_true",
                    help="Vorhandene Dateien nur kennzeichnen, Umrisse bleiben (Regular wird mit angepasst).")
    ap.add_argument("--staerke", type=float, default=STAERKE,
                    help=f"So viel dicker wird der Strich, bezogen auf em 2048 (Standard: {STAERKE}).")
    ap.add_argument("--neigung", type=float, default=NEIGUNG,
                    help=f"So viele Grad zusätzliche Neigung für kursive Schnitte (Standard: {NEIGUNG}).")
    ap.add_argument("--ueberschreiben", action="store_true",
                    help="Vorhandene Schnitte ersetzen (die alte Fassung bleibt als *.sfd.bak erhalten).")
    args = ap.parse_args(argv)

    if not args.regular.is_file():
        print(f"Fehler: {args.regular} gibt es nicht.", file=sys.stderr)
        return 1
    try:
        if args.nur_kennzeichen:
            dateien = nur_kennzeichnen(args.regular, args.schnitte, args.neigung)
        else:
            for hinweis in regular_hinweise(args.regular):
                print(f"Hinweis zur Regular-Datei: {hinweis}. --nur-kennzeichen korrigiert das.")
            vorhanden = [d.name for d in ziele(args.regular, args.schnitte).values() if d.exists()]
            if vorhanden and not args.ueberschreiben:
                print(f"Fehler: Es gibt schon {', '.join(vorhanden)}. Nachgearbeitetes ginge verloren; "
                      "bitte --ueberschreiben angeben, wenn das gewollt ist.", file=sys.stderr)
                return 1
            dateien = schnitte_ableiten(args.regular, args.schnitte, args.staerke, args.neigung)
    except SchnittFehler as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1
    for datei in dateien:
        print(f"* Gespeichert: {datei}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Umwandlung der vorbereiteten Bögen in Vektorbilder der Einzelglyphen
und anschließend in eine FontForge-Datei (*.sfd).

Aufruf z. B.:

    python3 Kritzelei-wird-Schrift-Scan2SVG.py --scans Kritzelei-Bilder-Vorbereitung/ \\
        -o Output/Kritzelei-01 -n Kritzelei-01 --rmppm

Mit ``--ohne-font`` werden nur die SVG-Dateien erzeugt;
``Kritzelei-wird-Schrift-SVG2Font.py`` kann dann später separat laufen.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kritzelei import strich  # noqa: E402
from kritzelei.glyphen import BELEGUNG, belegung  # noqa: E402
from kritzelei.vektor import (  # noqa: E402
    ERKENNUNGSVERFAHREN,
    POTRACE_PROFILE,
    POTRACE_PROFILE_SKELETT,
    glyphen_ausschneiden,
    skelettieren,
    vektorisieren,
)

__author__ = "Christoph Pfeiffer"
__license__ = "CC-BY-NC-SA-4.0"


def argumente(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Umwandlung in SVG-Dateien zum weiteren Import in FontForge.")
    eingabe = ap.add_argument_group("Eingabe (entweder --scans oder einzelne Bögen)")
    eingabe.add_argument("-s", "--scans", type=Path,
                         help="Ordner mit den vorbereiteten Bögen (*.jpg, nach Namen sortiert: A, B, C).")
    eingabe.add_argument("-a", "--blattA", type=Path, help="Bogen A")
    eingabe.add_argument("-b", "--blattB", type=Path, help="Bogen B")
    eingabe.add_argument("-c", "--blattC", type=Path, help="Bogen C")

    ap.add_argument("-o", "--output", type=Path,
                    help="Zielordner (Standard: <scans>/FONT).")
    ap.add_argument("-n", "--name", default="Kritzelei", help="Name der Schrift (Standard: Kritzelei).")
    ap.add_argument("-v", "--version", type=int, default=2, choices=sorted(BELEGUNG),
                    help="Version der Zeichenvorlage (Standard: 2).")
    ap.add_argument("--erkennung", choices=ERKENNUNGSVERFAHREN,
                    help="Kästchenerkennung: raster = Soll-Raster der Vorlage mit Feinjustierung "
                         "(Standard bei Vorlage 2), kontur = freie Suche nach Vierecken "
                         "(bisheriges Verfahren, Standard bei Vorlage 1).")
    ap.add_argument("-t", "--threshold", type=int, default=100,
                    help="Schwellwert 0–255, nur für --erkennung kontur (Standard: 100).")
    ap.add_argument("--blur", type=int, default=3,
                    help="Weichzeichner für die Ausschnitte, ungerade Zahl, 0 = aus (Standard: 3).")

    stift = ap.add_mutually_exclusive_group()
    stift.add_argument("--buntstift", action="store_true",
                       help="Buntstift, Farbe, uneinheitliche Deckkraft.")
    stift.add_argument("--ptdefault", action="store_true",
                       help="potrace-Standardeinstellungen (genauer).")

    breite = ap.add_argument_group("Strichbreite")
    breite.add_argument("--strichbreite-anpassen", type=float, nargs="?", const=1.0, metavar="ANTEIL",
                        help="Strichbreiten aller Zeichen einander annähern. ANTEIL zwischen 0 und 1: "
                             "0 = aus, 0.5 = halber Weg, ohne Zahl 1 = alle gleich breit "
                             f"(ohne die Option: {strich.STANDARD_ANTEIL}).")
    breite.add_argument("--strichbreite", type=float, metavar="EINHEITEN",
                        help="Zielbreite in Font-Einheiten (em 2048) für die Anpassung; ohne Anteil werden "
                             "alle Zeichen ganz angeglichen (Standard: Median aller Zeichen).")

    ap.add_argument("--skel", action="store_true",
                    help="Zusätzlich einen Font mit einheitlicher Strichstärke im Unterordner SKEL erzeugen.")
    ap.add_argument("--ohne-font", action="store_true", help="Nur SVG-Dateien erzeugen, keinen Font.")
    ap.add_argument("--rmppm", action="store_true", help="PPM-Dateien am Ende löschen.")
    ap.add_argument("--rmjpg", action="store_true", help="JPG-Dateien am Ende löschen.")
    ap.add_argument("--rmsvg", action="store_true", help="SVG-Dateien am Ende löschen.")
    args = ap.parse_args(argv)

    if not (args.scans or args.blattA or args.blattB or args.blattC):
        ap.error("Bitte --scans oder mindestens einen der Bögen -a/-b/-c angeben.")
    if args.blur and args.blur % 2 == 0:
        ap.error("--blur muss eine ungerade Zahl sein (oder 0).")
    if args.strichbreite_anpassen is None:
        args.strichbreite_anpassen = strich.STANDARD_ANTEIL if args.strichbreite is None else 1.0
    if not 0 <= args.strichbreite_anpassen <= 1:
        ap.error("--strichbreite-anpassen erwartet einen Anteil zwischen 0 und 1.")
    if args.strichbreite is not None and args.strichbreite <= 0:
        ap.error("--strichbreite muss größer 0 sein.")
    if args.strichbreite is not None and args.strichbreite_anpassen == 0:
        ap.error("--strichbreite passt nicht zu --strichbreite-anpassen 0 (aus).")
    if args.erkennung is None:
        # Das Soll-Raster ist für die aktuelle Vorlage (Version 2) vermessen.
        args.erkennung = "raster" if args.version == 2 else "kontur"
    if args.output is None:
        if args.scans is None:
            ap.error("Bei einzelnen Bögen bitte einen Zielordner mit -o angeben.")
        args.output = args.scans / "FONT"
    return args


def boegen(args: argparse.Namespace) -> list:
    if args.scans:
        dateien = sorted(args.scans.glob("*.jpg"))
        if not dateien:
            sys.exit(f"Keine *.jpg-Dateien in {args.scans} gefunden.")
        if len(dateien) > 3:
            print(f"Warnung: {len(dateien)} Bilder gefunden, verwendet werden nur die ersten drei.")
        return dateien[:3]
    return [args.blattA, args.blattB, args.blattC]


def profil(args: argparse.Namespace) -> str:
    if args.buntstift:
        return "buntstift"
    if args.ptdefault:
        return "default"
    return "standard"


def font_bauen(svg_dateien, args, ordner: Path) -> None:
    # erst hier importieren: fontforge wird nur für diesen Schritt gebraucht
    from kritzelei.font import font_erstellen

    sfd = font_erstellen(svg_dateien, belegung(args.version), args.name, ordner)
    print(f"* Zeichenvorlage in Version: {args.version}")
    print(f"* Schriftname: {args.name}")
    print(f"* Datei: {sfd}")
    with open(ordner / "info.txt", "a", encoding="utf-8") as info:
        info.write(str(vars(args)) + "\n")


def strichbreite_angleichen(jpgs, args: argparse.Namespace) -> None:
    bericht = strich.angleichen(jpgs, belegung(args.version), args.strichbreite_anpassen, args.strichbreite)
    if not bericht.vorher:
        print("Strichbreite: keine Zeichen zum Anpassen gefunden.")
        return

    def spanne(werte):
        return f"{min(werte):.0f}–{max(werte):.0f}"

    print(f"Strichbreite (Font-Einheiten): Ziel {bericht.ziel:.0f}, "
          f"vorher {spanne(bericht.vorher)}, nachher {spanne(bericht.nachher)} "
          f"({bericht.angepasst} Zeichen angepasst).")
    if bericht.begrenzt:
        print(f"  an der Grenze der Anpassung: {' '.join(bericht.begrenzt)}")
    if bericht.unveraendert:
        print(f"  nur Punkte, unverändert: {' '.join(bericht.unveraendert)}")


def loeschen(dateien, art: str) -> None:
    for datei in dateien:
        datei.unlink(missing_ok=True)
    print(f"* {len(dateien)} {art}-Dateien wurden gelöscht")


def main(argv=None) -> int:
    args = argumente(argv)
    ordner: Path = args.output
    jpgs = glyphen_ausschneiden(boegen(args), ordner, args.name, args.threshold, args.blur,
                                verfahren=args.erkennung, belegung=belegung(args.version))
    if args.strichbreite_anpassen:
        strichbreite_angleichen(jpgs, args)
    ppms, svgs = vektorisieren(jpgs, POTRACE_PROFILE[profil(args)])

    if args.skel:
        skel_ordner = ordner / "SKEL"
        skel_jpgs = skelettieren(jpgs, skel_ordner)
        skel_ppms, skel_svgs = vektorisieren(skel_jpgs, POTRACE_PROFILE_SKELETT[profil(args)])
        jpgs += skel_jpgs
        ppms += skel_ppms

    print("Zeichen aus Scan extrahiert und vektorisiert.")

    if not args.ohne_font:
        try:
            print("\nNun wird der Font erstellt:")
            font_bauen(svgs, args, ordner)
            if args.skel:
                print("\nNun wird der SKEL-Font erstellt:")
                font_bauen(skel_svgs, args, skel_ordner)
        except ValueError as fehler:
            print(f"Fehler: {fehler}", file=sys.stderr)
            return 1

    if args.rmppm:
        loeschen(ppms, "PPM")
    if args.rmjpg:
        loeschen(jpgs, "JPG")
    if args.rmsvg:
        loeschen(svgs + (skel_svgs if args.skel else []), "SVG")
    return 0


if __name__ == "__main__":
    sys.exit(main())

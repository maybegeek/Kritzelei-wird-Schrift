"""Ausschneiden der Kästcheninhalte und Vektorisierung mit potrace."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2 as cv
from PIL import Image

from . import raster
from .glyphen import BELEGUNG, KAESTCHEN_PRO_BLATT, Glyphe, kaestchen_bezeichnung

# potrace-Voreinstellungen ----------------------------------------------------
#   standard:   für Fineliner, Kugelschreiber u. ä.
#   buntstift:  für Buntstift, Farbe, uneinheitliche Deckkraft
#   default:    potrace ohne eigene Einstellungen (genauer, mehr Punkte)

POTRACE_PROFILE: dict[str, list[str]] = {
    "standard": ["--flat", "--longcurve", "--turdsize", "30"],
    "buntstift": ["--flat", "--longcurve", "--alphamax", "1.34",
                  "--turdsize", "30", "--blacklevel", "0.6"],
    "default": [],
}


def potrace_pruefen() -> None:
    if shutil.which("potrace") is None:
        raise RuntimeError("potrace wurde nicht gefunden – bitte installieren (z. B. `apt install potrace`).")


def glyphen_ausschneiden(
    blaetter: list[Path | None],
    zielordner: Path,
    name: str,
    weichzeichner: int = 3,
    belegung: list[Glyphe] = BELEGUNG,
) -> list[Path]:
    """Kästcheninhalte aller Bögen als JPG-Dateien ablegen.

    ``blaetter`` enthält die Bögen A, B, C in dieser Reihenfolge; ein
    fehlender Bogen ist ``None``. Die Nummerierung der Dateien richtet sich
    nach der Position des Bogens (A: 001–049, B: 050–098, C: 099–147).
    """
    zielordner.mkdir(parents=True, exist_ok=True)
    dateien: list[Path] = []
    for blatt_index, blatt in enumerate(blaetter):
        if blatt is None:
            continue
        bild = cv.imread(str(blatt))
        if bild is None:
            raise FileNotFoundError(f"Bild konnte nicht gelesen werden: {blatt}")

        start = blatt_index * KAESTCHEN_PRO_BLATT + 1
        anzahl = max(0, min(KAESTCHEN_PRO_BLATT, len(belegung) - (start - 1)))
        erkennung = raster.erkennen(bild, anzahl)
        for index, text in erkennung.warnungen:
            print(f"Warnung: {blatt.name}, {kaestchen_bezeichnung(start - 1 + index, belegung)}: {text}")

        for nummer, k in enumerate(erkennung.kaestchen, start):
            ausschnitt = raster.randreste_entfernen(k.ausschneiden(bild))
            if weichzeichner:
                ausschnitt = cv.GaussianBlur(ausschnitt, (weichzeichner, weichzeichner), 0)
            datei = zielordner / f"{name}-{nummer:03}.jpg"
            cv.imwrite(str(datei), ausschnitt)
            dateien.append(datei)
    return dateien


def vektorisieren(jpg_dateien: list[Path], potrace_optionen: list[str]) -> tuple[list[Path], list[Path]]:
    """JPG → PPM → SVG (potrace). Gibt (ppm_dateien, svg_dateien) zurück."""
    potrace_pruefen()
    ppm_dateien, svg_dateien = [], []
    for jpg in jpg_dateien:
        ppm = jpg.with_suffix(".ppm")
        svg = jpg.with_suffix(".svg")
        with Image.open(jpg) as bild:
            bild.save(ppm, "ppm")
        subprocess.run(["potrace", *potrace_optionen, "-s", str(ppm), "-o", str(svg)], check=True)
        ppm_dateien.append(ppm)
        svg_dateien.append(svg)
    return ppm_dateien, svg_dateien

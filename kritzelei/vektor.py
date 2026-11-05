"""Ausschneiden der Kästcheninhalte und Vektorisierung mit potrace."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2 as cv
import numpy as np
from PIL import Image
from skimage.morphology import dilation, skeletonize

from .bild import kaestchen_finden
from .glyphen import KAESTCHEN_PRO_BLATT

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

POTRACE_PROFILE_SKELETT: dict[str, list[str]] = {
    "standard": ["--flat", "--turdsize", "120"],
    "buntstift": ["--flat", "--longcurve", "--alphamax", "1.34",
                  "--turdsize", "120", "--blacklevel", "0.95"],
    "default": [],
}


def potrace_pruefen() -> None:
    if shutil.which("potrace") is None:
        raise RuntimeError("potrace wurde nicht gefunden – bitte installieren (z. B. `apt install potrace`).")


def glyphen_ausschneiden(
    blaetter: list[Path | None],
    zielordner: Path,
    name: str,
    schwellwert: int = 100,
    weichzeichner: int = 3,
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

        kaestchen = kaestchen_finden(bild, schwellwert)
        if len(kaestchen) != KAESTCHEN_PRO_BLATT:
            print(f"Warnung: {blatt.name}: {len(kaestchen)} statt {KAESTCHEN_PRO_BLATT} Kästchen erkannt.")

        start = blatt_index * KAESTCHEN_PRO_BLATT + 1
        for nummer, k in enumerate(kaestchen, start):
            ausschnitt = k.ausschneiden(bild)
            if weichzeichner:
                ausschnitt = cv.GaussianBlur(ausschnitt, (weichzeichner, weichzeichner), 0)
            datei = zielordner / f"{name}-{nummer:03}.jpg"
            cv.imwrite(str(datei), ausschnitt)
            dateien.append(datei)
    return dateien


def skelettieren(jpg_dateien: list[Path], zielordner: Path) -> list[Path]:
    """Strich auf eine einheitliche Dicke bringen (Skelett + Dilatation)."""
    zielordner.mkdir(parents=True, exist_ok=True)
    kernel = np.array([[0, 1, 1], [0, 1, 0], [1, 1, 0]], dtype=np.uint8)
    quadrat = np.ones((9, 9), dtype=np.uint8)
    ergebnis = []
    for datei in jpg_dateien:
        bild = cv.imread(str(datei), cv.IMREAD_GRAYSCALE)
        bild = cv.bilateralFilter(bild, 3, 25, 7)
        bild = cv.GaussianBlur(bild, (11, 11), 3)
        binaer = cv.adaptiveThreshold(bild, 255, cv.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv.THRESH_BINARY, 35, 11)
        binaer = cv.bitwise_not(binaer)
        binaer = cv.morphologyEx(binaer, cv.MORPH_CLOSE, kernel)
        skelett = skeletonize(binaer == 255).astype(np.uint8) * 255
        skelett = cv.bitwise_not(dilation(skelett, quadrat))
        ziel = zielordner / datei.name
        cv.imwrite(str(ziel), skelett)
        ergebnis.append(ziel)
    return ergebnis


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

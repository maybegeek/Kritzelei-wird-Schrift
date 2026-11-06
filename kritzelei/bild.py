"""Bildverarbeitung: Entzerren der Bögen (OpenCV)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2 as cv
import numpy as np

# Verhältnis Breite : Höhe des Bereichs zwischen den Randmarken.
SEITENVERHAELTNIS = 0.795


class MarkerFehler(RuntimeError):
    """Die vier ArUco-Randmarken wurden nicht (vollständig) gefunden."""


# --- Entzerren ---------------------------------------------------------------

def _aruco_marker_finden(grau: np.ndarray):
    """ArUco-Marker finden – mit alter (< 4.7) und neuer OpenCV-API."""
    aruco = cv.aruco
    if hasattr(aruco, "ArucoDetector"):
        woerterbuch = aruco.getPredefinedDictionary(aruco.DICT_6X6_50)
        detektor = aruco.ArucoDetector(woerterbuch, aruco.DetectorParameters())
        ecken, ids, _ = detektor.detectMarkers(grau)
    else:
        woerterbuch = aruco.Dictionary_get(aruco.DICT_6X6_50)
        parameter = aruco.DetectorParameters_create()
        ecken, ids, _ = aruco.detectMarkers(grau, woerterbuch, parameters=parameter)
    return ecken, ids


def entzerren(bild: np.ndarray) -> np.ndarray:
    """Bogen anhand der vier Randmarken entzerren und zuschneiden.

    Marker-IDs: 0 = links oben, 1 = rechts oben, 2 = rechts unten,
    3 = links unten. Verwendet wird jeweils die innenliegende Ecke.
    Ergebnis ist ein Graustufenbild.
    """
    grau = cv.cvtColor(bild, cv.COLOR_BGR2GRAY)
    ecken, ids = _aruco_marker_finden(grau)

    gefunden = set() if ids is None else {int(i) for i in ids.flatten()}
    fehlend = {0, 1, 2, 3} - gefunden
    if fehlend:
        raise MarkerFehler(
            "Randmarke(n) nicht gefunden: " + ", ".join(str(m) for m in sorted(fehlend))
        )

    def innere_ecke(marker_id: int, ecke: int) -> np.ndarray:
        index = int(np.where(ids == marker_id)[0][0])
        return ecken[index][0][ecke]

    lo, ro, ru, lu = innere_ecke(0, 2), innere_ecke(1, 3), innere_ecke(2, 0), innere_ecke(3, 1)
    quelle = np.float32([lo, ro, ru, lu])

    # Höhe als Mittel aus linker und rechter Kante, Breite fest daraus.
    hoehe = int(round((lu[1] - lo[1] + ru[1] - ro[1]) / 2))
    breite = int(round(hoehe * SEITENVERHAELTNIS))
    ziel = np.float32([[0, 0], [breite, 0], [breite, hoehe], [0, hoehe]])

    matrix = cv.getPerspectiveTransform(quelle, ziel)
    return cv.warpPerspective(grau, matrix, (breite, hoehe))


# --- Kästchen (gefunden werden sie in raster.py) -------------------------------

@dataclass(frozen=True)
class Kaestchen:
    """Innenbereich eines Kästchens (ohne Rand) in Pixeln."""

    x: int
    y: int
    w: int
    h: int

    def ausschneiden(self, bild: np.ndarray) -> np.ndarray:
        return bild[self.y : self.y + self.h, self.x : self.x + self.w]

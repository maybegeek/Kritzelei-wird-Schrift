"""Bildverarbeitung: Entzerren der Bögen und Erkennen der Kästchen (OpenCV)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2 as cv
import numpy as np

# Verhältnis Breite : Höhe des Bereichs zwischen den Randmarken.
SEITENVERHAELTNIS = 0.795

# Anteil der Kästchenhöhe, der rundum abgeschnitten wird, damit der
# Kästchenrand nicht mit in die Glyphe gerät.
ANSCHNITT = 0.046


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


# --- Kästchen erkennen -------------------------------------------------------

@dataclass(frozen=True)
class Kaestchen:
    """Innenbereich eines Kästchens (ohne Rand) in Pixeln."""

    x: int
    y: int
    w: int
    h: int

    def ausschneiden(self, bild: np.ndarray) -> np.ndarray:
        return bild[self.y : self.y + self.h, self.x : self.x + self.w]


def _mindestflaeche(bild: np.ndarray) -> float:
    min_hoehe = round(bild.shape[0] / 12, 1)
    min_breite = round(bild.shape[1] / 11, 1)
    return round(min_hoehe * min_breite, 1)


def kaestchen_konturen(bild: np.ndarray, schwellwert: int = 100) -> list[np.ndarray]:
    """Konturen der Kästchen, sortiert zeilenweise von links oben.

    ``schwellwert`` (0–255) trennt Kästchenlinien vom Papier.
    """
    if bild.ndim == 3:
        grau = cv.cvtColor(bild, cv.COLOR_BGR2GRAY)
    else:
        grau = bild
    _, binaer = cv.threshold(grau, schwellwert, 255, cv.THRESH_BINARY_INV)
    konturen, _ = cv.findContours(binaer, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    mindestflaeche = _mindestflaeche(bild)
    viereckig = []
    for kontur in konturen:
        if cv.contourArea(kontur) <= mindestflaeche:
            continue
        naeherung = cv.approxPolyDP(kontur, 0.01 * cv.arcLength(kontur, True), True)
        if len(naeherung) == 4:
            viereckig.append(kontur)

    # Sortierung: y auf ein Raster runden (Zeile), dann nach x.
    toleranz = round(mindestflaeche / 225)
    spalten = bild.shape[1]

    def reihenfolge(kontur: np.ndarray) -> int:
        x, y, _, _ = cv.boundingRect(kontur)
        return (y // toleranz) * toleranz * spalten + x

    viereckig.sort(key=reihenfolge)
    return viereckig


def kaestchen_finden(bild: np.ndarray, schwellwert: int = 100) -> list[Kaestchen]:
    """Innenbereiche der Kästchen, sortiert zeilenweise von links oben."""
    ergebnis = []
    for kontur in kaestchen_konturen(bild, schwellwert):
        x, y, w, h = cv.boundingRect(kontur)
        rand = int(round(ANSCHNITT * h))
        ergebnis.append(Kaestchen(x + rand, y + rand, w - 2 * rand, h - 2 * rand))
    return ergebnis


def kaestchen_markieren(bild: np.ndarray, konturen: list[np.ndarray]) -> np.ndarray:
    """Kopie des Bildes mit eingefärbten, durchnummerierten Kästchen."""
    markiert = bild.copy() if bild.ndim == 3 else cv.cvtColor(bild, cv.COLOR_GRAY2BGR)
    for nummer, kontur in enumerate(konturen):
        cv.fillPoly(markiert, pts=[kontur], color=(133, 160, 22))
        momente = cv.moments(kontur)
        cx = int(momente["m10"] / momente["m00"])
        cy = int(momente["m01"] / momente["m00"])
        cv.putText(markiert, str(nummer), (cx - 60, cy - 20),
                   cv.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 8)
    return markiert

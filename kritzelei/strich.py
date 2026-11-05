"""Angleichen der Strichbreite aller Zeichen (``--breite-anpassen``).

Warum die Striche im Font unterschiedlich dick werden
-----------------------------------------------------
Jedes Zeichen wird beim Bau des Fonts auf die Zielhöhe seiner Höhenklasse
skaliert (``font._groessen_anpassen``). Ein klein gezeichnetes „o“ wird dabei
viel stärker vergrößert als eine groß gezeichnete Klammer – und mit ihm sein
Strich. Dazu kommen Schwankungen beim Zeichnen selbst (Druck, Stift).

Vorgehen
--------
Vor dem Vektorisieren wird für jedes Kästchen

1. die Strichbreite in Pixeln gemessen (Median der Distanztransformation
   entlang des Skeletts),
2. vorhergesagt, wie breit dieser Strich im fertigen Font wird
   (Skalierung aus Höhenklasse und Tintenhöhe bzw. aus dem SVG-Import),
3. der Strich per vorzeichenbehafteter Distanz gleichmäßig nach innen oder
   außen versetzt, sodass er im Font die Zielbreite erreicht.

Der Versatz folgt der Kontur, der Charakter des Strichs (An- und
Abschwellen, Ecken, Strichenden) bleibt also erhalten – anders als bei
``--skel``, das alles auf ein einheitliches Skelett reduziert.

Reine Punkte (``.``, ``:``, ``·`` …) werden nicht verändert: Ihre „Breite“
ist der Punktdurchmesser, nicht die Strichbreite.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2 as cv
import numpy as np
from skimage.morphology import skeletonize

from .glyphen import EM, HOEHENKLASSEN, PRIVATE_SCHWELLE, Glyphe, klassenhoehen, metriken

SCHWELLE = 128
"""Graustufe, ab der ein Pixel als Tinte gilt (wie potrace: 50 %)."""

MIN_TINTE = 30
"""Kästchen mit weniger Tintenpixeln gelten als leer."""

PUNKT_VERHAELTNIS = 3.0
"""Skelettlänge / Strichbreite darunter: Zeichen besteht nur aus Punkten."""

MIN_FAKTOR, MAX_FAKTOR = 0.35, 3.0
"""Grenzen für neue / alte Strichbreite, damit nichts verschwindet oder verklumpt."""

MIN_BREITE_PX = 2.0


@dataclass
class Messung:
    breite_px: float          # gemessene Strichbreite im Ausschnitt
    hoehe_px: int             # Höhe der Tinte (Bounding Box)
    skelett_px: int           # Länge des Skeletts (Pixelanzahl)
    bildhoehe_px: int         # Höhe des Ausschnitts

    @property
    def punktartig(self) -> bool:
        return self.skelett_px < PUNKT_VERHAELTNIS * self.breite_px


def _tinte(grau: np.ndarray) -> np.ndarray:
    return (grau < SCHWELLE).astype(np.uint8)


def _abstaende(tinte: np.ndarray) -> np.ndarray:
    """Vorzeichenbehafteter Abstand zur Strichkante: innen positiv, außen negativ.

    Die Kante liegt zwischen den Pixeln, daher ±0,5 am Rand.
    """
    innen = cv.distanceTransform(tinte, cv.DIST_L2, 5)
    aussen = cv.distanceTransform(1 - tinte, cv.DIST_L2, 5)
    return np.where(tinte > 0, innen - 0.5, 0.5 - aussen)


def messen(grau: np.ndarray) -> Messung | None:
    """Strichbreite eines Ausschnitts messen; ``None`` bei leerem Kästchen."""
    tinte = _tinte(grau)
    if tinte.sum() < MIN_TINTE:
        return None
    abstand = _abstaende(tinte)
    skelett = skeletonize(tinte > 0)
    # Abstand Mitte → Kante ist die halbe Breite
    breite = 2 * float(np.median(abstand[skelett]))
    zeilen = np.nonzero(tinte.any(axis=1))[0]
    return Messung(
        breite_px=max(breite, 1.0),
        hoehe_px=int(zeilen[-1] - zeilen[0] + 1),
        skelett_px=int(skelett.sum()),
        bildhoehe_px=grau.shape[0],
    )


def breite_setzen(grau: np.ndarray, alt_px: float, neu_px: float) -> np.ndarray:
    """Strich um ``(neu - alt) / 2`` je Seite verbreitern bzw. verschmälern.

    Ergebnis ist ein Graustufenbild mit weicher Kante (1 px), das potrace wie
    gewohnt vektorisiert. Beim Verschmälern bleibt das Skelett mindestens
    2 px breit stehen, damit dünne Stellen nicht abreißen.
    """
    tinte = _tinte(grau)
    abstand = _abstaende(tinte) - (alt_px - neu_px) / 2
    ergebnis = np.clip(127.5 * (1 - abstand), 0, 255)
    if neu_px < alt_px:
        skelett = skeletonize(tinte > 0).astype(np.uint8)
        skelett = cv.dilate(skelett, np.ones((2, 2), np.uint8))
        ergebnis[skelett > 0] = 0
    return ergebnis.astype(np.uint8)


# --- Vorhersage der Skalierung im Font ---------------------------------------

def _glyphenname(name: str, codepoint: int) -> str:
    """Glyphenname wie FontForge ihn vergibt (für die Höhenklassen)."""
    if codepoint >= PRIVATE_SCHWELLE:
        return name
    ersatz = f"uni{codepoint:04X}" if codepoint < 0x10000 else f"u{codepoint:X}"
    # fontTools zuerst: fontforge.nameFromUnicode stürzt ab (Segfault), wenn im
    # selben Prozess zuvor ein Font geschlossen wurde.
    try:
        from fontTools.agl import UV2AGL  # noqa: PLC0415
        return UV2AGL.get(codepoint, ersatz)
    except ImportError:
        pass
    try:
        import fontforge  # noqa: PLC0415
        return fontforge.nameFromUnicode(codepoint)
    except ImportError:
        return ersatz


def _zielhoehen(belegung: list[Glyphe]) -> list[float | None]:
    """Zielhöhe im Font je Zeichen, ``None`` = Zeichen ohne Höhenklasse."""
    klasse_von = {n: k for k, namen in HOEHENKLASSEN.items() for n in namen}
    hoehen = klassenhoehen(metriken())
    ergebnis = []
    for name, codepoint in belegung:
        klasse = klasse_von.get(_glyphenname(name, codepoint))
        ergebnis.append(hoehen[klasse][0] if klasse else None)
    return ergebnis


def breite_im_font(m: Messung, zielhoehe: float | None, breite_px: float | None = None) -> float:
    """Strichbreite in Font-Einheiten nach Import und Größenanpassung.

    Mit ``breite_px`` wird eine geänderte Breite angenommen; die Tintenhöhe
    wächst bzw. schrumpft dabei mit (oben und unten je ein halber Versatz).
    """
    b = m.breite_px if breite_px is None else breite_px
    if zielhoehe is None:
        # Keine Klasse: FontForge skaliert das SVG beim Import auf die em-Höhe.
        return b * EM / m.bildhoehe_px
    return b * zielhoehe / (m.hoehe_px + b - m.breite_px)


def noetige_breite_px(m: Messung, zielhoehe: float | None, ziel: float) -> float:
    """Pixelbreite, mit der der Strich im Font ``ziel`` Einheiten breit wird."""
    if zielhoehe is None:
        return ziel * m.bildhoehe_px / EM
    # aus  b · Z / (h + b − b_alt) = ziel
    return ziel * (m.hoehe_px - m.breite_px) / (zielhoehe - ziel)


# --- Hauptfunktion -------------------------------------------------------------

@dataclass
class Bericht:
    ziel: float
    vorher: list[float]
    nachher: list[float]
    angepasst: int
    begrenzt: list[str]
    unveraendert: list[str]


def angleichen(
    jpg_dateien: list[Path],
    belegung: list[Glyphe],
    anteil: float = 1.0,
    ziel: float | None = None,
) -> Bericht:
    """Strichbreiten der Ausschnitte angleichen (Dateien werden überschrieben).

    ``anteil``: 1 = alle auf die Zielbreite, 0,5 = halber Weg dorthin.
    ``ziel``: Zielbreite in Font-Einheiten; Standard ist der Median aller Zeichen.
    """
    zielhoehen = _zielhoehen(belegung)
    eintraege = []
    unveraendert = []
    for datei, (name, _), zielhoehe in zip(jpg_dateien, belegung, zielhoehen):
        grau = cv.imread(str(datei), cv.IMREAD_GRAYSCALE)
        m = messen(grau)
        if m is None:
            continue
        if m.punktartig:
            unveraendert.append(name)
            continue
        eintraege.append((datei, name, grau, m, zielhoehe, breite_im_font(m, zielhoehe)))

    if not eintraege:
        return Bericht(ziel or 0.0, [], [], 0, [], unveraendert)

    vorher = [e[5] for e in eintraege]
    if ziel is None:
        ziel = float(np.median(vorher))

    nachher, begrenzt = [], []
    for datei, name, grau, m, zielhoehe, breite in eintraege:
        soll = breite + anteil * (ziel - breite)
        neu = noetige_breite_px(m, zielhoehe, soll)
        grenzen = (max(MIN_BREITE_PX, MIN_FAKTOR * m.breite_px), MAX_FAKTOR * m.breite_px)
        if not grenzen[0] <= neu <= grenzen[1]:
            begrenzt.append(name)
            neu = min(max(neu, grenzen[0]), grenzen[1])
        cv.imwrite(str(datei), breite_setzen(grau, m.breite_px, neu))
        nachher.append(breite_im_font(m, zielhoehe, neu))

    return Bericht(ziel, vorher, nachher, len(eintraege), begrenzt, unveraendert)

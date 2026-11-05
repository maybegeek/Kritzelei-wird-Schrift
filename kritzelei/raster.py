"""Kästchenerkennung über das bekannte Raster der Zeichenvorlage.

Nach dem Entzerren (ArUco-Randmarken) liegen die 7 × 7 Kästchen auf jedem
Bogen fast genau an denselben relativen Positionen. Statt die Kästchen frei
im Bild zu suchen, wird daher von diesen Soll-Positionen ausgegangen und
jede der vier Rahmenlinien nur noch in einem kleinen Bereich um die
erwartete Lage gesucht (Projektionsprofil: Anteil dunkler Pixel je Zeile
bzw. Spalte). Eine Rahmenlinie ist über ihre ganze Länge dunkel, ein Strich
der Glyphe, der den Rahmen berührt oder kreuzt, nur an einer Stelle – er
stört die Erkennung deshalb kaum.

Kann eine Linie nicht sicher gefunden werden, wird sie aus der
gegenüberliegenden Linie und der üblichen Kästchengröße ergänzt bzw. aus
der Lage der Nachbarkästchen derselben Zeile/Spalte geschätzt – mit einer
Warnung statt eines Abbruchs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2 as cv
import numpy as np

from .bild import Kaestchen

# --- Soll-Raster (relativ zum entzerrten Bogen, Außenkante des Rahmens) ------
# Gemessen an den Beispielbögen A, B, C (Vorlage Version 2).

SPALTEN_X = (0.0255, 0.1663, 0.3074, 0.4478, 0.5881, 0.7287, 0.8695)
ZEILEN_Y = (0.0378, 0.1776, 0.3152, 0.4549, 0.5952, 0.7342, 0.8711)
BREITE = 0.1059
HOEHE = 0.0911

SPALTEN = len(SPALTEN_X)
ZEILEN = len(ZEILEN_Y)

# Suchbereich um die erwartete Linienlage, relativ zur Kästchengröße
SUCHRADIUS = 0.12
# Mindestanteil dunkler Pixel entlang einer Linie, damit sie als Rahmen gilt
MIN_ABDECKUNG = 0.6
# zulässige Abweichung der Innenmaße vom Median aller Kästchen eines Bogens
MAX_GROESSENABWEICHUNG = 0.06
# Sicherheitsabstand zwischen Rahmen-Innenkante und Ausschnitt, relativ zur Höhe
INNENABSTAND = 0.01

OBEN, UNTEN, LINKS, RECHTS = "oben", "unten", "links", "rechts"
KANTEN = (OBEN, UNTEN, LINKS, RECHTS)


@dataclass
class Rahmen:
    """Ergebnis für ein Kästchen."""

    soll: tuple[int, int, int, int]
    """Soll-Position (x, y, w, h) der Außenkante."""
    innen: dict[str, int] = field(default_factory=dict)
    """Innenkanten des Rahmens: oben/unten (y), links/rechts (x)."""
    abdeckung: dict[str, float] = field(default_factory=dict)
    geschaetzt: set[str] = field(default_factory=set)
    """Kanten, die nicht gefunden, sondern geschätzt wurden."""

    @property
    def innen_breite(self) -> int:
        return self.innen[RECHTS] - self.innen[LINKS]

    @property
    def innen_hoehe(self) -> int:
        return self.innen[UNTEN] - self.innen[OBEN]


@dataclass
class Erkennung:
    rahmen: list[Rahmen]
    kaestchen: list[Kaestchen]
    warnungen: list[tuple[int, str]]
    """(Kästchen-Index, Text)"""


def binarisieren(grau: np.ndarray) -> np.ndarray:
    """Dunkle Linien → 1, Papier → 0; lokaler Schwellwert gegen ungleiches Licht."""
    block = int(round(grau.shape[1] / 20)) | 1
    binaer = cv.adaptiveThreshold(grau, 1, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY_INV, block, 15)
    return binaer


def soll_positionen(breite: int, hoehe: int, anzahl: int = SPALTEN * ZEILEN) -> list[tuple[int, int, int, int]]:
    w = int(round(BREITE * breite))
    h = int(round(HOEHE * hoehe))
    positionen = []
    for zeile in range(ZEILEN):
        for spalte in range(SPALTEN):
            positionen.append((int(round(SPALTEN_X[spalte] * breite)), int(round(ZEILEN_Y[zeile] * hoehe)), w, h))
    return positionen[:anzahl]


def _linie_suchen(binaer: np.ndarray, kante: str, x: int, y: int, w: int, h: int) -> tuple[int | None, float]:
    """Innenkante einer Rahmenlinie suchen. Gibt (Lage, Abdeckung) zurück."""
    bild_h, bild_w = binaer.shape
    horizontal = kante in (OBEN, UNTEN)
    radius = int(round(SUCHRADIUS * min(w, h)))

    if horizontal:
        erwartet = y if kante == OBEN else y + h - 1
        a, b = max(0, erwartet - radius), min(bild_h, erwartet + radius + 1)
        quer0, quer1 = max(0, x + w // 10), min(bild_w, x + w - w // 10)
        profil = binaer[a:b, quer0:quer1].mean(axis=1)
    else:
        erwartet = x if kante == LINKS else x + w - 1
        a, b = max(0, erwartet - radius), min(bild_w, erwartet + radius + 1)
        quer0, quer1 = max(0, y + h // 10), min(bild_h, y + h - h // 10)
        profil = binaer[quer0:quer1, a:b].mean(axis=0)

    if profil.size == 0:
        return None, 0.0
    spitze = int(np.argmax(profil))
    abdeckung = float(profil[spitze])
    if abdeckung < MIN_ABDECKUNG:
        return None, abdeckung

    # zusammenhängender Bereich der Linie um die Spitze
    grenze = 0.5 * abdeckung
    anfang = spitze
    while anfang > 0 and profil[anfang - 1] >= grenze:
        anfang -= 1
    ende = spitze
    while ende < len(profil) - 1 and profil[ende + 1] >= grenze:
        ende += 1

    # Innenkante: oben/links = erste Zeile nach der Linie, unten/rechts = Linienbeginn
    lage = a + (ende + 1 if kante in (OBEN, LINKS) else anfang)
    return lage, abdeckung


def _median(werte: list[float]) -> float | None:
    return float(np.median(werte)) if werte else None


def erkennen(bild: np.ndarray, anzahl: int = SPALTEN * ZEILEN) -> Erkennung:
    """Kästchen eines entzerrten Bogens über das Soll-Raster finden."""
    grau = cv.cvtColor(bild, cv.COLOR_BGR2GRAY) if bild.ndim == 3 else bild
    binaer = binarisieren(grau)
    hoehe_bild, breite_bild = grau.shape

    rahmen_liste: list[Rahmen] = []
    for soll in soll_positionen(breite_bild, hoehe_bild, anzahl):
        r = Rahmen(soll=soll)
        for kante in KANTEN:
            lage, abdeckung = _linie_suchen(binaer, kante, *soll)
            r.abdeckung[kante] = abdeckung
            if lage is None:
                r.geschaetzt.add(kante)
            else:
                r.innen[kante] = lage
        rahmen_liste.append(r)

    def sicher(r: Rahmen, *kanten: str) -> bool:
        return all(k not in r.geschaetzt for k in kanten)

    # typische Innenmaße und Linienversatz (Ist − Soll) aus den sicheren Kästchen
    med_b = _median([r.innen_breite for r in rahmen_liste if sicher(r, LINKS, RECHTS)])
    med_h = _median([r.innen_hoehe for r in rahmen_liste if sicher(r, OBEN, UNTEN)])

    # Plausibilität: weicht ein Maß zu stark ab, ist die schwächere Kante verdächtig
    for r in rahmen_liste:
        for a, b, med, innen in ((LINKS, RECHTS, med_b, "innen_breite"), (OBEN, UNTEN, med_h, "innen_hoehe")):
            if med and sicher(r, a, b) and abs(getattr(r, innen) - med) > MAX_GROESSENABWEICHUNG * med:
                schwach = a if r.abdeckung[a] < r.abdeckung[b] else b
                r.geschaetzt.add(schwach)
                del r.innen[schwach]

    def versatz(kante: str, r: Rahmen, nachbarn: list[Rahmen]) -> int:
        soll_x, soll_y, _, _ = r.soll
        werte = []
        for n in nachbarn:
            if kante in n.geschaetzt:
                continue
            nx, ny, _, _ = n.soll
            werte.append(n.innen[kante] - (ny if kante in (OBEN, UNTEN) else nx))
        basis = soll_y if kante in (OBEN, UNTEN) else soll_x
        med = _median(werte)
        if med is not None:
            return int(round(basis + med))
        # ohne Nachbarn: typische Linienstärke grob annehmen
        _, _, w, h = r.soll
        dicke = int(round(0.04 * h))
        return {OBEN: soll_y + dicke, UNTEN: soll_y + h - dicke,
                LINKS: soll_x + dicke, RECHTS: soll_x + w - dicke}[kante]

    gegenueber = {OBEN: UNTEN, UNTEN: OBEN, LINKS: RECHTS, RECHTS: LINKS}
    warnungen: list[tuple[int, str]] = []
    for index, r in enumerate(rahmen_liste):
        if not r.geschaetzt:
            continue
        zeile, spalte = divmod(index, SPALTEN)
        for kante in sorted(r.geschaetzt, key=KANTEN.index):
            g = gegenueber[kante]
            med = med_h if kante in (OBEN, UNTEN) else med_b
            if g not in r.geschaetzt and med:
                vorzeichen = 1 if kante in (UNTEN, RECHTS) else -1
                r.innen[kante] = int(round(r.innen[g] + vorzeichen * med))
            else:
                if kante in (OBEN, UNTEN):
                    nachbarn = rahmen_liste[zeile * SPALTEN : (zeile + 1) * SPALTEN]
                else:
                    nachbarn = rahmen_liste[spalte::SPALTEN]
                r.innen[kante] = versatz(kante, r, nachbarn)
        warnungen.append((index, "Rahmen nicht sicher erkannt (" + ", ".join(
            k for k in KANTEN if k in r.geschaetzt) + "), Lage geschätzt"))

    kaestchen = []
    for r in rahmen_liste:
        rand = max(2, int(round(INNENABSTAND * r.soll[3])))
        x0, x1 = r.innen[LINKS] + rand, r.innen[RECHTS] - rand
        y0, y1 = r.innen[OBEN] + rand, r.innen[UNTEN] - rand
        kaestchen.append(Kaestchen(x0, y0, max(1, x1 - x0), max(1, y1 - y0)))

    return Erkennung(rahmen_liste, kaestchen, warnungen)


def randreste_entfernen(ausschnitt: np.ndarray) -> np.ndarray:
    """Kleine dunkle Reste entfernen, die nur in einem schmalen Randstreifen liegen.

    Das sind typischerweise Überbleibsel der Rahmenlinie. Teile der Glyphe,
    die über den Randstreifen hinaus nach innen reichen, bleiben erhalten.
    """
    grau = cv.cvtColor(ausschnitt, cv.COLOR_BGR2GRAY) if ausschnitt.ndim == 3 else ausschnitt
    _, binaer = cv.threshold(grau, 0, 255, cv.THRESH_BINARY_INV | cv.THRESH_OTSU)
    h, w = binaer.shape
    streifen = max(3, int(round(0.03 * min(h, w))))
    anzahl, marken, werte, _ = cv.connectedComponentsWithStats(binaer, connectivity=8)
    ergebnis = ausschnitt.copy()
    for i in range(1, anzahl):
        x, y, bw, bh, _ = werte[i]
        im_streifen = (
            y + bh <= streifen or y >= h - streifen      # oben/unten
            or x + bw <= streifen or x >= w - streifen   # links/rechts
        )
        if im_streifen:
            ergebnis[marken == i] = 255
    return ergebnis


def markieren(bild: np.ndarray, erkennung: Erkennung, beschriftungen: list[str] | None = None) -> np.ndarray:
    """Kontrollbild: Soll-Raster (blau), gefundener Rahmen (grün, geschätzt: orange),
    Ausschnitt für die Glyphe (rot), Beschriftung je Kästchen."""
    markiert = bild.copy() if bild.ndim == 3 else cv.cvtColor(bild, cv.COLOR_GRAY2BGR)
    dicke = max(2, markiert.shape[1] // 500)
    for index, (r, k) in enumerate(zip(erkennung.rahmen, erkennung.kaestchen)):
        x, y, w, h = r.soll
        cv.rectangle(markiert, (x, y), (x + w, y + h), (255, 120, 0), dicke)
        farbe = (0, 140, 255) if r.geschaetzt else (40, 170, 40)
        cv.rectangle(markiert, (r.innen[LINKS], r.innen[OBEN]), (r.innen[RECHTS], r.innen[UNTEN]), farbe, dicke)
        cv.rectangle(markiert, (k.x, k.y), (k.x + k.w, k.y + k.h), (0, 0, 220), max(1, dicke // 2))
        text = beschriftungen[index] if beschriftungen else str(index + 1)
        cv.putText(markiert, text, (x + dicke * 2, y + h - dicke * 3), cv.FONT_HERSHEY_SIMPLEX,
                   h / 160, (0, 0, 220), max(1, dicke // 2), cv.LINE_AA)
    return markiert

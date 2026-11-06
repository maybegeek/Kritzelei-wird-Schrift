"""Stresstests für die Raster-Erkennung.

Aus dem Beispielbogen A werden künstlich erschwerte Varianten erzeugt:
Striche über den Rahmen, ungleichmäßiges Licht, gewölbtes Papier.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei import raster  # noqa: E402

BOGEN = ROOT / "Kritzelei-Bilder-Vorbereitung" / "A.jpg"
BERUEHRT = [0, 3, 8, 16, 24, 30, 40, 48]


@pytest.fixture(scope="module")
def bogen():
    return cv2.imread(str(BOGEN))


@pytest.fixture(scope="module")
def referenz(bogen):
    return raster.erkennen(bogen)


def striche_ueber_rahmen(bild, referenz):
    """In einigen Kästchen dicke Striche quer über den Rahmen zeichnen."""
    bild = bild.copy()
    for i in BERUEHRT:
        k = referenz.kaestchen[i]
        cx, cy = k.x + k.w // 2, k.y + k.h // 2
        # nach rechts unten aus dem Kästchen hinaus und nach oben durch den Rahmen
        cv2.line(bild, (cx, cy), (k.x + k.w + 25, k.y + k.h + 20), (20, 20, 20), 7)
        cv2.line(bild, (cx - 20, cy), (cx - 10, k.y - 30), (20, 20, 20), 6)
    return bild


def ungleiches_licht(bild):
    """Helligkeitsverlauf von 35 % (links oben) bis 100 % plus Schattenkeil."""
    h, w = bild.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    faktor = 0.35 + 0.65 * (xx / w + yy / h) / 2
    faktor[(xx > 0.6 * w) & (yy < 0.4 * h)] *= 0.6
    return np.clip(bild.astype(np.float32) * faktor[..., None], 0, 255).astype(np.uint8)


def gewoelbt(bild, staerke=12):
    """Papierwölbung: Zeilen in der Bildmitte bis zu `staerke` px nach unten verschoben."""
    h, w = bild.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    map_y = yy - staerke * np.sin(np.pi * xx / w) * np.sin(np.pi * yy / h)
    return cv2.remap(bild, xx, map_y, cv2.INTER_LINEAR, borderValue=(200, 200, 200))


def rahmenfrei(bild, erkennung):
    """Kein Ausschnitt darf an seinem Rand noch Rahmenlinie enthalten."""
    grau = cv2.cvtColor(bild, cv2.COLOR_BGR2GRAY)
    dunkel = raster.binarisieren(grau)
    for index, k in enumerate(erkennung.kaestchen):
        stueck = dunkel[k.y : k.y + k.h, k.x : k.x + k.w]
        for rand in (stueck[:2], stueck[-2:], stueck[:, :2], stueck[:, -2:]):
            assert rand.mean() < 0.35, f"Kästchen {index + 1}: Rahmenrest im Ausschnitt"


def abstand(a, b):
    return max(max(abs(p.x - q.x), abs(p.y - q.y), abs(p.w - q.w), abs(p.h - q.h)) for p, q in zip(a, b))


def test_originalbogen_ohne_warnungen(bogen, referenz):
    assert len(referenz.kaestchen) == 49
    assert referenz.warnungen == []
    rahmenfrei(bogen, referenz)


def test_striche_ueber_den_rahmen(bogen, referenz):
    bild = striche_ueber_rahmen(bogen, referenz)
    erkennung = raster.erkennen(bild)
    assert abstand(erkennung.kaestchen, referenz.kaestchen) <= 3


def test_ungleiches_licht(bogen, referenz):
    bild = ungleiches_licht(bogen)
    erkennung = raster.erkennen(bild)
    assert erkennung.warnungen == []
    assert abstand(erkennung.kaestchen, referenz.kaestchen) <= 3


def test_gewoelbtes_papier(bogen):
    bild = gewoelbt(bogen)
    erkennung = raster.erkennen(bild)
    assert erkennung.warnungen == []
    rahmenfrei(bild, erkennung)


def test_alles_zusammen(bogen, referenz):
    bild = gewoelbt(ungleiches_licht(striche_ueber_rahmen(bogen, referenz)))
    erkennung = raster.erkennen(bild)
    assert len(erkennung.kaestchen) == 49
    rahmenfrei(bild, erkennung)


def test_fehlende_linie_wird_geschaetzt(bogen, referenz):
    """Rahmenlinie übermalt → Warnung, Lage aus Nachbarn/Gegenseite geschätzt."""
    bild = bogen.copy()
    r = referenz.rahmen[10]
    x, y, w, h = r.soll
    # obere Linie mit Papierfarbe übermalen
    cv2.rectangle(bild, (x - 5, y - 8), (x + w + 5, r.innen["oben"] + 1), (190, 190, 190), -1)
    erkennung = raster.erkennen(bild)
    assert [i for i, _ in erkennung.warnungen] == [10]
    assert abs(erkennung.kaestchen[10].y - referenz.kaestchen[10].y) <= 4


def test_randreste_entfernen():
    ausschnitt = np.full((150, 150, 3), 190, np.uint8)
    cv2.rectangle(ausschnitt, (0, 0), (60, 2), (20, 20, 20), -1)        # Rest der Rahmenlinie
    cv2.line(ausschnitt, (75, 0), (75, 100), (20, 20, 20), 6)           # Glyphe, berührt den Rand
    cv2.circle(ausschnitt, (40, 120), 6, (20, 20, 20), -1)              # Punkt
    sauber = raster.randreste_entfernen(ausschnitt)
    assert sauber[1, 20].max() == 255          # Linienrest entfernt
    assert sauber[50, 75].max() < 100          # Glyphe bleibt
    assert sauber[1, 75].max() < 100           # auch ihr Teil am Rand
    assert sauber[120, 40].max() < 100         # Punkt bleibt

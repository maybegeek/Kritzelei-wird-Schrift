"""Tests für das Angleichen der Strichbreite (kritzelei/strich.py)."""

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei import strich  # noqa: E402


def kreis(dicke, radius=50, groesse=174):
    """Weißes Kästchen mit einem schwarzen Ring („o“) der Strichstärke `dicke`."""
    bild = np.full((groesse, groesse), 255, np.uint8)
    cv2.circle(bild, (groesse // 2, groesse // 2), radius, 0, dicke, cv2.LINE_AA)
    return bild


@pytest.mark.parametrize("dicke", [4, 8, 14])
def test_breite_wird_gemessen(dicke):
    m = strich.messen(kreis(dicke))
    assert m.breite_px == pytest.approx(dicke, abs=1.5)
    assert not m.punktartig


def test_leeres_kaestchen():
    assert strich.messen(np.full((100, 100), 255, np.uint8)) is None


def test_punkt_bleibt_punkt():
    bild = np.full((174, 174), 255, np.uint8)
    cv2.circle(bild, (87, 140), 8, 0, -1)
    assert strich.messen(bild).punktartig


@pytest.mark.parametrize("alt, neu", [(6, 12), (12, 5)])
def test_breite_setzen(alt, neu):
    vorher = kreis(alt)
    m = strich.messen(vorher)
    nachher = strich.breite_setzen(vorher, m.breite_px, neu)
    assert strich.messen(nachher).breite_px == pytest.approx(neu, abs=1.5)


def test_verschmaelern_reisst_nicht_ab():
    """Auch bei starkem Verschmälern bleibt der Ring geschlossen."""
    vorher = kreis(5)
    nachher = strich.breite_setzen(vorher, 5, 0.5)
    anzahl, _ = cv2.connectedComponents((nachher < 128).astype(np.uint8))
    assert anzahl - 1 == 1


def test_vorhersage_trifft_ziel():
    """Mit der berechneten Pixelbreite wird der Strich im Font genau `ziel` breit."""
    m = strich.messen(kreis(6))
    zielhoehe = 862.1  # x-Höhe
    neu = strich.noetige_breite_px(m, zielhoehe, 90)
    assert strich.breite_im_font(m, zielhoehe, neu) == pytest.approx(90)
    assert strich.breite_im_font(m, None, strich.noetige_breite_px(m, None, 90)) == pytest.approx(90)


def test_kleines_und_grosses_o_werden_gleich(tmp_path):
    """Ein klein gezeichnetes „o“ wird stärker skaliert – nach dem Angleichen
    haben beide im Font dieselbe Strichbreite."""
    klein, gross = tmp_path / "klein.jpg", tmp_path / "gross.jpg"
    cv2.imwrite(str(klein), kreis(6, radius=25))
    cv2.imwrite(str(gross), kreis(6, radius=60))
    belegung = [("o", ord("o")), ("o.ss01", 993078)]
    bericht = strich.angleichen([klein, gross], belegung)
    assert max(bericht.vorher) / min(bericht.vorher) > 2
    assert max(bericht.nachher) / min(bericht.nachher) < 1.05
    assert not bericht.begrenzt

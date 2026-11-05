"""Tests für Kritzelei wird Schrift.

    python3 -m pytest tests

Die Bildtests verwenden die Beispielbögen im Repository; der Font-Test
läuft nur, wenn das FontForge-Python-Modul und potrace vorhanden sind.
"""

import shutil
import sys
from pathlib import Path

import cv2
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei.bild import entzerren, kaestchen_finden  # noqa: E402
from kritzelei.glyphen import BELEGUNG, HOEHENKLASSEN, KAESTCHEN_PRO_BLATT, belegung  # noqa: E402

ORIGINALE = ROOT / "Kritzelei-Bilder-Original"
VORBEREITET = ROOT / "Kritzelei-Bilder-Vorbereitung"


def test_belegung_passt_auf_die_boegen():
    assert len(belegung(2)) == 3 * KAESTCHEN_PRO_BLATT
    assert len(belegung(1)) == 137


def test_belegung_ohne_doppelte_codepoints():
    for version, glyphen in BELEGUNG.items():
        codepoints = [cp for _, cp in glyphen]
        assert len(codepoints) == len(set(codepoints)), version


def test_unbekannte_version():
    with pytest.raises(ValueError):
        belegung(99)


def test_hoehenklassen_ohne_doppelte():
    alle = [g for namen in HOEHENKLASSEN.values() for g in namen]
    assert len(alle) == len(set(alle))


@pytest.mark.parametrize("bogen", ["A", "B", "C"])
def test_entzerren_wie_vorbereitet(bogen):
    entzerrt = entzerren(cv2.imread(str(ORIGINALE / f"{bogen}.jpg")))
    erwartet = cv2.imread(str(VORBEREITET / f"{bogen}.jpg"), cv2.IMREAD_GRAYSCALE)
    assert entzerrt.shape == erwartet.shape


@pytest.mark.parametrize("bogen", ["A", "B", "C"])
def test_alle_kaestchen_erkannt(bogen):
    kaestchen = kaestchen_finden(cv2.imread(str(VORBEREITET / f"{bogen}.jpg")))
    assert len(kaestchen) == KAESTCHEN_PRO_BLATT
    # zeilenweise sortiert: erste Zeile hat die kleinsten y-Werte
    erste_zeile = kaestchen[:7]
    assert max(k.y for k in erste_zeile) < min(k.y for k in kaestchen[7:])
    assert [k.x for k in erste_zeile] == sorted(k.x for k in erste_zeile)


def test_font_wird_erstellt(tmp_path):
    pytest.importorskip("fontforge")
    if shutil.which("potrace") is None:
        pytest.skip("potrace fehlt")
    from kritzelei.font import font_erstellen
    from kritzelei.vektor import POTRACE_PROFILE, glyphen_ausschneiden, vektorisieren

    boegen = [VORBEREITET / f"{b}.jpg" for b in "ABC"]
    jpgs = glyphen_ausschneiden(boegen, tmp_path, "Test")
    _, svgs = vektorisieren(jpgs, POTRACE_PROFILE["standard"])
    sfd = font_erstellen(svgs, belegung(2), "Test", tmp_path)

    import fontforge
    font = fontforge.open(str(sfd))
    try:
        assert font.fontname == "Test-Regular"
        for name in ["A", "z", "germandbls", "c_k.liga", "pfote.lig", "u1F43E", ".notdef"]:
            assert name in font, name
            assert font[name].isWorthOutputting()

        # Größenanpassung: alle Zeichen einer Höhenklasse gleich hoch, gleiche Unterkante
        for klasse, namen in HOEHENKLASSEN.items():
            boxen = [font[n].boundingBox() for n in namen if n in font]
            hoehen = [y1 - y0 for _, y0, _, y1 in boxen]
            unterkanten = [y0 for _, y0, _, _ in boxen]
            assert max(hoehen) - min(hoehen) <= 2, klasse
            assert max(unterkanten) - min(unterkanten) <= 2, klasse
    finally:
        font.close()

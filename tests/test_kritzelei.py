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

from kritzelei import raster  # noqa: E402
from kritzelei.bild import entzerren  # noqa: E402
from kritzelei.glyphen import BELEGUNG, HOEHENKLASSEN, KAESTCHEN_PRO_BLATT, beschriftung  # noqa: E402

ORIGINALE = ROOT / "Kritzelei-Bilder-Original"
VORBEREITET = ROOT / "Kritzelei-Bilder-Vorbereitung"


def test_belegung_passt_auf_die_boegen():
    assert len(BELEGUNG) == 3 * KAESTCHEN_PRO_BLATT


def test_belegung_ohne_doppelte_codepoints():
    codepoints = [cp for _, cp in BELEGUNG]
    assert len(codepoints) == len(set(codepoints))


@pytest.mark.parametrize("name, text", [
    ("A", "A"), ("Ä", "Ä"), ("§", "§"), ("ẞ", "ẞ (groß)"), ("–", "Gedankenstrich"), ("„", "„ unten"),
    ("ﬃ", "ffi-Ligatur"), ("c_k.liga", "ck-Ligatur"), ("a.ss02", "a Variante 2"), ("copyright", "©"),
    ("uni203d", "‽ (Interrobang)"), ("long", "ſ (langes s)"),
])
def test_beschriftung(name, text):
    assert beschriftung(name) == text


def test_beschriftungen_eindeutig_und_darstellbar():
    from fontTools.ttLib import TTFont

    texte = [beschriftung(name) for name, _ in BELEGUNG]
    assert len(texte) == len(set(texte))
    zeichenvorrat = TTFont(raster.BESCHRIFTUNG_SCHRIFT).getBestCmap()
    fehlend = {z for text in texte for z in text if ord(z) not in zeichenvorrat}
    assert not fehlend


def test_kontrollbild_beschriftet_sonderzeichen():
    bild = cv2.imread(str(VORBEREITET / "C.jpg"))
    erkennung = raster.erkennen(bild, 3)
    ohne = raster.markieren(bild, erkennung, ["", "", ""])
    mit = raster.markieren(bild, erkennung, ["Gedankenstrich", "ẞ", "‽ (Interrobang)"])
    assert (ohne != mit).any()


def test_frei_geschriebene_zeichen_ohne_hoehenklasse():
    """G, J, ẞ, ſ werden sehr unterschiedlich geschrieben und behalten ihre Größe."""
    alle = {g for namen in HOEHENKLASSEN.values() for g in namen}
    assert alle.isdisjoint({"G", "J", "uni1E9E", "longs"})


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
    kaestchen = raster.erkennen(cv2.imread(str(VORBEREITET / f"{bogen}.jpg"))).kaestchen
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
    sfd = font_erstellen(svgs, BELEGUNG, "Test", tmp_path)

    import fontforge
    font = fontforge.open(str(sfd))
    try:
        assert font.fontname == "Test-Regular"
        for name in ["A", "z", "germandbls", "c_k.liga", "pfote.lig", "u1F43E", ".notdef"]:
            assert name in font, name
            assert font[name].isWorthOutputting()

        # Hints: auch der Regular-Schnitt bekommt welche
        assert font["n"].vhints and font["H"].vhints

        # Wortabstand: breit genug, damit kurze Wörter nicht zusammenkleben
        assert font["space"].width == font["uni00A0"].width
        assert font["space"].width >= font["i"].width
        # besondere Leerzeichen: Reihenfolge von schmal nach breit bleibt erhalten
        breiten = [font[n].width for n in ("uni200B", "uni200A", "uni2009", "space", "uni2002", "uni2003")]
        assert breiten == sorted(breiten) and len(set(breiten)) == len(breiten)

        # Größenanpassung: alle Zeichen einer Höhenklasse gleich hoch, gleiche Unterkante
        for klasse, namen in HOEHENKLASSEN.items():
            boxen = [font[n].boundingBox() for n in namen if n in font]
            hoehen = [y1 - y0 for _, y0, _, y1 in boxen]
            unterkanten = [y0 for _, y0, _, _ in boxen]
            assert max(hoehen) - min(hoehen) <= 2, klasse
            assert max(unterkanten) - min(unterkanten) <= 2, klasse

        def box(name):
            return font[name].boundingBox()

        def hoehe(name):
            _, y0, _, y1 = box(name)
            return y1 - y0

        # umgedrehte Satzzeichen: so groß wie das Ausgangszeichen, bis zur Unterlänge
        for unten, oben in [("questiondown", "question"), ("exclamdown", "exclam"), ("uni2E18", "uni203D")]:
            assert abs(hoehe(unten) - hoehe(oben)) <= 2, unten
            assert abs(box(unten)[1] - box("g")[1]) <= 2, unten
        # Interrobang und Absatzzeichen wie Großbuchstaben
        for name in ("uni203D", "paragraph"):
            assert all(abs(a - b) <= 2 for a, b in zip(box(name)[1::2], box("A")[1::2])), name
        # tt-Ligatur mit Unterlänge wie die ff-Ligatur
        assert all(abs(a - b) <= 2 for a, b in zip(box("t_t.liga")[1::2], box("uniFB00")[1::2]))
        # Copyleft an Ort und Stelle des Copyright-Zeichens
        assert all(abs(a - b) <= 2 for a, b in zip(box("u1F12F"), box("copyright")))
        # hochgestellte Ziffern: halbe Ziffernhöhe, Oberkante auf Versalhöhe
        for hoch, ziffer in [("uni00B9", "one"), ("uni00B2", "two"), ("uni00B3", "three")]:
            assert abs(hoehe(hoch) - hoehe(ziffer) / 2) <= 2, hoch
            assert abs(box(hoch)[3] - box("H")[3]) <= 2, hoch
    finally:
        font.close()

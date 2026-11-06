"""Tests für die Schriftschnitte aus der überarbeiteten Regular-Datei."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei import auftrag  # noqa: E402

BEISPIEL = ROOT / "Output" / "Kritzelei" / "Kritzelei-Regular.sfd"


def regular_anlegen(ordner: Path, winkel: float = 0) -> Path:
    """Eine überarbeitete Regular-Datei: hier mit Winkel, wie bei geneigter Handschrift."""
    import fontforge

    if not BEISPIEL.exists():
        pytest.skip("Beispiel-Font fehlt")
    font = fontforge.open(str(BEISPIEL))
    try:
        font.fontname, font.familyname = "Test-Regular", "Test"
        font.italicangle = winkel
        ziel = ordner / "Test-Regular.sfd"
        font.save(str(ziel))
    finally:
        font.close()
    return ziel


@pytest.fixture(scope="module")
def schnitte(tmp_path_factory):
    pytest.importorskip("fontforge")
    from kritzelei.schnitte import STILE, schnitte_ableiten

    regular = regular_anlegen(tmp_path_factory.mktemp("schnitte"))
    return regular, {p.stem.split("-")[1]: p for p in schnitte_ableiten(regular, list(STILE))}


def otf_lesen(sfd, tmp_path):
    from fontTools.ttLib import TTFont

    otf = tmp_path / f"{sfd.stem}.otf"
    subprocess.run(auftrag.befehl_schriftprobe(sfd, otf), cwd=ROOT, check=True, capture_output=True)
    return TTFont(otf)


def umriss(pfad, zeichen="n"):
    import fontforge

    font = fontforge.open(str(pfad))
    try:
        return font[zeichen].boundingBox(), font[zeichen].width
    finally:
        font.close()


def test_drei_dateien(schnitte):
    assert sorted(schnitte[1]) == ["Bold", "BoldItalic", "Italic"]
    assert all(p.is_file() for p in schnitte[1].values())


@pytest.mark.parametrize("stil, unterfamilie, voll, gewicht, mac, fs_bits, winkel, panose", [
    ("Italic", "Italic", "Test Italic", 400, 0x02, 0x01, -12, 5),
    ("Bold", "Bold", "Test Bold", 700, 0x01, 0x20, 0, 8),
    ("BoldItalic", "Bold Italic", "Test Bold Italic", 700, 0x03, 0x21, -12, 8),
])
def test_kennzeichen_einer_familie(schnitte, tmp_path, stil, unterfamilie, voll, gewicht, mac, fs_bits, winkel, panose):
    font = otf_lesen(schnitte[1][stil], tmp_path)
    namen = font["name"]
    assert namen.getDebugName(1) == "Test"  # dieselbe Familie
    assert namen.getDebugName(2) == unterfamilie
    assert namen.getDebugName(4) == voll
    assert namen.getDebugName(6) == f"Test-{stil}"
    assert font["OS/2"].usWeightClass == gewicht
    assert font["head"].macStyle == mac
    assert font["OS/2"].fsSelection & 0x61 == fs_bits & 0x61
    assert font["post"].italicAngle == winkel
    assert font["OS/2"].panose.bFamilyType == 3 and font["OS/2"].panose.bWeight == panose


def test_zeichen_und_merkmale_bleiben(schnitte, tmp_path):
    def merkmale(font):
        return {r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord}

    regular = otf_lesen(schnitte[0], tmp_path)
    for pfad in schnitte[1].values():
        font = otf_lesen(pfad, tmp_path)
        assert font.getBestCmap().keys() == regular.getBestCmap().keys()
        assert merkmale(font) == merkmale(regular)


def test_umrisse_und_laufweite(schnitte):
    (x0, _, x1, _), breite = umriss(schnitte[0])
    for stil in ("Bold", "BoldItalic", "Italic"):
        assert umriss(schnitte[1][stil])[1] == breite, stil  # die Laufweite bleibt überall
    (fx0, _, fx1, _), _ = umriss(schnitte[1]["Bold"])
    (kx0, _, kx1, _), _ = umriss(schnitte[1]["Italic"])
    assert fx1 - fx0 > x1 - x0  # fett: kräftiger
    assert kx1 - kx0 > x1 - x0  # kursiv: schräg


def test_neigung_baut_auf_dem_winkel_der_regular_auf(tmp_path):
    pytest.importorskip("fontforge")
    import fontforge

    from kritzelei.schnitte import schnitte_ableiten

    regular = regular_anlegen(tmp_path, winkel=-10)
    kursiv, = schnitte_ableiten(regular, ["Italic"], neigung=11)
    font = fontforge.open(str(kursiv))
    try:
        assert font.italicangle == -21
    finally:
        font.close()


def test_regular_als_quelle_pflicht(schnitte):
    from kritzelei.schnitte import SchnittFehler, ziele

    with pytest.raises(SchnittFehler):
        ziele(schnitte[1]["Bold"], ["Italic"])


def test_nur_kennzeichen_laesst_umrisse_und_setzt_felder(tmp_path):
    pytest.importorskip("fontforge")
    import fontforge

    from kritzelei.schnitte import SchnittFehler, nur_kennzeichnen

    regular = regular_anlegen(tmp_path, winkel=-5)
    with pytest.raises(SchnittFehler, match="fehlen"):
        nur_kennzeichnen(regular, ["Bold"])

    handarbeit = tmp_path / "Test-Bold.sfd"
    shutil.copy(regular, handarbeit)  # „von Hand gestaltet“: Inhalt wie Regular, Kennzeichen falsch
    vorher = umriss(handarbeit)
    nur_kennzeichnen(regular, ["Bold"])
    assert umriss(handarbeit) == vorher
    font = fontforge.open(str(handarbeit))
    try:
        assert (font.fontname, font.weight, font.os2_weight) == ("Test-Bold", "Bold", 700)
        assert font.italicangle == -5
    finally:
        font.close()
    assert (tmp_path / "Test-Bold.sfd.bak").exists()
    assert (tmp_path / "Test-Regular.sfd.bak").exists()


def test_skript_ueberschreibt_nur_auf_wunsch(tmp_path):
    pytest.importorskip("fontforge")
    regular = regular_anlegen(tmp_path)
    handarbeit = tmp_path / "Test-Italic.sfd"
    handarbeit.write_text("alt")

    def lauf(ueberschreiben):
        befehl = auftrag.befehl_schnitte(regular, ["Italic"], False, 46, 12, ueberschreiben)
        return subprocess.run(befehl, cwd=ROOT, capture_output=True, text=True)

    aus = lauf(False)
    assert aus.returncode == 1 and "Test-Italic.sfd" in aus.stderr and handarbeit.read_text() == "alt"
    assert lauf(True).returncode == 0
    assert handarbeit.read_text() != "alt"
    assert (tmp_path / "Test-Italic.sfd.bak").read_text() == "alt"


def test_fontname_aus_sfd_lesen(tmp_path):
    datei = tmp_path / "x.sfd"
    datei.write_text("SplineFontDB: 3.0\nFontName: Mein-Font-Regular\nFullName: Mein Font\nBeginChars: 1 1\n")
    assert auftrag.sfd_stamm(datei) == "Mein-Font"
    assert auftrag.sfd_stamm(tmp_path / "gibtsnicht.sfd") is None


def test_regular_vom_font_aufbau_gekennzeichnet():
    fontforge = pytest.importorskip("fontforge")
    from kritzelei.font import _font_anlegen

    font = _font_anlegen("T")
    try:
        assert (font.os2_stylemap, font.os2_weight) == (0x40, 400)
        assert font.os2_panose[:3] == (3, 0, 5)
    finally:
        font.close()
    assert fontforge  # nur für importorskip

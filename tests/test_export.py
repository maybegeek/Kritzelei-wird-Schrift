"""Tests für den Export: Formate, ZIP-Inhalt, Hinweistext."""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei import auftrag  # noqa: E402
from kritzelei.export import ExportFehler, liesmich_text, sfd_finden, zip_packen  # noqa: E402

BEISPIEL = ROOT / "Output" / "Kritzelei" / "Kritzelei-Regular.sfd"


@pytest.fixture(scope="module")
def ausgabe(tmp_path_factory):
    pytest.importorskip("fontforge")
    if not BEISPIEL.exists():
        pytest.skip("Beispiel-Font fehlt")
    ordner = tmp_path_factory.mktemp("export") / "Test"
    ordner.mkdir()
    shutil.copy(BEISPIEL, ordner / "Kritzelei-Regular.sfd")
    (ordner / "Kritzelei-Regular.sfd.bak").write_text("Sicherung")
    (ordner / "Kritzelei-001.jpg").write_text("Zwischendatei")
    (ordner / "info.txt").write_text("Zwischendatei")
    ziel = ordner.parent / "paket.zip"
    aus = subprocess.run(auftrag.befehl_export(ordner, ["otf", "ttf", "woff2", "ufo"], ziel), cwd=ROOT,
                         capture_output=True, text=True)
    assert aus.returncode == 0, aus.stderr
    return ordner, ziel


def test_formate_nach_zweck(ausgabe):
    export = ausgabe[0] / "export"
    assert (export / "installieren" / "Kritzelei-Regular.otf").is_file()
    assert (export / "installieren" / "Kritzelei-Regular.ttf").is_file()
    assert (export / "web" / "Kritzelei-Regular.woff2").is_file()
    assert (export / "bearbeiten" / "Kritzelei-Regular.ufo" / "fontinfo.plist").is_file()


def test_exportierte_dateien_sind_lesbar(ausgabe):
    from fontTools.ttLib import TTFont
    from fontTools.ufoLib import UFOReader

    export = ausgabe[0] / "export"
    assert "CFF " in TTFont(export / "installieren" / "Kritzelei-Regular.otf")
    assert "glyf" in TTFont(export / "installieren" / "Kritzelei-Regular.ttf")
    assert TTFont(export / "web" / "Kritzelei-Regular.woff2").flavor == "woff2"
    ufo = UFOReader(str(export / "bearbeiten" / "Kritzelei-Regular.ufo"))
    assert len(ufo.getGlyphSet().keys()) > 150
    assert "liga" in ufo.readFeatures()


def test_zip_enthaelt_nur_das_wichtige(ausgabe):
    with zipfile.ZipFile(ausgabe[1]) as paket:
        namen = paket.namelist()
        assert "Kritzelei/LIESMICH.md" in namen
        assert "Kritzelei/bearbeiten/Kritzelei-Regular.sfd" in namen
        assert "Kritzelei/installieren/Kritzelei-Regular.otf" in namen
        assert "Kritzelei/web/Kritzelei-Regular.woff2" in namen
        assert any(n.startswith("Kritzelei/bearbeiten/Kritzelei-Regular.ufo/glyphs/") for n in namen)
        assert not any(n.endswith((".bak", ".jpg", "info.txt")) for n in namen)
        assert "# Ihre Schrift: Kritzelei" in paket.read("Kritzelei/LIESMICH.md").decode("utf-8")


def test_abgewaehltes_format_faellt_weg(ausgabe, tmp_path):
    ordner = tmp_path / "Test"
    shutil.copytree(ausgabe[0], ordner)
    ziel = tmp_path / "nur.zip"
    aus = subprocess.run(auftrag.befehl_export(ordner, ["otf"], ziel), cwd=ROOT, capture_output=True, text=True)
    assert aus.returncode == 0, aus.stderr
    assert not (ordner / "export" / "web" / "Kritzelei-Regular.woff2").exists()
    with zipfile.ZipFile(ziel) as paket:
        assert not any(".woff2" in n or ".ufo" in n or ".ttf" in n for n in paket.namelist())


def test_nur_sfd_ohne_formate(tmp_path):
    (tmp_path / "A-Regular.sfd").write_text("x")
    ziel = zip_packen(tmp_path, tmp_path / "unter" / "a.zip", [])
    with zipfile.ZipFile(ziel) as paket:
        assert sorted(paket.namelist()) == ["A/LIESMICH.md", "A/bearbeiten/A-Regular.sfd"]
    assert not ziel.with_name("a.zip.tmp").exists()


def test_liesmich_passt_zum_stand():
    regular = [Path("F-Regular.sfd")]
    alle = [Path(f"F-{s}.sfd") for s in ("Bold", "BoldItalic", "Italic", "Regular")]
    erst = liesmich_text("F", regular, ["otf"])
    assert "`bearbeiten/F-Regular.sfd`" in erst and "lassen sich daraus" in erst and "web/" not in erst
    assert "[Quellcode auf GitHub](https://github.com/maybegeek/Kritzelei-wird-Schrift)" in erst
    assert "Christoph Pfeiffer" in erst and "3. Juni 2019" in erst and "26. Dezember 2021" in erst
    spaeter = liesmich_text("F", alle, ["otf", "woff2", "ufo"])
    assert "automatisch abgeleitet" in spaeter and "lassen sich daraus" not in spaeter
    assert "`*.ufo`" in spaeter and "`web/`" in spaeter
    assert "{" not in spaeter


def test_ohne_sfd_klare_meldung(tmp_path):
    with pytest.raises(ExportFehler, match="Keine"):
        sfd_finden(tmp_path)
    aus = subprocess.run(auftrag.befehl_export(tmp_path, ["otf"]), cwd=ROOT, capture_output=True, text=True)
    assert aus.returncode == 1 and "Keine" in aus.stderr


def test_speichern_unter_befehl(monkeypatch):
    monkeypatch.setattr(auftrag.shutil, "which", lambda name: f"/usr/bin/{name}" if name == "zenity" else None)
    befehl = auftrag.befehl_speichern_unter("T", Path("/a/F.zip"), 7)
    assert "--save" in befehl and "--filename=/a/F.zip" in befehl and "--attach=7" in befehl
    monkeypatch.setattr(auftrag.shutil, "which", lambda name: None)
    assert auftrag.befehl_speichern_unter("T", Path("/a/F.zip")) is None


def test_export_seite():
    tk = pytest.importorskip("tkinter")
    ctk = pytest.importorskip("customtkinter")
    from kritzelei.oberflaeche import Oberflaeche

    try:
        fenster = ctk.CTk()
    except tk.TclError:
        pytest.skip("keine Anzeige vorhanden")
    fenster.withdraw()
    app = Oberflaeche(fenster)
    meldungen = []
    app._fehler = lambda titel, text: meldungen.append(text)
    try:
        app.ziel.set("gibtsnicht")
        app.zeige("Export")
        assert "Noch keine" in app.export_info.cget("text")
        assert app.export_formate_gewaehlt() == ["otf", "woff2", "ufo"]
        app.nur_exportieren()
        assert meldungen and not app.beschaeftigt
    finally:
        app.beenden()

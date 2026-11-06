"""Tests für die Bedienoberfläche: Aufrufe der Skripte und ein Lauf ohne sichtbares Fenster."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei import auftrag  # noqa: E402
from kritzelei.auftrag import ScanEinstellungen, befehl_scan2svg  # noqa: E402

VORBEREITET = ROOT / "Kritzelei-Bilder-Vorbereitung"
BEISPIEL_SFD = ROOT / "Output" / "Kritzelei" / "Kritzelei-Regular.sfd"


def scan2svg_argumente(befehl):
    """Der Befehl muss zum echten Parser passen – so fällt jede Änderung am Skript auf."""
    spec = importlib.util.spec_from_file_location("scan2svg", ROOT / "Kritzelei-wird-Schrift-Scan2SVG.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul.argumente(befehl[3:])


def test_scan2svg_standard():
    args = scan2svg_argumente(befehl_scan2svg(ScanEinstellungen(Path("s"), Path("z"), "Test")))
    assert (args.scans, args.output, args.name) == (Path("s"), Path("z"), "Test")
    assert args.erkennung == "raster" and args.version == 2 and args.rmppm
    assert args.breite_anpassen is None and not args.buntstift and not args.ptdefault


def test_scan2svg_alle_optionen():
    args = scan2svg_argumente(befehl_scan2svg(ScanEinstellungen(
        Path("s"), Path("z"), "Test", version=1, erkennung="kontur", schwellwert=120, blur=5,
        stift="buntstift", breite_anteil=0.5, strichbreite=90.0, skel=True, ohne_font=True,
        rmppm=False, rmjpg=True, rmsvg=True)))
    assert args.version == 1 and args.erkennung == "kontur" and args.threshold == 120 and args.blur == 5
    assert args.buntstift and args.breite_anpassen == 0.5 and args.strichbreite == 90.0
    assert args.skel and args.ohne_font and args.rmjpg and args.rmsvg and not args.rmppm


def test_scan2svg_ptdefault():
    assert scan2svg_argumente(befehl_scan2svg(ScanEinstellungen(Path("s"), Path("z"), "T", stift="default"))).ptdefault


def test_strichbreite_ohne_anpassung_entfaellt():
    befehl = befehl_scan2svg(ScanEinstellungen(Path("s"), Path("z"), "T", strichbreite=90.0))
    assert "--strichbreite" not in befehl


def _fontforge_umgebung(monkeypatch, befehle, flatpak_app):
    monkeypatch.setattr(auftrag.shutil, "which", lambda name: f"/usr/bin/{name}" if name in befehle else None)
    monkeypatch.setattr(auftrag.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0 if flatpak_app else 1))


def test_fontforge_flatpak_geht_vor(monkeypatch):
    _fontforge_umgebung(monkeypatch, {"flatpak", "fontforge"}, flatpak_app=True)
    befehl = auftrag.befehl_fontforge(Path("/a/b/F.sfd"))
    assert befehl == ["flatpak", "run", "--filesystem=/a/b", auftrag.FONTFORGE_FLATPAK, "/a/b/F.sfd"]


def test_fontforge_ohne_flatpak_app(monkeypatch):
    _fontforge_umgebung(monkeypatch, {"flatpak", "fontforge"}, flatpak_app=False)
    assert auftrag.befehl_fontforge(Path("/a/F.sfd")) == ["fontforge", "/a/F.sfd"]


def test_fontforge_nirgends(monkeypatch):
    _fontforge_umgebung(monkeypatch, set(), flatpak_app=False)
    assert auftrag.befehl_fontforge(Path("/a/F.sfd")) is None


def test_fehlersuche_aufruf_laeuft(tmp_path):
    befehl = auftrag.befehl_fehlersuche(VORBEREITET, 2, auftrag.AUTOMATISCH, 100, tmp_path)
    assert subprocess.run(befehl, cwd=ROOT, capture_output=True).returncode == 0
    assert sorted(d.name for d in tmp_path.glob("*.jpg")) == ["A.jpg", "B.jpg", "C.jpg"]


@pytest.mark.parametrize("name", ["Kritzelei-01", "a_b", "9x"])
def test_gueltige_namen(name):
    assert auftrag.name_pruefen(name) is None


@pytest.mark.parametrize("name", ["", "mit leerzeichen", "Größe", "../weg", "-x"])
def test_ungueltige_namen(name):
    assert auftrag.name_pruefen(name)


def test_strichbreite_lesen():
    assert auftrag.strichbreite_lesen("") is None
    assert auftrag.strichbreite_lesen(" 90,5 ") == 90.5
    for falsch in ("abc", "0", "-3"):
        with pytest.raises(ValueError):
            auftrag.strichbreite_lesen(falsch)


def test_schwellwert_nur_bei_kontur():
    assert auftrag.schwellwert_aktiv(2, "kontur")
    assert auftrag.schwellwert_aktiv(1, auftrag.AUTOMATISCH)
    assert not auftrag.schwellwert_aktiv(2, auftrag.AUTOMATISCH)
    assert not auftrag.schwellwert_aktiv(1, "raster")


def test_boegen_hinweis():
    assert "Keine" in auftrag.boegen_hinweis([])
    assert auftrag.boegen_hinweis(auftrag.bilder_finden(VORBEREITET)).startswith("3 Bögen")
    assert "Nur 1" in auftrag.boegen_hinweis([Path("A.jpg")])
    assert "ersten drei" in auftrag.boegen_hinweis([Path(f"{c}.jpg") for c in "ABCD"])


def test_zeilenart():
    assert auftrag.zeilenart("A.jpg: 49 Kästchen, 0 unsicher – ok") is None
    assert auftrag.zeilenart("A.jpg: 49 Kästchen, 2 unsicher – PRÜFEN") == "warnung"
    assert auftrag.zeilenart("Warnung: A.jpg, Kästchen 3: Lage geschätzt") == "warnung"
    assert auftrag.zeilenart("Fehler: 3 SVG-Dateien gefunden") == "fehler"
    assert not auftrag.zeile_zeigen("Program root: /usr")


def test_schriftprobe(tmp_path):
    if importlib.util.find_spec("fontforge") is None or not BEISPIEL_SFD.exists():
        pytest.skip("FontForge oder Beispiel-Font fehlt")
    from kritzelei.schriftprobe import setzen

    otf = tmp_path / "probe.otf"
    subprocess.run(auftrag.befehl_schriftprobe(BEISPIEL_SFD, otf), cwd=ROOT, check=True, capture_output=True)
    kurz = setzen(otf, "Hallo", 40, 600)
    lang = setzen(otf, "Hallo Welt, das ist eine lange Zeile mit vielen Wörtern darin", 40, 600)
    assert kurz.width == lang.width == 600
    assert lang.height > kurz.height  # umgebrochen
    assert kurz.convert("L").getextrema()[0] < 128  # es steht etwas da


def test_fenster_baut_den_richtigen_auftrag():
    tk = pytest.importorskip("tkinter")
    from kritzelei.oberflaeche import Oberflaeche

    try:
        fenster = tk.Tk()
    except tk.TclError:
        pytest.skip("keine Anzeige vorhanden")
    fenster.withdraw()
    app = Oberflaeche(fenster)
    try:
        app.name.set("Neu")
        assert app.ziel.get() == "Output/Neu"  # folgt dem Namen
        app.ziel.set("Anderswo")
        app.name.set("Neu2")
        assert app.ziel.get() == "Anderswo"  # von Hand gesetzt, bleibt

        app.breite_an.set(True)
        app.breite_anteil.set(0.5)
        app.stift.set("buntstift")
        args = scan2svg_argumente(befehl_scan2svg(app.einstellungen()))
        assert args.name == "Neu2" and args.buntstift and args.breite_anpassen == 0.5
        assert args.output == auftrag.WURZEL / "Anderswo"

        app.strichbreite.set("abc")
        with pytest.raises(ValueError):
            app.einstellungen()
        app.strichbreite.set("")
        app.name.set("mit leerzeichen")
        with pytest.raises(ValueError):
            app.einstellungen()
    finally:
        app.beenden()


def test_abbrechen_beendet_den_prozess():
    tk = pytest.importorskip("tkinter")
    from kritzelei.oberflaeche import Oberflaeche

    try:
        fenster = tk.Tk()
    except tk.TclError:
        pytest.skip("keine Anzeige vorhanden")
    fenster.withdraw()
    app = Oberflaeche(fenster)
    try:
        aufgerufen = []
        app.starten([sys.executable, "-u", "-c", "import time; print('los'); time.sleep(60)"], "Test",
                    aufgerufen.append)
        assert app.beschaeftigt
        app.abbrechen()
        app._prozess.wait(timeout=5)
        while app.beschaeftigt:
            fenster.update()
        assert aufgerufen == []  # nach Abbruch geht es nicht automatisch weiter
    finally:
        app.beenden()

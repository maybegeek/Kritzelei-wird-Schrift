"""Tests für die Bedienoberfläche: Aufrufe der Skripte und ein Lauf ohne sichtbares Fenster."""

import importlib.util
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei import auftrag, strich  # noqa: E402
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
    assert args.rmppm
    assert args.strichbreite_anpassen == strich.STANDARD_ANTEIL and not args.buntstift and not args.ptdefault


@pytest.mark.parametrize("zusatz, anteil", [
    ([], strich.STANDARD_ANTEIL),
    (["--strichbreite-anpassen"], 1.0),
    (["--strichbreite-anpassen", "0"], 0.0),
    (["--strichbreite-anpassen", "0.5"], 0.5),
    (["--strichbreite", "90"], 1.0),
    (["--strichbreite-anpassen", "0.5", "--strichbreite", "90"], 0.5),
])
def test_strichbreite_anpassen_kommandozeile(zusatz, anteil):
    assert scan2svg_argumente(["python3", "-u", "skript", "-s", "s", *zusatz]).strichbreite_anpassen == anteil


@pytest.mark.parametrize("zusatz", [
    ["--strichbreite-anpassen", "1.5"],
    ["--strichbreite-anpassen", "-0.1"],
    ["--strichbreite-anpassen", "0", "--strichbreite", "90"],
])
def test_strichbreite_anpassen_ungueltig(zusatz):
    with pytest.raises(SystemExit):
        scan2svg_argumente(["python3", "-u", "skript", "-s", "s", *zusatz])


def test_vorgabe_der_oberflaeche_wie_im_skript():
    assert ScanEinstellungen.strichbreite_anteil == strich.STANDARD_ANTEIL


def test_scan2svg_alle_optionen():
    args = scan2svg_argumente(befehl_scan2svg(ScanEinstellungen(
        Path("s"), Path("z"), "Test", blur=5,
        stift="buntstift", strichbreite_anteil=0.5, strichbreite=90.0, ohne_font=True,
        rmppm=False, rmjpg=True, rmsvg=True)))
    assert args.blur == 5
    assert args.buntstift and args.strichbreite_anpassen == 0.5 and args.strichbreite == 90.0
    assert args.ohne_font and args.rmjpg and args.rmsvg and not args.rmppm


def test_skel_gibt_es_nicht_mehr():
    with pytest.raises(SystemExit):
        scan2svg_argumente(["python3", "-u", "skript", "-s", "s", "--skel"])


def test_scan2svg_ptdefault():
    assert scan2svg_argumente(befehl_scan2svg(ScanEinstellungen(Path("s"), Path("z"), "T", stift="default"))).ptdefault


def test_strichbreite_ohne_anpassung_entfaellt():
    args = scan2svg_argumente(befehl_scan2svg(ScanEinstellungen(Path("s"), Path("z"), "T", strichbreite_anteil=0,
                                                                strichbreite=90.0)))
    assert args.strichbreite_anpassen == 0 and args.strichbreite is None


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
    befehl = auftrag.befehl_fehlersuche(VORBEREITET, tmp_path)
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
    assert not auftrag.zeile_zeigen("Warning: No stroke output for contour")


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
    ctk = pytest.importorskip("customtkinter")
    from kritzelei.oberflaeche import Oberflaeche

    try:
        fenster = ctk.CTk()
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

        assert app.einstellungen().strichbreite_anteil == strich.STANDARD_ANTEIL  # vorab eingeschaltet
        app.strichbreite_an.set(False)
        assert scan2svg_argumente(befehl_scan2svg(app.einstellungen())).strichbreite_anpassen == 0

        app.strichbreite_an.set(True)
        app.strichbreite_anteil.set(0.5)
        app.stift.set("buntstift")
        args = scan2svg_argumente(befehl_scan2svg(app.einstellungen()))
        assert args.name == "Neu2" and args.buntstift and args.strichbreite_anpassen == 0.5
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
    ctk = pytest.importorskip("customtkinter")
    from kritzelei.oberflaeche import Oberflaeche

    try:
        fenster = ctk.CTk()
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


def test_bilder_der_oberflaeche_vorhanden():
    for name in ("titel.png", "schriftprobe.png"):
        assert (ROOT / "template" / "oberflaeche" / name).is_file()


def test_bildlaufleiste_nur_bei_bedarf():
    """Wie im echten Start: Das Fenster wird versteckt aufgebaut und erst dann gezeigt."""
    tk = pytest.importorskip("tkinter")
    ctk = pytest.importorskip("customtkinter")
    from kritzelei.oberflaeche import Oberflaeche, Rollflaeche

    try:
        fenster = ctk.CTk()
    except tk.TclError:
        pytest.skip("keine Anzeige vorhanden")

    def warten():
        for _ in range(30):
            fenster.update()
            time.sleep(0.02)

    def rollflaeche(widget):
        if isinstance(widget, Rollflaeche):
            return widget
        return next(filter(None, map(rollflaeche, widget.winfo_children())), None)

    fenster.withdraw()
    app = Oberflaeche(fenster)
    try:
        fenster.deiconify()
        fenster.geometry("1160x820")
        warten()
        rolle = rollflaeche(app.seiten["Start"])
        assert not rolle.leiste_sichtbar
        # die Karten nutzen die ganze Breite, nichts wird rechts abgeschnitten
        assert rolle.inhalt.winfo_width() == rolle.winfo_width()
        fenster.geometry("1160x500")
        warten()
        assert rolle.leiste_sichtbar
        fenster.geometry("1160x820")
        warten()
        assert not rolle.leiste_sichtbar
    finally:
        app.beenden()


def test_schnitte_seite_baut_den_aufruf():
    tk = pytest.importorskip("tkinter")
    ctk = pytest.importorskip("customtkinter")
    from kritzelei import oberflaeche
    from kritzelei.oberflaeche import Oberflaeche

    try:
        fenster = ctk.CTk()
    except tk.TclError:
        pytest.skip("keine Anzeige vorhanden")
    fenster.withdraw()
    app = Oberflaeche(fenster)
    meldungen = []
    alt = oberflaeche.messagebox.showerror
    oberflaeche.messagebox.showerror = lambda t, m, **k: meldungen.append(m)
    try:
        app.zeige("Schriftschnitte")
        app.schnitt_quelle.set("gibtsnicht.sfd")
        app.schnitte_erzeugen()
        assert "Regular-Datei" in meldungen[-1] and not app.beschaeftigt
        app.schnitt_art.set("kennzeichen")
        app._schnitt_art_geaendert()
        assert app.schnitt_staerke_regler.cget("state") == "disabled"
    finally:
        oberflaeche.messagebox.showerror = alt
        app.beenden()

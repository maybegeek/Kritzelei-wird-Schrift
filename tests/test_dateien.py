"""Tests für die zulässigen Bilddateien: jpg, JPG, jpeg und png in allen Schritten."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kritzelei import auftrag  # noqa: E402
from kritzelei.dateien import bilder_finden  # noqa: E402

ORIGINALE = ROOT / "Kritzelei-Bilder-Original"
VORBEREITET = ROOT / "Kritzelei-Bilder-Vorbereitung"


def gemischt(quelle: Path, ziel: Path) -> Path:
    """A.JPG, B.jpeg und C.png mit demselben Bildinhalt wie die Beispielbögen anlegen."""
    ziel.mkdir()
    shutil.copy(quelle / "A.jpg", ziel / "A.JPG")
    shutil.copy(quelle / "B.jpg", ziel / "B.jpeg")
    cv2.imwrite(str(ziel / "C.png"), cv2.imread(str(quelle / "C.jpg")))
    return ziel


def test_auswahl_und_sortierung(tmp_path):
    for name in ["C.png", "A.JPG", "B.jpeg", "D.PNG", "notiz.txt", "Schriftname.txt", "E.gif"]:
        (tmp_path / name).touch()
    (tmp_path / "F.jpg").mkdir()  # ein Ordner ist kein Bild
    assert [d.name for d in bilder_finden(tmp_path)] == ["A.JPG", "B.jpeg", "C.png", "D.PNG"]


def test_fehlender_ordner(tmp_path):
    assert bilder_finden(tmp_path / "gibtsnicht") == []


def test_oberflaeche_und_skripte_nutzen_dieselbe_suche():
    assert auftrag.bilder_finden is bilder_finden


def test_vorbereitung_schreibt_immer_jpg(tmp_path):
    quelle = gemischt(ORIGINALE, tmp_path / "quelle")
    ziel = tmp_path / "ziel"
    (tmp_path / "ziel").mkdir()
    (ziel / "A.jpg").write_bytes(b"alt")  # ein neuer Lauf ersetzt das alte Ergebnis
    befehl = auftrag.befehl_vorbereitung(quelle, ziel)
    assert subprocess.run(befehl, cwd=ROOT, capture_output=True).returncode == 0
    assert sorted(d.name for d in ziel.iterdir()) == ["A.jpg", "B.jpg", "C.jpg"]
    assert cv2.imread(str(ziel / "A.jpg")) is not None


def test_vorbereitung_warnt_bei_gleichem_namen(tmp_path):
    quelle = tmp_path / "quelle"
    quelle.mkdir()
    shutil.copy(ORIGINALE / "A.jpg", quelle / "A.jpg")
    shutil.copy(ORIGINALE / "A.jpg", quelle / "A.jpeg")
    aus = subprocess.run(auftrag.befehl_vorbereitung(quelle, tmp_path / "ziel"), cwd=ROOT,
                         capture_output=True, text=True)
    assert "Warnung" in aus.stdout


def test_fehlersuche_mit_gemischten_endungen(tmp_path):
    quelle = gemischt(VORBEREITET, tmp_path / "quelle")
    markiert = tmp_path / "markiert"
    befehl = auftrag.befehl_fehlersuche(quelle, markiert)
    assert subprocess.run(befehl, cwd=ROOT, capture_output=True).returncode == 0
    assert [d.name for d in bilder_finden(markiert)] == ["A.JPG", "B.jpeg", "C.png"]


def test_scan2svg_findet_gemischte_endungen(tmp_path):
    spec = importlib.util.spec_from_file_location("scan2svg", ROOT / "Kritzelei-wird-Schrift-Scan2SVG.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    quelle = gemischt(VORBEREITET, tmp_path / "quelle")
    boegen = modul.boegen(modul.argumente(["-s", str(quelle)]))
    assert [d.name for d in boegen] == ["A.JPG", "B.jpeg", "C.png"]


def test_scan2svg_ohne_bilder(tmp_path):
    spec = importlib.util.spec_from_file_location("scan2svg", ROOT / "Kritzelei-wird-Schrift-Scan2SVG.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    with pytest.raises(SystemExit, match="Keine Bilddateien"):
        modul.boegen(modul.argumente(["-s", str(tmp_path)]))

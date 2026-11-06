"""Aus den Einstellungen der Oberfläche werden Aufrufe der Kommandozeilen-Skripte.

Die Oberfläche startet die Skripte als eigene Prozesse: So gibt es nur einen
Arbeitsablauf, und ein Absturz in FontForge reißt das Fenster nicht mit.
Dieses Modul braucht weder Tk noch FontForge und lässt sich daher einfach testen.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]

FONTFORGE_FLATPAK = "org.fontforge.FontForge"
AUTOMATISCH = "automatisch"
ERKENNUNG_AUSWAHL = (AUTOMATISCH, "raster", "kontur")
STIFT_AUSWAHL = {
    "standard": "Fineliner, Kugelschreiber (Standard)",
    "buntstift": "Buntstift, Farbe, uneinheitliche Deckkraft",
    "default": "potrace-Standard (genauer, mehr Punkte)",
}

_NAME_MUSTER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
_FEHLER_MUSTER = re.compile(r"^\s*(Fehler|Traceback)|FEHLER|nicht gelesen|Randmarken|^usage:|error:")
_WARN_MUSTER = re.compile(r"^\s*Warnung|PRÜFEN|geschätzt")


@dataclass
class ScanEinstellungen:
    """Eine Zeile pro Option von ``Kritzelei-wird-Schrift-Scan2SVG.py``."""

    scans: Path
    ziel: Path
    name: str
    version: int = 2
    erkennung: str = AUTOMATISCH
    schwellwert: int = 100
    blur: int = 3
    stift: str = "standard"
    strichbreite_anteil: float = 0.75  # 0 = aus; Vorgabe wie strich.STANDARD_ANTEIL
    strichbreite: float | None = None
    skel: bool = False
    ohne_font: bool = False
    rmppm: bool = True
    rmjpg: bool = False
    rmsvg: bool = False


def _skript(name: str, *argumente) -> list[str]:
    # -u: Ausgaben sofort weiterreichen, damit das Protokoll mitläuft
    return [sys.executable, "-u", str(WURZEL / name), *map(str, argumente)]


def befehl_vorbereitung(fotos: Path, ziel: Path) -> list[str]:
    return _skript("Kritzelei-Bilder-Vorbereitung.py", "-s", fotos, "-o", ziel, "--ohne-vorschau")


def befehl_fehlersuche(scans: Path, version: int, erkennung: str, schwellwert: int,
                       speichern: Path) -> list[str]:
    befehl = _skript("Kritzelei-Bilder-Fehlersuche.py", "-s", scans, "-v", version,
                     "-t", schwellwert, "--speichern", speichern)
    if erkennung != AUTOMATISCH:
        befehl += ["--erkennung", erkennung]
    return befehl


def befehl_scan2svg(e: ScanEinstellungen) -> list[str]:
    befehl = _skript("Kritzelei-wird-Schrift-Scan2SVG.py", "-s", e.scans, "-o", e.ziel, "-n", e.name,
                     "-v", e.version, "-t", e.schwellwert, "--blur", e.blur)
    if e.erkennung != AUTOMATISCH:
        befehl += ["--erkennung", e.erkennung]
    if e.stift == "buntstift":
        befehl.append("--buntstift")
    elif e.stift == "default":
        befehl.append("--ptdefault")
    befehl += ["--strichbreite-anpassen", str(e.strichbreite_anteil)]
    if e.strichbreite_anteil and e.strichbreite is not None:
        befehl += ["--strichbreite", str(e.strichbreite)]
    for gesetzt, schalter in ((e.skel, "--skel"), (e.ohne_font, "--ohne-font"), (e.rmppm, "--rmppm"),
                              (e.rmjpg, "--rmjpg"), (e.rmsvg, "--rmsvg")):
        if gesetzt:
            befehl.append(schalter)
    return befehl


def befehl_svg2font(ordner: Path, name: str, version: int) -> list[str]:
    return _skript("Kritzelei-wird-Schrift-SVG2Font.py", "-svg", ordner, "-n", name, "-v", version)


def befehl_schriftprobe(sfd: Path, otf: Path) -> list[str]:
    return [sys.executable, "-u", "-m", "kritzelei.schriftprobe", str(sfd), str(otf)]


def befehl_fontforge(sfd: Path) -> list[str] | None:
    """Aufruf des grafischen FontForge oder ``None``, wenn es keines geben kann.

    Das Flatpak hat immer eine Oberfläche und geht vor. Der Befehl ``fontforge``
    kann auch ``fontforge-nox`` sein; das zeigt sich erst beim Start.
    """
    if shutil.which("flatpak") and subprocess.run(
            ["flatpak", "info", FONTFORGE_FLATPAK], capture_output=True).returncode == 0:
        return ["flatpak", "run", f"--filesystem={sfd.parent}", FONTFORGE_FLATPAK, str(sfd)]
    if shutil.which("fontforge"):
        return ["fontforge", str(sfd)]
    return None


def anzeigen(befehl: list[str]) -> str:
    """Befehl so, wie man ihn im Projektordner selbst eintippen würde."""
    teile = ["python3", *befehl[2:]]
    wurzel = f"{WURZEL}/"
    return shlex.join(t.removeprefix(wurzel) for t in teile)


def pfad(text: str) -> Path:
    """Eingabe aus einem Ordnerfeld; relative Angaben beziehen sich auf den Projektordner."""
    return WURZEL / text.strip()


def name_pruefen(name: str) -> str | None:
    """Fehlermeldung oder ``None``: Der Name landet im PostScript-Namen und im Dateinamen."""
    if not _NAME_MUSTER.fullmatch(name):
        return ("Der Schriftname darf nur aus Buchstaben A–Z, Ziffern, „-“ und „_“ bestehen "
                "und muss mit einem Buchstaben oder einer Ziffer beginnen.")
    return None


def strichbreite_lesen(text: str) -> float | None:
    """Leeres Feld = Median aller Zeichen; ``ValueError`` bei ungültiger Eingabe."""
    text = text.strip().replace(",", ".")
    if not text:
        return None
    wert = float(text)
    if wert <= 0:
        raise ValueError(text)
    return wert


def schwellwert_aktiv(version: int, erkennung: str) -> bool:
    """Der Schwellwert wirkt nur bei der Konturerkennung (Standard bei Vorlage 1)."""
    return erkennung == "kontur" or (erkennung == AUTOMATISCH and version != 2)


def bilder_finden(ordner: Path) -> list[Path]:
    """Dieselbe Auswahl, die die Skripte treffen."""
    return sorted(ordner.glob("*.jpg")) if ordner.is_dir() else []


def boegen_hinweis(dateien: list[Path]) -> str:
    if not dateien:
        return "Keine *.jpg-Dateien gefunden."
    namen = ", ".join(d.name for d in dateien)
    if len(dateien) == 3:
        return f"3 Bögen: {namen}"
    if len(dateien) > 3:
        return f"{len(dateien)} Bilder ({namen}) – verwendet werden nur die ersten drei."
    return f"Nur {len(dateien)} von 3 Bögen ({namen}) – sie werden der Reihe nach als A, B, C gelesen."


def sfd_dateien(ziel: Path) -> list[Path]:
    """Fonts im Zielordner, dazu der SKEL-Font aus dem Unterordner."""
    if not ziel.is_dir():
        return []
    return sorted(ziel.glob("*.sfd")) + sorted((ziel / "SKEL").glob("*.sfd"))


def zeilenart(zeile: str) -> str | None:
    """Einordnung einer Ausgabezeile für die Hervorhebung im Protokoll."""
    if _FEHLER_MUSTER.search(zeile):
        return "fehler"
    if _WARN_MUSTER.search(zeile):
        return "warnung"
    return None


def zeile_zeigen(zeile: str) -> bool:
    """FontForge meldet sich beim Import, das hilft im Protokoll niemandem."""
    return not zeile.startswith("Program root")

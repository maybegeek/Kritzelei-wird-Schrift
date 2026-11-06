"""Schriftschnitte: Italic, Bold und Bold-Italic aus einer überarbeiteten Regular-Datei.

Die Schnitte entstehen bewusst erst nach der Überarbeitung in FontForge, damit
Korrekturen nicht in vier Dateien anfallen. Zwei Betriebsarten:

* ``schnitte_ableiten``: Umrisse automatisch verstärken bzw. neigen (Ausgangspunkt
  für die weitere Arbeit) und die Kennzeichen setzen.
* ``nur_kennzeichnen``: vorhandene, von Hand gestaltete Dateien bekommen nur die
  richtigen Kennzeichen, die Umrisse bleiben unberührt.

Kennzeichen sind die Felder, die sich zwischen den Schnitten einer Familie
unterscheiden: Namen, Gewicht, Neigungswinkel, Stil-Zuordnung und Panose.
Abgeleitete Schnitte bekommen eigene Hints, die der Regular-Datei passen nach dem
Verstärken und Neigen nicht mehr. Überschriebene Dateien werden vorher als
``*.sfd.bak`` gesichert.
"""

from __future__ import annotations

import math
import shutil
from pathlib import Path

import fontforge
import psMat

from .font import hints_erneuern

STAERKE = 46
"""Um so viele Einheiten (bezogen auf em 2048) wird der Strich im fetten Schnitt dicker."""

NEIGUNG = 12
"""Um so viele Grad wird der kursive Schnitt gegenüber Regular zusätzlich geneigt."""

_EM_BEZUG = 2048

# Schnitt → (fett, kursiv)
STILE = {"Italic": (False, True), "Bold": (True, False), "BoldItalic": (True, True)}

_STILNAMEN = {"Regular": "Regular", "Italic": "Italic", "Bold": "Bold", "BoldItalic": "Bold Italic"}
_OS2_REGULAR, _OS2_KURSIV, _OS2_FETT = 0x40, 0x01, 0x20
# Panose: 3 = handschriftlich, an dritter Stelle das Gewicht (5 normal, 8 fett)
_PANOSE_NORMAL = (3, 0, 5, 0, 0, 0, 0, 0, 0, 0)
_PANOSE_FETT = (3, 0, 8, 0, 0, 0, 0, 0, 0, 0)
# Diese Namen würden sonst vom Regular-Schnitt übernommen und stünden im falschen Schnitt.
_NAMEN_JE_SCHNITT = {"SubFamily", "Fullname", "UniqueID", "PostScriptName", "Preferred Styles", "Compatible Full"}


class SchnittFehler(ValueError):
    """Die Eingabe passt nicht, die Meldung ist für die Nutzenden bestimmt."""


def _stamm(font) -> str:
    """Name vor dem Bindestrich: aus ``Kritzelei-01-Regular`` wird ``Kritzelei-01``."""
    stamm, _, stil = font.fontname.rpartition("-")
    if stil in STILE:
        raise SchnittFehler(f"{font.fontname} ist schon ein abgeleiteter Schnitt. "
                            "Bitte die Regular-Datei angeben.")
    return stamm if stil == "Regular" else font.fontname


def _kennzeichnen(font, stamm: str, familie: str, stil: str, winkel: float) -> None:
    fett, kursiv = STILE.get(stil, (False, False))
    font.fontname = f"{stamm}-{stil}"
    font.familyname = familie
    font.fullname = f"{familie} {_STILNAMEN[stil]}"
    font.weight = "Bold" if fett else "Regular"
    font.os2_weight = 700 if fett else 400
    font.italicangle = winkel
    font.os2_stylemap = ((_OS2_FETT if fett else 0) | (_OS2_KURSIV if kursiv else 0)) or _OS2_REGULAR
    font.os2_panose = _PANOSE_FETT if fett else _PANOSE_NORMAL
    font.sfnt_names = tuple(n for n in font.sfnt_names if n[1] not in _NAMEN_JE_SCHNITT)
    # Von selbst schriebe FontForge hier „BoldItalic“, Programme erwarten „Bold Italic“.
    font.appendSFNTName("English (US)", "SubFamily", _STILNAMEN[stil])


def regular_hinweise(regular: Path) -> list[str]:
    """Was an der Regular-Datei nicht zu einer vollständigen Familie passt."""
    font = fontforge.open(str(regular))
    try:
        hinweise = []
        if font.os2_stylemap != _OS2_REGULAR:
            hinweise.append("Stil-Zuordnung (StyleMap) ist nicht „Regular“")
        if font.os2_weight != 400:
            hinweise.append(f"Gewicht ist {font.os2_weight} statt 400")
        return hinweise
    finally:
        font.close()


def ziele(regular: Path, stile: list[str]) -> dict[str, Path]:
    """Die Dateien der Schnitte, sie liegen neben der Regular-Datei."""
    font = fontforge.open(str(regular))
    try:
        stamm = _stamm(font)
    finally:
        font.close()
    return {stil: regular.with_name(f"{stamm}-{stil}.sfd") for stil in stile}


def _sichern(datei: Path) -> None:
    if datei.exists():
        shutil.copy2(datei, datei.with_name(datei.name + ".bak"))


def _speichern(font, ziel: Path) -> Path:
    font.selection.all()
    font.correctDirection()
    font.round()
    font.addExtrema()
    hints_erneuern(font)
    _sichern(ziel)
    font.save(str(ziel))
    return ziel


def _ableiten(quelle: Path, ziel: Path, stil: str, staerke: float, neigung: float, stamm: str, familie: str,
              grundwinkel: float, verstaerken: bool) -> Path:
    fett, kursiv = STILE[stil]
    font = fontforge.open(str(quelle))
    try:
        font.selection.all()
        font.unlinkReferences()
        if verstaerken:
            # squish: Die Laufweiten bleiben, damit passt auch das übernommene Kerning weiter.
            font.changeWeight(staerke * font.em / _EM_BEZUG, "auto", 0, 0, "squish")
        if kursiv:
            font.selection.all()
            font.transform(psMat.skew(math.radians(neigung)))
        _kennzeichnen(font, stamm, familie, stil, grundwinkel - neigung if kursiv else grundwinkel)
        return _speichern(font, ziel)
    finally:
        font.close()


def schnitte_ableiten(regular: Path, stile: list[str], staerke: float = STAERKE,
                      neigung: float = NEIGUNG) -> list[Path]:
    """Schnitte aus der Regular-Datei ableiten; ihr eigener Neigungswinkel bleibt die Grundlage."""
    font = fontforge.open(str(regular))
    try:
        stamm, familie, grundwinkel = _stamm(font), font.familyname, font.italicangle
    finally:
        font.close()
    dateien = ziele(regular, stile)
    ergebnis = []
    for stil in ("Italic", "Bold", "BoldItalic"):
        if stil not in stile:
            continue
        # Bold-Italic baut auf dem frisch erzeugten Bold auf, das spart das aufwendige Verstärken.
        aus_bold = stil == "BoldItalic" and "Bold" in stile
        quelle = dateien["Bold"] if aus_bold else regular
        ergebnis.append(_ableiten(quelle, dateien[stil], stil, staerke, neigung, stamm, familie, grundwinkel,
                                  verstaerken=STILE[stil][0] and not aus_bold))
    return ergebnis


def nur_kennzeichnen(regular: Path, stile: list[str], neigung: float = NEIGUNG) -> list[Path]:
    """Vorhandene Dateien kennzeichnen, die Umrisse bleiben. Regular wird mit angepasst."""
    font = fontforge.open(str(regular))
    try:
        stamm, familie, grundwinkel = _stamm(font), font.familyname, font.italicangle
    finally:
        font.close()
    dateien = ziele(regular, stile)
    fehlend = [d.name for d in dateien.values() if not d.is_file()]
    if fehlend:
        raise SchnittFehler(f"Diese Dateien fehlen: {', '.join(fehlend)}.")

    ergebnis = []
    for stil, datei in {"Regular": regular, **dateien}.items():
        font = fontforge.open(str(datei))
        try:
            winkel = grundwinkel
            if STILE.get(stil, (False, False))[1]:
                # Ein von Hand gesetzter Winkel bleibt, sonst Grundwinkel plus Neigung.
                winkel = font.italicangle if font.italicangle != grundwinkel else grundwinkel - neigung
            _kennzeichnen(font, stamm, familie, stil, winkel)
            _sichern(datei)
            font.save(str(datei))
            ergebnis.append(datei)
        finally:
            font.close()
    return ergebnis

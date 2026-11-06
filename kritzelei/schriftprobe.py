"""Schriftprobe: SFD in eine OTF-Datei wandeln und Beispieltext damit setzen.

Die Umwandlung läuft als eigener Prozess (``python3 -m kritzelei.schriftprobe a.sfd b.otf``),
das Setzen des Textes kommt mit Pillow aus.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def otf_erzeugen(sfd: Path, otf: Path) -> None:
    # erst hier importieren: fontforge wird nur für diesen Schritt gebraucht
    import fontforge

    font = fontforge.open(str(sfd))
    try:
        font.generate(str(otf))
    finally:
        font.close()


def _umbrechen(absatz: str, schrift: ImageFont.FreeTypeFont, breite: int) -> list[str]:
    zeilen, zeile = [], ""
    for wort in absatz.split(" "):
        versuch = f"{zeile} {wort}" if zeile else wort
        if zeile and schrift.getlength(versuch) > breite:
            zeilen.append(zeile)
            zeile = wort
        else:
            zeile = versuch
    zeilen.append(zeile)
    return zeilen


def setzen(otf: Path, text: str, groesse: int, breite: int) -> Image.Image:
    """Text mit Umbruch auf die gegebene Breite setzen, schwarz auf weiß."""
    schrift = ImageFont.truetype(str(otf), groesse)
    rand = max(8, groesse // 3)
    innen = max(1, breite - 2 * rand)
    zeilen = [z for absatz in text.splitlines() for z in _umbrechen(absatz, schrift, innen)]
    oben, unten = schrift.getmetrics()
    zeilenhoehe = oben + unten
    bild = Image.new("RGB", (breite, 2 * rand + zeilenhoehe * max(1, len(zeilen))), "white")
    stift = ImageDraw.Draw(bild)
    for nummer, zeile in enumerate(zeilen):
        stift.text((rand, rand + nummer * zeilenhoehe), zeile, font=schrift, fill="black")
    return bild


if __name__ == "__main__":
    otf_erzeugen(Path(sys.argv[1]), Path(sys.argv[2]))

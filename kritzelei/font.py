"""Erstellung der FontForge-Datei (*.sfd) aus den SVG-Glyphen.

Benötigt das Python-Modul von FontForge (``python3-fontforge``).
"""

from __future__ import annotations

import math
import tempfile
from contextlib import contextmanager
from pathlib import Path

import fontforge
import psMat

from . import symbole
from .glyphen import HOEHENKLASSEN, PRIVATE_SCHWELLE, Glyphe

EM = 2048
SEITENABSTAND = 48  # side bearing links und rechts in Font-Einheiten
UEBERHANG = 15      # so weit reichen Zeichen ohne Unterlänge unter die Grundlinie

# (codepoint, name, Breite) – name None = FontForge-Standardname
LEERZEICHEN: list[tuple[int, str | None, int]] = [
    (0x0000, None, 390),       # NUL, Default Character
    (0x000D, "CR", 390),       # Carriage Return
    (0x0020, "space", 390),    # Space
    (0x00A0, "uni00A0", 390),  # No-Break Space
    (0x2000, "uni2000", 500),  # En Quad
    (0x2001, "uni2001", 900),  # Em Quad
    (0x2002, "uni2002", 500),  # En Space
    (0x2003, "uni2003", 900),  # Em Space
    (0x2007, "uni2007", 1000), # Figure Space
    (0x2008, "uni2008", 280),  # Punctuation Space
    (0x2009, "uni2009", 200),  # Thin Space
    (0x200A, "uni200A", 100),  # Hair Space
    (0x200B, "uni200B", 10),   # Zero Width Space
    (0x202F, "uni202F", 200),  # Narrow No-Break Space
]

STYLISTIC_SETS: dict[str, list[str]] = {
    "ss01": ["a", "d", "e", "i", "m", "n", "o", "r", "s", "t"],
    "ss02": ["a", "e"],
}

# Ligatur-Glyphe (Codepoint) → Folge der Ausgangszeichen
LIGATUREN: dict[int, tuple[str, ...]] = {
    0xFB00: ("f", "f"),
    0xFB01: ("f", "i"),
    0xFB02: ("f", "l"),
    0xFB03: ("f", "f", "i"),
}
DLIGATUREN: dict[int, tuple[str, ...]] = {
    0xF273A: ("c", "k"),
    0xF273B: ("Q", "u"),
    0xF273C: ("s", "s"),
    0xF273D: ("e", "i"),
    0xF273E: ("t", "t"),
}


def _seitenabstand(glyphe, abstand: int = SEITENABSTAND) -> None:
    glyphe.left_side_bearing = glyphe.right_side_bearing = abstand


@contextmanager
def _svg_datei(svg: str):
    """SVG-Text als temporäre Datei für ``importOutlines`` bereitstellen."""
    with tempfile.NamedTemporaryFile("w", suffix=".svg", encoding="utf-8") as datei:
        datei.write(svg)
        datei.flush()
        yield datei.name


# --- Grundgerüst ---------------------------------------------------------------

def _font_anlegen(name: str):
    font = fontforge.font()
    font.encoding = "UnicodeFull"
    font.version = "1.0"
    font.weight = "Regular"
    font.fontname = f"{name}-Regular"
    font.familyname = name
    font.fullname = f"{name} Regular"
    font.comment = "FONT_COMMENT"
    font.copyright = "FONT_LICENSE"
    font.em = EM
    # kubische Kurven (PostScript/OTF) statt quadratischer (TrueType)
    font.layers[0].is_quadratic = 0
    font.layers[1].is_quadratic = 0
    return font


def _lookups_anlegen(font) -> None:
    latin = [["latn", ["dflt"]]]
    for feature, typ, lookup in [
        ("ss01", "gsub_single", '"ss01" Style Set 1 lookup'),
        ("ss02", "gsub_single", '"ss02" Style Set 2 lookup'),
        ("liga", "gsub_ligature", "ligatures"),
        ("dlig", "gsub_ligature", "extra-ligatures"),
    ]:
        font.addLookup(lookup, typ, (), [[feature, latin]])
        font.addLookupSubtable(lookup, feature)


def _leerzeichen_anlegen(font) -> None:
    for codepoint, name, breite in LEERZEICHEN:
        glyphe = font.createChar(codepoint, name) if name else font.createChar(codepoint)
        glyphe.width = breite


def _glyphen_importieren(font, svg_dateien: list[Path], belegung: list[Glyphe]) -> None:
    for svg, (name, codepoint) in zip(svg_dateien, belegung):
        if codepoint < PRIVATE_SCHWELLE:
            glyphe = font.createChar(codepoint)
        else:
            glyphe = font.createChar(codepoint, name)
        glyphe.importOutlines(str(svg))
        glyphe.simplify()
        _seitenabstand(glyphe)
        glyphe.round()
        glyphe.addExtrema()


# --- eingebettete Zeichen -------------------------------------------------------

def _pfoten_anlegen(font):
    """Katzenpfote, „Samtpfote“-Ligatur und 🐾 (PAW PRINTS)."""
    pfote = font.createChar(0xF273F, "pfote")
    pfote.comment = "Gerne den Vorschlag von Christine Fraunhofer hier umgesetzt!"
    stift = pfote.glyphPen()
    for kontur in symbole.PFOTE_KONTUREN:
        stift.moveTo(*kontur[0])
        for c1x, c1y, c2x, c2y, x, y in kontur[1:]:
            stift.curveTo((c1x, c1y), (c2x, c2y), (x, y))
        stift.closePath()
    stift = None  # schließt den Stift, Konturen werden übernommen
    _seitenabstand(pfote, 120)

    # Pfotenspur: vier Pfoten, gedreht, verkleinert, versetzt
    spur = font.createChar(0xF2740, "pfote.lig")
    for matrix in [
        psMat.compose(psMat.rotate(math.radians(2)), psMat.translate(0, -50)),
        psMat.compose(psMat.scale(0.95), psMat.translate(-1500, -500)),
        psMat.compose(psMat.scale(0.9), psMat.translate(-3000, -100)),
        psMat.compose(psMat.scale(0.85), psMat.translate(-4500, -600)),
    ]:
        spur.addReference("pfote", matrix)
    spur.unlinkRef()
    _seitenabstand(spur, 180)
    spur.comment = 'Hier wurde die Pfote aus "pfote" übernommen, vervielfältigt und transformiert.'

    paws = font.createChar(0x1F43E, "u1F43E")
    paws.addReference("pfote", psMat.compose(psMat.rotate(math.radians(90)), psMat.translate(-800, 600)))
    paws.addReference("pfote", psMat.compose(psMat.rotate(math.radians(90)), psMat.translate(0, -150)))
    paws.unlinkRef()
    _seitenabstand(paws, 90)
    return spur


def _notdef_anlegen(font) -> None:
    with _svg_datei(symbole.SVG_NOTDEF) as pfad:
        glyphe = font.createChar(0x25A1, ".notdef")
        glyphe.importOutlines(pfad)
    _seitenabstand(glyphe, 90)


def _haende_anlegen(font):
    """Zeigehände (☚ ☛ 🖘 🖙 🖞 🖟 👈 👉 👆 👇).

    Gibt die Hilfsglyphe mit der weißen Hand zurück; sie wird am Ende
    geleert, nachdem die übrigen Hände aus ihr abgeleitet wurden.
    """
    with _svg_datei(symbole.SVG_HAND_WEISS) as weiss, _svg_datei(symbole.SVG_HAND_SCHWARZ) as schwarz:
        weisse_hand = font.createChar(0x1FFFE, "u1FFFE")
        weisse_hand.importOutlines(weiss)
        weisse_hand.round(1)
        _seitenabstand(weisse_hand, 0)

        schwarz_links = font.createChar(0x261A, "u261A")      # BLACK LEFT POINTING INDEX
        schwarz_links.importOutlines(schwarz)
        schwarz_links.round(1)
        _seitenabstand(schwarz_links)

        schwarz_rechts = font.createChar(0x261B, "u261B")     # BLACK RIGHT POINTING INDEX
        schwarz_rechts.importOutlines(schwarz)
        schwarz_rechts.round(1)
        schwarz_rechts.layers[1] = schwarz_rechts.layers[1].transform(psMat.scale(-1, 1))
        _seitenabstand(schwarz_rechts)

    # Achtung: layer.transform() verändert die Ebene selbst. `glyph.layers[1]`
    # liefert bei jedem Zugriff eine neue Kopie – deshalb jedes Mal neu holen.
    gespiegelt = psMat.scale(-1, 1)
    hoch = psMat.rotate(math.radians(-90))
    runter = psMat.rotate(math.radians(90))

    for codepoint, matrix, abstand in [
        (0x1F598, None, SEITENABSTAND),        # SIDEWAYS WHITE LEFT POINTING INDEX
        (0x1F599, gespiegelt, SEITENABSTAND),  # SIDEWAYS WHITE RIGHT POINTING INDEX
        (0x1F59E, hoch, None),                 # SIDEWAYS WHITE UP POINTING INDEX
        (0x1F59F, runter, None),               # SIDEWAYS WHITE DOWN POINTING INDEX
        (0x1F448, None, SEITENABSTAND),        # WHITE LEFT POINTING BACKHAND INDEX
        (0x1F449, gespiegelt, SEITENABSTAND),  # WHITE RIGHT POINTING BACKHAND INDEX
        (0x1F446, hoch, None),                 # WHITE UP POINTING BACKHAND INDEX
        (0x1F447, runter, None),               # WHITE DOWN POINTING BACKHAND INDEX
    ]:
        ebene = weisse_hand.layers[1]
        if matrix is not None:
            ebene = ebene.transform(matrix)
        glyphe = font.createChar(codepoint, f"u{codepoint:X}")
        glyphe.layers[1] = ebene
        if abstand is not None:
            _seitenabstand(glyphe, abstand)
    return weisse_hand


# --- OpenType-Features ------------------------------------------------------------

def _features_anlegen(font, pfotenspur) -> None:
    for feature, zeichen in STYLISTIC_SETS.items():
        for z in zeichen:
            font.createChar(ord(z)).addPosSub(feature, f"{z}.{feature}")
    for codepoint, folge in LIGATUREN.items():
        font.createChar(codepoint).addPosSub("liga", folge)
    pfotenspur.addPosSub("liga", tuple("Samtpfote"))
    for codepoint, folge in DLIGATUREN.items():
        font.createChar(codepoint).addPosSub("dlig", folge)


# --- abgeleitete Zeichen ----------------------------------------------------------

def _abgeleitete_zeichen_anlegen(font) -> None:
    gedreht = psMat.rotate(math.radians(180))
    hochgestellt = psMat.compose(psMat.scale(0.5), psMat.translate(0, 1000))

    # (codepoint, name, Quelle, Transformation, Kommentar, Seitenabstand)
    for codepoint, name, quelle, matrix, kommentar, abstand in [
        (0xA1, "exclamdown", "exclam", gedreht, "Umgedrehtes Ausrufezeichen.", None),
        (0x1F12F, "u1F12F", "copyright", gedreht, "Copyleft symbol.", None),
        (0xB9, "uni00B9", "one", hochgestellt, "superscript one, nicht referenziert.", SEITENABSTAND),
        (0xB2, "uni00B2", "two", hochgestellt, "superscript two, nicht referenziert.", SEITENABSTAND),
        (0xB3, "uni00B3", "three", hochgestellt, "superscript three, nicht referenziert.", SEITENABSTAND),
        (0xBF, "questiondown", "question", gedreht, "Umgedrehtes Fragezeichen.", None),
        (0x2E18, "uni2E18", "uni203D", gedreht, "Umgedrehtes Interrobang.", None),
    ]:
        glyphe = font.createChar(codepoint, name)
        glyphe.addReference(quelle, matrix)
        glyphe.unlinkRef()
        if abstand is not None:
            _seitenabstand(glyphe, abstand)
        glyphe.comment = kommentar

    # weiches Trennzeichen bleibt als Referenz auf den Bindestrich bestehen
    shy = font.createChar(0xAD, "uni00AD")
    shy.addReference("hyphen")
    _seitenabstand(shy)
    shy.comment = "SHY, referenziert."


# --- Größenanpassung --------------------------------------------------------------

def _groessen_anpassen(font) -> None:
    """Zeichen je nach Höhenklasse auf Grundlinie setzen und skalieren."""
    aufstrich = font.ascent
    unterlaenge = font.descent

    x_hoehe = round(aufstrich / 1.9, 1)
    versal = round(aufstrich / 1.03, 1)
    oberlaenge = round(aufstrich / 1.09, 1)
    unter = round(unterlaenge / 1.08, 1)

    # Hilfslinien für die Nacharbeit in FontForge
    for hoehe in (x_hoehe * 0.9, oberlaenge):
        linie = fontforge.contour()
        linie.moveTo(-font.em, hoehe)
        linie.lineTo(1.8 * font.em, hoehe)
        font.guide += linie

    # Zielhöhe je Klasse; ab_unterlaenge = Zeichen reicht unter die Grundlinie
    klassen = {
        "base_max": (versal, False),
        "base_x": (x_hoehe, False),
        "base_maxless": (oberlaenge, False),
        "min_x": (unter + x_hoehe, True),
        "min_maxless": (unter + oberlaenge, True),
    }

    # Jede Glyphe wird so skaliert, dass sie genau die Zielhöhe ihrer Klasse
    # hat, und dann mit der Unterkante auf eine feste Lage gesetzt.
    # Faktor und Versatz werden bewusst nicht gerundet: Eine Rundung des
    # Faktors auf 0,1 ließ gleich große Zeichen um bis zu ~9 % springen,
    # und ein Versatz vor dem Skalieren wurde mitskaliert.
    for klasse, glyphennamen in HOEHENKLASSEN.items():
        zielhoehe, ab_unterlaenge = klassen[klasse]
        unterkante = -unter if ab_unterlaenge else -UEBERHANG
        for glyphenname in glyphennamen:
            glyphe = font[glyphenname]
            _, y_min, _, y_max = glyphe.boundingBox()
            if y_max <= y_min:
                continue  # leere Glyphe, z. B. nicht ausgefülltes Kästchen
            faktor = zielhoehe / (y_max - y_min)
            matrix = psMat.compose(
                psMat.translate(0, -y_min),
                psMat.compose(psMat.scale(faktor), psMat.translate(0, unterkante)),
            )
            glyphe.transform(matrix)
            _seitenabstand(glyphe)


# --- Hauptfunktion ----------------------------------------------------------------

def font_erstellen(svg_dateien: list[Path], belegung: list[Glyphe], name: str, ziel: Path) -> Path:
    """Font aus SVG-Glyphen bauen und als ``<ziel>/<name>-Regular.sfd`` speichern."""
    if len(svg_dateien) != len(belegung):
        raise ValueError(
            f"{len(svg_dateien)} SVG-Dateien gefunden, die Vorlage hat aber {len(belegung)} Zeichen. "
            "Wurden alle Kästchen erkannt? (Kritzelei-Bilder-Fehlersuche.py hilft beim Prüfen.)"
        )

    font = _font_anlegen(name)
    try:
        _lookups_anlegen(font)
        _leerzeichen_anlegen(font)
        _glyphen_importieren(font, svg_dateien, belegung)
        pfotenspur = _pfoten_anlegen(font)
        _notdef_anlegen(font)
        weisse_hand = _haende_anlegen(font)
        _features_anlegen(font, pfotenspur)
        _abgeleitete_zeichen_anlegen(font)
        _groessen_anpassen(font)
        weisse_hand.clear()

        # Aufräumen über alle Glyphen
        font.selection.all()
        font.correctDirection()
        font.removeOverlap()
        font.simplify()
        font.round()
        font.addExtrema()

        sfd = ziel / f"{name}-Regular.sfd"
        font.save(str(sfd))
        return sfd
    finally:
        font.close()

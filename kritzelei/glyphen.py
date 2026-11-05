"""Glyphenbelegung der Kritzelei-Zeichenvorlage.

Reine Daten, ohne Abhängigkeit von OpenCV oder FontForge.

Jeder Eintrag ist ``(name, codepoint)``. Die Reihenfolge entspricht der
Reihenfolge der Kästchen auf den Bögen A, B und C (zeilenweise, von links
oben nach rechts unten). Codepoints oberhalb von :data:`PRIVATE_SCHWELLE`
sind keine echten Unicode-Zeichen, sondern Platzhalter für benannte
Zusatzglyphen (Ligaturen, Stylistic Sets); für sie wird der Name verwendet.
"""

from __future__ import annotations

KAESTCHEN_PRO_BLATT = 49
"""Anzahl der Kästchen je Bogen (7 × 7)."""

PRIVATE_SCHWELLE = 993000
"""Codepoints darüber stehen für benannte Glyphen ohne Unicode-Wert."""

Glyphe = tuple[str, int]

_GROSSBUCHSTABEN: list[Glyphe] = [(c, ord(c)) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜẞ"]
_KLEINBUCHSTABEN: list[Glyphe] = [(c, ord(c)) for c in "abcdefghijklmnopqrstuvwxyzäöüß"]
_ZIFFERN: list[Glyphe] = [(c, ord(c)) for c in "1234567890"]

_SATZZEICHEN_VOR_KLAMMERN: list[Glyphe] = [(c, ord(c)) for c in "!?§$%&/()"]
_SATZZEICHEN_NACH_KLAMMERN: list[Glyphe] = [
    (c, ord(c)) for c in "[]=<>|\\,;*.:-–#+~\"'@^_`·«»¼½¾‚‘„“…€ﬀﬁﬂﬃ"
]

_ZUSATZGLYPHEN: list[Glyphe] = [
    ("c_k.liga", 993082),
    ("Q_u.liga", 993083),
    ("s_s.liga", 993084),
    ("e_i.liga", 993085),
    ("t_t.liga", 993086),
    ("a.ss01", 993070),
    ("a.ss02", 993071),
    ("d.ss01", 993072),
    ("e.ss01", 993073),
    ("e.ss02", 993074),
    ("i.ss01", 993075),
    ("m.ss01", 993076),
    ("n.ss01", 993077),
    ("o.ss01", 993078),
    ("r.ss01", 993079),
    ("s.ss01", 993080),
    ("t.ss01", 993081),
]

_ERGAENZUNG_V2: list[Glyphe] = [
    ("copyright", 0xA9),
    ("registered", 0xAE),
    ("logicalnot", 0xAC),
    ("paragraph", 0xB6),
    ("divide", 0xF7),
    ("multiply", 0xD7),
    ("uni203d", 0x203D),
    ("arrowright", 0x2192),
    ("arrowleft", 0x2190),
    ("long", 0x17F),
]


def _belegung(klammern: str, ergaenzung: list[Glyphe]) -> list[Glyphe]:
    return [
        *_GROSSBUCHSTABEN,
        *_KLEINBUCHSTABEN,
        *_ZIFFERN,
        *_SATZZEICHEN_VOR_KLAMMERN,
        *[(c, ord(c)) for c in klammern],
        *_SATZZEICHEN_NACH_KLAMMERN,
        *_ZUSATZGLYPHEN,
        *ergaenzung,
    ]


# Version 1 hatte die geschweiften Klammern in der Reihenfolge `{ }`,
# Version 2 auf dem Bogen `} {` und zehn zusätzliche Zeichen.
BELEGUNG: dict[int, list[Glyphe]] = {
    1: _belegung("{}", []),
    2: _belegung("}{", _ERGAENZUNG_V2),
}


def belegung(version: int) -> list[Glyphe]:
    """Glyphenbelegung für eine Version der Zeichenvorlage."""
    try:
        return BELEGUNG[version]
    except KeyError:
        bekannt = ", ".join(str(v) for v in sorted(BELEGUNG))
        raise ValueError(f"Unbekannte Version der Zeichenvorlage: {version} (bekannt: {bekannt})") from None


def kaestchen_bezeichnung(index: int, belegung_: list[Glyphe] | None = None) -> str:
    """Lesbare Bezeichnung eines Kästchens, z. B. ``Kästchen 23 („&“)``.

    ``index`` zählt über alle Bögen ab 0; angezeigt wird die Nummer auf dem Bogen (1–49).
    """
    text = f"Kästchen {index % KAESTCHEN_PRO_BLATT + 1}"
    if belegung_ is not None and index < len(belegung_):
        text += f" („{belegung_[index][0]}“)"
    return text


# --- Höhenklassen für die automatische Größenanpassung ----------------------
#
# Jede Klasse beschreibt, von wo bis wo ein Zeichen reichen soll:
#   base = Grundlinie, x = x-Höhe, max = Versalhöhe,
#   maxless = Oberlänge (etwas unter Versalhöhe), min = Unterlänge.
#
# Bewusst ohne Klasse (Größe und Lage wie im Kästchen gezeichnet):
#   * Zeichen, die sehr unterschiedlich geschrieben werden: G, J, ẞ, ſ
#     (auf der Grundlinie endend oder mit Schnörkel/Unterlänge)
#   * Satz- und Sonderzeichen wie , . - « » „ “ © ® …
# Abgeleitete Zeichen (¡ ¿ ⸘ 🄯 ¹ ² ³) bekommen ebenfalls keine Klasse: Sie
# entstehen erst nach der Größenanpassung aus ihren Ausgangszeichen.

HOEHENKLASSEN: dict[str, list[str]] = {
    "base_max": [
        "exclam", "numbersign", "dollar", "percent", "ampersand", "parenleft",
        "parenright", "slash", "question", "A", "B", "C", "D", "E", "F", "H",
        "I", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W",
        "X", "Y", "Z", "bracketleft", "backslash", "bracketright", "braceleft",
        "bar", "braceright", "section", "Adieresis", "Odieresis", "Udieresis",
        "Euro", "Q_u.liga", "uni203D", "paragraph",
    ],
    "base_x": [
        "at", "a", "c", "e", "i", "m", "n", "o", "r", "s", "u", "v", "w", "x",
        "z", "adieresis", "odieresis", "udieresis", "a.ss01", "a.ss02",
        "e.ss01", "e.ss02", "i.ss01", "m.ss01", "n.ss01", "o.ss01", "r.ss01",
        "s.ss01", "s_s.liga", "e_i.liga",
    ],
    "base_maxless": [
        "b", "d", "h", "k", "l", "t", "onequarter", "onehalf",
        "threequarters", "d.ss01", "t.ss01", "c_k.liga", "zero",
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "u1F59E", "u1F59F", "u1F446", "u1F447",
    ],
    "min_x": [
        "g", "j", "p", "q", "y",
    ],
    "min_maxless": [
        "f", "germandbls", "uniFB00", "uniFB01", "uniFB02", "uniFB03", "t_t.liga",
    ],
}


# --- Ziellinien ---------------------------------------------------------------
#
# Font-Maße bei em 2048 (FontForge verteilt ascent/descent standardmäßig 80/20).
# Hier statt in font.py, damit auch der Rasterschritt (Strichbreite) ohne
# FontForge weiß, wie groß ein Zeichen im Font später wird.

EM = 2048
ASCENT = 1638
DESCENT = 410
UEBERHANG = 15
"""So weit reichen Zeichen ohne Unterlänge unter die Grundlinie."""


def metriken(ascent: float = ASCENT, descent: float = DESCENT) -> dict[str, float]:
    """Ziellinien in Font-Einheiten (aus ascent/descent abgeleitet)."""
    return {
        "x_hoehe": round(ascent / 1.9, 1),
        "versal": round(ascent / 1.03, 1),
        "oberlaenge": round(ascent / 1.09, 1),
        "unter": round(descent / 1.08, 1),
    }


def klassenhoehen(m: dict[str, float]) -> dict[str, tuple[float, bool]]:
    """Zielhöhe je Höhenklasse; der zweite Wert: Zeichen reicht unter die Grundlinie."""
    return {
        "base_max": (m["versal"], False),
        "base_x": (m["x_hoehe"], False),
        "base_maxless": (m["oberlaenge"], False),
        "min_x": (m["unter"] + m["x_hoehe"], True),
        "min_maxless": (m["unter"] + m["oberlaenge"], True),
    }

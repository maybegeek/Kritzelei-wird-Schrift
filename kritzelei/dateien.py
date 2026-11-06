"""Welche Dateien eines Ordners als Bögen gelten – für alle Skripte und die Oberfläche gleich."""

from __future__ import annotations

from pathlib import Path

BILD_ENDUNGEN = (".jpg", ".jpeg", ".png")
BILD_ARTEN = "jpg, jpeg, png"


def bilder_finden(ordner: Path) -> list[Path]:
    """Bilddateien nach Namen sortiert, die Reihenfolge ergibt die Bögen A, B, C.

    Die Schreibweise der Endung zählt nicht (``A.JPG``).
    """
    if not ordner.is_dir():
        return []
    return sorted(d for d in ordner.iterdir() if d.is_file() and d.suffix.lower() in BILD_ENDUNGEN)

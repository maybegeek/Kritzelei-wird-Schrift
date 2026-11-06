"""Export: andere Schriftformate erzeugen und alles Wichtige als ZIP packen.

Die Formate landen in ``<ordner>/export/`` nach Zweck sortiert. Das ZIP enthält
dazu die sfd-Dateien und einen Hinweistext (``template/LIESMICH.md``), aber keine
Zwischendateien und keine Sicherungen; es ist zum Weitergeben gedacht.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
LIESMICH = WURZEL / "template" / "LIESMICH.md"

# Format → Unterordner nach Zweck
FORMATE = {"otf": "installieren", "ttf": "installieren", "woff2": "web", "ufo": "bearbeiten"}
UNTERORDNER = ("bearbeiten", "installieren", "web")


class ExportFehler(ValueError):
    """Die Eingabe passt nicht, die Meldung ist für die Nutzenden bestimmt."""


def sfd_finden(ordner: Path) -> list[Path]:
    dateien = sorted(ordner.glob("*.sfd")) if ordner.is_dir() else []
    if not dateien:
        raise ExportFehler(f"Keine *.sfd-Dateien in {ordner}.")
    return dateien


def _alte_entfernen(ordner: Path) -> None:
    """Nur was der Export selbst anlegt: Sonst käme ein abgewähltes Format noch ins ZIP."""
    for format_, unterordner in FORMATE.items():
        for alt in (ordner / "export" / unterordner).glob(f"*.{format_}"):
            shutil.rmtree(alt) if alt.is_dir() else alt.unlink()


def exportieren(ordner: Path, formate: list[str]) -> list[Path]:
    """Alle sfd-Dateien des Ordners in die gewählten Formate umwandeln."""
    # erst hier importieren: fontforge wird nur für diesen Schritt gebraucht
    import fontforge

    dateien = sfd_finden(ordner)
    _alte_entfernen(ordner)
    ergebnis = []
    for sfd in dateien:
        font = fontforge.open(str(sfd))
        try:
            for format_ in formate:
                ziel = ordner / "export" / FORMATE[format_] / f"{sfd.stem}.{format_}"
                ziel.parent.mkdir(parents=True, exist_ok=True)
                font.generate(str(ziel))
                ergebnis.append(ziel)
        finally:
            font.close()
    return ergebnis


def _inhalt_beschreiben(formate: list[str]) -> str:
    zeilen = ["- `bearbeiten/`: zum Weiterarbeiten, `*.sfd` für FontForge"
              + (", `*.ufo` für andere Programme wie Glyphs, RoboFont, FontLab oder Fontra" if "ufo" in formate else "")]
    installieren = [f"`*.{f}`" for f in ("otf", "ttf") if f in formate]
    if installieren:
        zeilen.append(f"- `installieren/`: zum Installieren und Benutzen, {' und '.join(installieren)}")
    if "woff2" in formate:
        zeilen.append("- `web/`: zum Einbinden in Webseiten, `*.woff2`")
    return "\n".join(zeilen)


def _weiter_beschreiben(familie: str, dateien: list[Path]) -> str:
    regular = next((d.name for d in dateien if d.stem.endswith("-Regular")), f"{familie}-Regular.sfd")
    schritte = [f"1. Öffnen Sie `bearbeiten/{regular}` in FontForge und überarbeiten Sie die Zeichen."]
    if len(dateien) > 1:
        schritte.append("2. Italic, Bold und Bold-Italic sind automatisch abgeleitet. Sie sind ein Ausgangspunkt: "
                        "Prüfen Sie enge Formen wie `@` und `©` und das Kerning. "
                        "Korrekturen an Regular erscheinen nicht von selbst in den anderen Schnitten.")
    else:
        schritte.append("2. Wenn Regular passt, lassen sich daraus Italic, Bold und Bold-Italic ableiten "
                        "(Schritt „Schriftschnitte“ in *Kritzelei wird Schrift*). "
                        "Deshalb lohnt es sich, zuerst Regular sorgfältig zu überarbeiten.")
    schritte.append("3. Die fertige Schrift erzeugen Sie in FontForge im Menü „Datei“ "
                    "(englische Oberfläche: *File > Generate Fonts*).")
    return "\n".join(schritte)


def liesmich_text(familie: str, dateien: list[Path], formate: list[str]) -> str:
    return LIESMICH.read_text(encoding="utf-8").format(
        familie=familie, inhalt=_inhalt_beschreiben(formate), weiter=_weiter_beschreiben(familie, dateien))


def zip_packen(ordner: Path, ziel: Path, formate: list[str]) -> Path:
    """Das Paket zum Weitergeben; die Formate müssen vorher exportiert sein."""
    dateien = sfd_finden(ordner)
    familie = dateien[0].stem.rpartition("-")[0] or dateien[0].stem
    ziel.parent.mkdir(parents=True, exist_ok=True)
    zwischen = ziel.with_name(ziel.name + ".tmp")  # ein Abbruch soll kein halbes ZIP hinterlassen
    with zipfile.ZipFile(zwischen, "w", zipfile.ZIP_DEFLATED) as paket:
        paket.writestr(f"{familie}/LIESMICH.md", liesmich_text(familie, dateien, formate))
        for sfd in dateien:
            paket.write(sfd, f"{familie}/bearbeiten/{sfd.name}")
        for format_ in formate:
            unterordner = FORMATE[format_]
            for pfad in sorted((ordner / "export" / unterordner).glob(f"*.{format_}")):
                teile = sorted(pfad.rglob("*")) if pfad.is_dir() else [pfad]
                for teil in teile:
                    if teil.is_file():
                        paket.write(teil, f"{familie}/{unterordner}/{teil.relative_to(pfad.parent)}")
    zwischen.replace(ziel)
    return ziel

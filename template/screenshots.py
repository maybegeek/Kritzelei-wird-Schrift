#!/usr/bin/env python3
"""Bildschirmfotos der Oberfläche für die README neu aufnehmen (braucht ImageMagick).

    /usr/bin/python3 template/screenshots.py

Öffnet kurz das Fenster. Es schreibt nur nach template/oberflaeche/doku/.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import customtkinter as ctk  # noqa: E402

from kritzelei.oberflaeche import Oberflaeche  # noqa: E402

ZIEL = ROOT / "template" / "oberflaeche" / "doku"


def main() -> None:
    fenster = ctk.CTk(className="Kritzelei")
    fenster.withdraw()
    app = Oberflaeche(fenster)
    fenster.deiconify()

    def warten(sekunden: float) -> None:
        ende = time.time() + sekunden
        while time.time() < ende or app.beschaeftigt:
            fenster.update()
            time.sleep(0.02)

    def foto(name: str) -> None:
        warten(1)
        subprocess.run(["import", "-window", hex(fenster.winfo_id()), str(ZIEL / f"{name}.png")], check=True)

    warten(2)
    app.ziel.set("Output/Kritzelei")  # der Beispiel-Font; hier wird nur gelesen
    foto("start")
    app.zeige("Erkennung prüfen")
    warten(0.5)
    app.erkennung_pruefen()
    foto("erkennung")
    app.zeige("Ergebnis")
    foto("ergebnis")
    app.zeige("Export")
    foto("export")
    app.beenden()


if __name__ == "__main__":
    main()

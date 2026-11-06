#!/usr/bin/env python3
"""Bedienoberfläche für alle Schritte von den Fotos bis zur Schrift.

    python3 Kritzelei-Oberflaeche.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from kritzelei.oberflaeche import main  # noqa: E402
except ImportError as fehler:
    sys.exit("Die Oberfläche braucht Tk, Pillow mit Tk-Anbindung und CustomTkinter, z. B.:\n"
             "  apt install python3-tk python3-pil.imagetk\n"
             "  pip3 install --user --break-system-packages customtkinter\n"
             f"(Fehlermeldung: {fehler})")

if __name__ == "__main__":
    sys.exit(main())

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
    sys.exit(f"Die Oberfläche braucht Tk und Pillow mit Tk-Anbindung "
             f"(z. B. `apt install python3-tk python3-pil.imagetk`): {fehler}")

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Compatibilidade: delega o atlas Material ao conversor Resvg local.

Resvg é usado apenas no host porque renderizar paths SVG no EFI aumentaria
demais o runtime. O resultado continua sendo uma tabela alpha C estática.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONVERTER = ROOT / "tools" / "scripts" / "generate_material_icons.cjs"


if __name__ == "__main__":
    raise SystemExit(subprocess.call(["node", str(CONVERTER), *sys.argv[1:]], cwd=ROOT))

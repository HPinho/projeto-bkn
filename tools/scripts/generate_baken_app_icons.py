#!/usr/bin/env python3
"""Compatibilidade PowerShell: delega o atlas de apps ao Resvg local."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONVERTER = ROOT / "tools" / "scripts" / "generate_baken_app_icons.cjs"


if __name__ == "__main__":
    raise SystemExit(subprocess.call(["node", str(CONVERTER), *sys.argv[1:]], cwd=ROOT))

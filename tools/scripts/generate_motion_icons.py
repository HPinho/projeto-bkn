#!/usr/bin/env python3
"""Extrai somente os SVGs usados e os compila em atlas para o kernel EFI."""
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets" / "icons"
STAGING = ROOT / "build" / "tooling" / "baken-motion-src"
CONVERTER = ROOT / "tools" / "scripts" / "generate_motion_icons.cjs"
SELECTION = {
    "Play pause circle.zip": ("play-circle.svg", "pause-circle.svg"),
    "Skip back.zip": ("skip-back.svg",),
    "Refresh.zip": ("refresh.svg",),
    "Settings.zip": ("settings.svg",),
}


def extract_selected() -> None:
    STAGING.mkdir(parents=True, exist_ok=True)
    for archive_name, members in SELECTION.items():
        archive_path = ASSETS / archive_name
        if not archive_path.is_file():
            raise FileNotFoundError(f"pacote de movimento ausente: {archive_path}")
        with zipfile.ZipFile(archive_path) as archive:
            names = {name.lstrip("/"): name for name in archive.namelist()}
            for member in members:
                if member not in names:
                    raise ValueError(f"{member} ausente em {archive_name}")
                (STAGING / member).write_bytes(archive.read(names[member]))


if __name__ == "__main__":
    extract_selected()
    raise SystemExit(subprocess.call(["node", str(CONVERTER), *sys.argv[1:]], cwd=ROOT))

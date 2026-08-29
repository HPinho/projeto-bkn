#!/usr/bin/env python3
"""Gera tabelas sRGB <-> linear para o compositor bare-metal."""
from math import pow
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "kernel" / "include" / "baken_color_lut.h"


def srgb_to_linear(value: int) -> int:
    channel = value / 255.0
    linear = channel / 12.92 if channel <= 0.04045 else pow((channel + 0.055) / 1.055, 2.4)
    return round(linear * 65535.0)


def linear_to_srgb(value: int) -> int:
    linear = value / 4096.0
    channel = linear * 12.92 if linear <= 0.0031308 else 1.055 * pow(linear, 1.0 / 2.4) - 0.055
    return max(0, min(255, round(channel * 255.0)))


def values(items):
    return ",".join(map(str, items))


def main() -> None:
    forward = [srgb_to_linear(value) for value in range(256)]
    inverse = [linear_to_srgb(value) for value in range(4097)]
    content = "\n".join((
        "#pragma once", "#include <stdint.h>",
        "/* Generated sRGB IEC 61966-2-1 transfer tables. Do not edit. */",
        f"static const uint16_t bkn_srgb_to_linear_16[256] = {{{values(forward)}}};",
        f"static const uint8_t bkn_linear_16_to_srgb[4097] = {{{values(inverse)}}};", "",
    ))
    OUTPUT.write_text(content, encoding="ascii")
    print(f"[OK] LUT sRGB linear: {OUTPUT}")


if __name__ == "__main__":
    main()

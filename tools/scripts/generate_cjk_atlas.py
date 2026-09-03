#!/usr/bin/env python3
"""Gera atlas de alta definicao com caracteres nativos CJK (中文, 日本語) e Grego (Ελληνικά)
para o rasterizador Sotlas do Baken OS."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_HEADER = ROOT / "kernel" / "include" / "baken_cjk_atlas.h"

# Fontes nativas do Windows
FONTS_TRY = [
    r"C:\Windows\Fonts\msyh.ttc",     # Microsoft YaHei
    r"C:\Windows\Fonts\msgothic.ttc", # MS Gothic
    r"C:\Windows\Fonts\simsun.ttc",   # SimSun
]

def get_font(size, preferred=None):
    if preferred and Path(preferred).is_file():
        try:
            return ImageFont.truetype(preferred, size)
        except Exception:
            pass
    for f in FONTS_TRY:
        if Path(f).is_file():
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()

ITEMS = [
    # (id, texto, fonte_preferida)
    (0, "中文", r"C:\Windows\Fonts\msyh.ttc"),
    (1, "日本語", r"C:\Windows\Fonts\msgothic.ttc"),
    (2, "Ελληνικά", r"C:\Windows\Fonts\msyh.ttc"),
]

def render_item(text, font_path, size=16):
    font = get_font(size, font_path)
    # Mede dimensões exatas
    bbox = font.getbbox(text)
    w = max(1, bbox[2] - bbox[0] + 4)
    h = max(1, bbox[3] - bbox[1] + 4)
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    draw.text((-bbox[0] + 2, -bbox[1] + 2), text, fill=255, font=font)
    return w, h, list(img.tobytes())

def main():
    lines = [
        "/* Baken OS - Atlas de Ideogramas Nativos CJK e Grego em Alta Definicao */",
        "/* Gerado automaticamente para Sotlas. */",
        "#pragma once",
        "#include <stdint.h>",
        "",
        "typedef struct {",
        "    uint32_t width;",
        "    uint32_t height;",
        "    const uint8_t *alpha;",
        "} BakenCJKGlyphItem;",
        ""
    ]

    for idx, text, fpath in ITEMS:
        w, h, alpha = render_item(text, fpath, size=16)
        name = f"g_cjk_item_{idx}"
        alpha_str = ",".join(str(b) for b in alpha)
        lines.append(f"static const uint8_t {name}_alpha[{len(alpha)}] = {{{alpha_str}}};")
        lines.append(f"static const BakenCJKGlyphItem {name} = {{{w}, {h}, {name}_alpha}};")
        lines.append("")

    lines.append("static const BakenCJKGlyphItem g_baken_cjk_items[] = {")
    for idx, _, _ in ITEMS:
        lines.append(f"    g_cjk_item_{idx},")
    lines.append("};")
    lines.append("#define BAKEN_CJK_COUNT 3")
    lines.append("")

    OUTPUT_HEADER.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HEADER.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Atlas CJK gerado: {OUTPUT_HEADER}")

if __name__ == "__main__":
    main()

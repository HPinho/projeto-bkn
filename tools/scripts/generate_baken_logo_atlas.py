#!/usr/bin/env python3
"""Gera o atlas do logotipo e emblema oficial do Baken OS em alta definicao para o microkernel."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ICON_SRC = ROOT / "Logo Icone.png"
OUTPUT = ROOT / "kernel" / "include" / "baken_logo_atlas.h"

SIZES = (128, 64, 32, 24)

def generate_logo_atlas():
    if not ICON_SRC.is_file():
        raise SystemExit(f"Logo oficial nao encontrado: {ICON_SRC}")

    img = Image.open(ICON_SRC).convert("RGBA")
    
    # Auto-crop bounding box to center perfectly
    bbox = img.getbbox()
    if bbox:
        # Make it square
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        max_dim = max(bw, bh)
        cx = (bbox[0] + bbox[2]) // 2
        cy = (bbox[1] + bbox[3]) // 2
        sq_box = (cx - max_dim // 2, cy - max_dim // 2, cx + max_dim // 2, cy + max_dim // 2)
        sq_img = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
        crop_area = img.crop((max(0, sq_box[0]), max(0, sq_box[1]), min(img.width, sq_box[2]), min(img.height, sq_box[3])))
        paste_x = max(0, -sq_box[0])
        paste_y = max(0, -sq_box[1])
        sq_img.paste(crop_area, (paste_x, paste_y))
        img = sq_img

    lines = [
        "/* Generated Baken OS Official Swirl Emblem Atlas. Do not edit. */",
        "#pragma once",
        "#include <stdint.h>",
        "",
        "typedef struct {",
        "    uint32_t size;",
        "    const uint32_t *pixels;",
        "} BakenLogoAtlas;",
        ""
    ]

    for size in SIZES:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        rgba_data = resized.getdata()
        
        # Convert to 32-bit 0xAARRGGBB
        argb_pixels = []
        for r, g, b, a in rgba_data:
            val = (a << 24) | (r << 16) | (g << 8) | b
            argb_pixels.append(f"0x{val:08X}")
        
        lines.append(f"static const uint32_t baken_logo_swirl_{size}_pixels[{size * size}] = {{")
        # Format 8 per line
        for i in range(0, len(argb_pixels), 8):
            lines.append("    " + ", ".join(argb_pixels[i:i+8]) + ",")
        lines.append("};")
        lines.append("")

    lines.append("static const BakenLogoAtlas g_baken_logo_atlases[] = {")
    for size in SIZES:
        lines.append(f"    {{ {size}, baken_logo_swirl_{size}_pixels }},")
    lines.append("};")
    lines.append(f"#define BAKEN_LOGO_ATLAS_COUNT {len(SIZES)}")
    lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Atlas do logotipo oficial Baken OS gerado em: {OUTPUT}")

if __name__ == "__main__":
    generate_logo_atlas()

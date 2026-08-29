#!/usr/bin/env python3
"""Gera atlas Google Sans Flex em tamanhos nativos para o rasterizador EFI."""
from pathlib import Path
import zipfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT_ZIP = ROOT / "assets" / "fonts" / "Google_Sans_Flex.zip"
FONT_MEMBER = "GoogleSansFlex-VariableFont_GRAD,ROND,opsz,slnt,wdth,wght.ttf"
FONT = ROOT / "build" / "tooling" / "fonts" / "GoogleSansFlex.ttf"
OUTPUT = ROOT / "kernel" / "include" / "font_google_sans_flex_atlas.h"
# Atlases acima de 32 px são necessários para escala 200% em painéis 2K.
# O rasterizador sempre reduz o atlas seguinte; nunca amplia uma máscara.
SIZES = ((12, 11, 15, -2), (14, 13, 18, -3), (16, 15, 20, -3),
         (20, 18, 25, -4), (24, 22, 30, -5), (32, 29, 40, -7),
         (40, 37, 50, -9), (48, 44, 60, -10), (64, 59, 80, -14))
PT_BR = {129:'á',128:'à',130:'â',131:'ã',137:'é',138:'ê',141:'í',147:'ó',148:'ô',149:'õ',154:'ú',156:'ü',135:'ç',193:'Á',192:'À',194:'Â',195:'Ã',201:'É',202:'Ê',205:'Í',211:'Ó',212:'Ô',213:'Õ',218:'Ú',220:'Ü',199:'Ç',176:'°',183:'·',133:'…',169:'©'}

def render(size, width, height, baseline):
    font = ImageFont.truetype(FONT, size)
    advances, pixels = [0] * 256, [0] * (256 * width * height)
    characters = {i: chr(i) for i in range(32, 127)} | PT_BR
    for code, char in characters.items():
        image = Image.new('L', (width, height), 0)
        ImageDraw.Draw(image).text((0, baseline), char, fill=255, font=font)
        start = code * width * height
        pixels[start:start + width * height] = list(image.getdata())
        advance = int(round(font.getlength(char)))
        advances[code] = max(2, min(width, 4 if char == ' ' else advance))
    return advances, pixels


def stage_font() -> None:
    """Extrai um único TTF temporário, nunca o pacote inteiro para assets."""
    if not FONT_ZIP.is_file():
        raise SystemExit(f"Fonte Google Sans Flex nao encontrada: {FONT_ZIP}")
    FONT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(FONT_ZIP) as archive:
        if FONT_MEMBER not in archive.namelist():
            raise SystemExit(f"Fonte variavel ausente no ZIP: {FONT_MEMBER}")
        FONT.write_bytes(archive.read(FONT_MEMBER))

def main():
    stage_font()
    lines = ['#pragma once', '#include <stdint.h>', '',
        '/* Generated from Google Sans Flex (SIL Open Font License 1.1). Do not edit. */',
        'typedef struct { uint8_t px, width, height; const uint8_t *advances, *alpha; } CqFontAtlas;', '']
    for size, width, height, baseline in SIZES:
        advances, pixels = render(size, width, height, baseline)
        lines += [f'static const uint8_t google_sans_flex_{size}_advances[256] = {{' + ','.join(map(str, advances)) + '};',
                  f'static const uint8_t google_sans_flex_{size}_alpha[{len(pixels)}] = {{' + ','.join(map(str, pixels)) + '};', '']
    lines += ['static const CqFontAtlas cq_font_atlases[] = {']
    lines += [f'    {{{size}, {width}, {height}, google_sans_flex_{size}_advances, google_sans_flex_{size}_alpha}},' for size, width, height, _ in SIZES]
    lines += ['};', f'#define CQ_FONT_ATLAS_COUNT {len(SIZES)}', '']
    OUTPUT.parent.mkdir(parents=True, exist_ok=True); OUTPUT.write_text('\n'.join(lines), encoding='ascii')
    print(f'[OK] atlas Google Sans Flex multi-resolucao: {OUTPUT} ({len(SIZES)} tamanhos)')

if __name__ == '__main__': main()

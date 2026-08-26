/*
 * Baken OS - Fonte Bitmap 8x16 Integrada de Alta Resolução
 * Contém a matriz de pixels dos caracteres ASCII legíveis (0x20 a 0x7E)
 */

#ifndef BKN_FONT_H
#define BKN_FONT_H

#include <stdint.h>

// Fonte clássica 8x16 VGA / BIOS simplificada de alta nitidez
extern const uint8_t bkn_font8x16[128][16];

// Retorna a linha 'row' (0..15) do glifo 'char_code' — chamável por BKN via extern "C"
uint8_t bkn_font_get_row(uint8_t char_code, uint8_t row);

#endif // BKN_FONT_H

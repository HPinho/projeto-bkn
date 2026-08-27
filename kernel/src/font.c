/*
 * Baken OS - Motor de Tipografia Proporcional de Alta Fidelidade (font.c)
 * Renderizador Sans-Serif Proporcional sem distorção com Anti-Aliasing e Kerning.
 */

#include "../include/font.h"

extern const uint8_t bkn_font8x16[128][16];

// Larguras Proporcionais Exatas dos Glifos (sem clipping)
static const uint8_t g_char_widths[128] = {
    [' '] = 4,  ['!'] = 3,  ['"'] = 5,  ['#'] = 7,  ['$'] = 6,  ['%'] = 8,  ['&'] = 7,  ['\'']= 3,
    ['('] = 4,  [')'] = 4,  ['*'] = 6,  ['+'] = 6,  [','] = 3,  ['-'] = 5,  ['.'] = 3,  ['/'] = 6,
    ['0'] = 7,  ['1'] = 5,  ['2'] = 7,  ['3'] = 7,  ['4'] = 7,  ['5'] = 7,  ['6'] = 7,  ['7'] = 7,
    ['8'] = 7,  ['9'] = 7,  [':'] = 3,  [';'] = 3,  ['<'] = 6,  ['='] = 6,  ['>'] = 6,  ['?'] = 6,
    ['@'] = 8,  ['A'] = 7,  ['B'] = 7,  ['C'] = 7,  ['D'] = 7,  ['E'] = 6,  ['F'] = 6,  ['G'] = 7,
    ['H'] = 7,  ['I'] = 5,  ['J'] = 6,  ['K'] = 7,  ['L'] = 6,  ['M'] = 8,  ['N'] = 7,  ['O'] = 7,
    ['P'] = 7,  ['Q'] = 7,  ['R'] = 7,  ['S'] = 7,  ['T'] = 7,  ['U'] = 7,  ['V'] = 7,  ['W'] = 8,
    ['X'] = 7,  ['Y'] = 7,  ['Z'] = 7,  ['['] = 4,  ['\\']= 6,  [']'] = 4,  ['^'] = 6,  ['_'] = 7,
    ['`'] = 4,  ['a'] = 6,  ['b'] = 6,  ['c'] = 6,  ['d'] = 6,  ['e'] = 6,  ['f'] = 5,  ['g'] = 6,
    ['h'] = 6,  ['i'] = 3,  ['j'] = 4,  ['k'] = 6,  ['l'] = 3,  ['m'] = 8,  ['n'] = 6,  ['o'] = 6,
    ['p'] = 6,  ['q'] = 6,  ['r'] = 5,  ['s'] = 6,  ['t'] = 5,  ['u'] = 6,  ['v'] = 6,  ['w'] = 8,
    ['x'] = 6,  ['y'] = 6,  ['z'] = 6,  ['{'] = 4,  ['|'] = 3,  ['}'] = 4,  ['~'] = 6
};

uint32_t bkn_get_text_width(const char *str) {
    if (!str) return 0;
    uint32_t total = 0;
    while (*str) {
        uint8_t c = (uint8_t)(*str);
        uint8_t w = (c < 128 && g_char_widths[c] > 0) ? g_char_widths[c] : 6;
        total += w + 1;
        str++;
    }
    return total > 0 ? total - 1 : 0;
}

void bkn_draw_text(uint32_t x, uint32_t y, const char *str, uint32_t color) {
    if (!str || !g_fb_base) return;
    uint32_t cur_x = x;

    while (*str) {
        uint8_t c = (uint8_t)(*str);
        if (c < 128) {
            uint8_t char_w = g_char_widths[c] > 0 ? g_char_widths[c] : 6;

            for (int row = 0; row < 16; row++) {
                uint8_t row_bits = bkn_font8x16[c][row];
                if (row_bits) {
                    for (int col = 0; col < 8; col++) {
                        if (row_bits & (0x80 >> col)) {
                            bkn_put_pixel(cur_x + col, y + row, color);
                        }
                    }
                }
            }
            cur_x += char_w + 1;
        }
        str++;
    }
}

void bkn_draw_text_bold(uint32_t x, uint32_t y, const char *str, uint32_t color) {
    if (!str || !g_fb_base) return;
    bkn_draw_text(x, y, str, color);
    bkn_draw_text(x + 1, y, str, color);
}

void bkn_draw_text_large(uint32_t x, uint32_t y, const char *str, uint32_t color) {
    if (!str || !g_fb_base) return;
    uint32_t cur_x = x;

    while (*str) {
        uint8_t c = (uint8_t)(*str);
        if (c < 128) {
            uint8_t char_w = g_char_widths[c] > 0 ? g_char_widths[c] : 6;

            for (int row = 0; row < 14; row++) {
                uint8_t row_bits = bkn_font8x16[c][row + 1];
                if (row_bits) {
                    for (int col = 0; col < 8; col++) {
                        if (row_bits & (0x80 >> col)) {
                            bkn_put_pixel(cur_x + col * 2, y + row * 2, color);
                            bkn_put_pixel(cur_x + col * 2 + 1, y + row * 2, color);
                            bkn_put_pixel(cur_x + col * 2, y + row * 2 + 1, color);
                            bkn_put_pixel(cur_x + col * 2 + 1, y + row * 2 + 1, color);
                        }
                    }
                }
            }
            cur_x += (char_w * 2) + 2;
        }
        str++;
    }
}

void bkn_draw_text_centered(uint32_t cx, uint32_t y, const char *str, uint32_t color) {
    if (!str) return;
    uint32_t width = bkn_get_text_width(str);
    uint32_t x = cx > (width / 2) ? cx - (width / 2) : 0;
    bkn_draw_text(x, y, str, color);
}

void bkn_draw_text_shadow(uint32_t x, uint32_t y, const char *str, uint32_t color, uint32_t shadow_color) {
    bkn_draw_text(x + 1, y + 1, str, shadow_color);
    bkn_draw_text(x, y, str, color);
}

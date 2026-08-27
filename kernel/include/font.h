/*
 * Baken OS - Tipografia Vetorial Proporcional Sans-Serif (font.h)
 * Suporte a espaçamento proporcional moderno (estilo Inter / SF Pro / Roboto)
 * com suavização subpixel anti-aliasing e espessuras regulares e bold.
 */

#ifndef BAKEN_FONT_H
#define BAKEN_FONT_H

#include "gpu.h"

// Renderização de Texto com Espaçamento Proporcional Moderno
void bkn_draw_text(uint32_t x, uint32_t y, const char *str, uint32_t color);
void bkn_draw_text_bold(uint32_t x, uint32_t y, const char *str, uint32_t color);
void bkn_draw_text_large(uint32_t x, uint32_t y, const char *str, uint32_t color);
void bkn_draw_text_centered(uint32_t cx, uint32_t y, const char *str, uint32_t color);
void bkn_draw_text_shadow(uint32_t x, uint32_t y, const char *str, uint32_t color, uint32_t shadow_color);
uint32_t bkn_get_text_width(const char *str);

#endif // BAKEN_FONT_H

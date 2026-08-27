/*
 * Baken OS - Ícones Vetoriais Nativos (icons.h)
 */

#ifndef BAKEN_ICONS_H
#define BAKEN_ICONS_H

#include "gpu.h"
#include "sdf.h"
#include "font.h"

void bkn_draw_vector_folder(uint32_t x, uint32_t y, const char *label, uint32_t color);
void bkn_draw_system_core_card(uint32_t x, uint32_t y);
void bkn_draw_vortex_icon(uint32_t cx, uint32_t cy, float radius);
void bkn_draw_weather_sun(uint32_t cx, uint32_t cy);
void bkn_draw_dock_app_glyph(uint32_t cx, uint32_t cy, int app_id);

#endif // BAKEN_ICONS_H

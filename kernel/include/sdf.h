/*
 * Baken OS - Motor SDF e Subpixel Anti-Aliasing (sdf.h)
 */

#ifndef BAKEN_SDF_H
#define BAKEN_SDF_H

#include "gpu.h"

float sdf_box(float px, float py, float rx, float ry, float rw, float rh, float radius);
float sdf_smoothstep(float dist, float softness);

void bkn_draw_sdf_glass_card(
    uint32_t x, uint32_t y, uint32_t w, uint32_t h,
    float radius,
    uint32_t bg_color, uint8_t bg_alpha,
    uint32_t border_color, float border_width
);

void bkn_draw_sdf_circle(uint32_t cx, uint32_t cy, float radius, uint32_t color, uint8_t alpha);

#endif // BAKEN_SDF_H

/*
 * Baken OS - Motor SDF com Dual Kawase Blur Integrado (sdf.c)
 */

#include "../include/sdf.h"

float sdf_box(float px, float py, float rx, float ry, float rw, float rh, float radius) {
    float half_w = rw * 0.5f;
    float half_h = rh * 0.5f;
    float cx = rx + half_w;
    float cy = ry + half_h;

    float dx = bkn_abs(px - cx) - (half_w - radius);
    float dy = bkn_abs(py - cy) - (half_h - radius);

    float ax = dx > 0.0f ? dx : 0.0f;
    float ay = dy > 0.0f ? dy : 0.0f;
    float outside = bkn_sqrt(ax * ax + ay * ay);

    float inside = (dx > dy) ? (dx < 0.0f ? dx : 0.0f) : (dy < 0.0f ? dy : 0.0f);
    return outside + inside - radius;
}

float sdf_smoothstep(float dist, float softness) {
    if (dist < -softness) return 1.0f;
    if (dist > softness) return 0.0f;
    float t = (dist + softness) / (2.0f * softness);
    return 1.0f - (t * t * (3.0f - 2.0f * t));
}

void bkn_draw_sdf_glass_card(
    uint32_t x, uint32_t y, uint32_t w, uint32_t h,
    float radius,
    uint32_t bg_color, uint8_t bg_alpha,
    uint32_t border_color, float border_width
) {
    // 1. Aplica Dual Kawase Blur no fundo para efeito de vidro fosco real
    bkn_dual_kawase_blur(x, y, w, h, 2);

    float rx = (float)x;
    float ry = (float)y;
    float rw = (float)w;
    float rh = (float)h;

    // 2. Renderiza o corpo do card com cantos arredondados contínuos (Squircles)
    for (uint32_t py = y; py < y + h && py < g_fb_height; py++) {
        for (uint32_t px = x; px < x + w && px < g_fb_width; px++) {
            float dist = sdf_box((float)px + 0.5f, (float)py + 0.5f, rx, ry, rw, rh, radius);
            float alpha_factor = sdf_smoothstep(dist, 0.85f);

            if (alpha_factor > 0.01f) {
                if (dist > -border_width) {
                    float factor = (dist + border_width) / border_width;
                    uint8_t blend_a = (uint8_t)(((float)bg_alpha * (1.0f - factor) + 230.0f * factor) * alpha_factor);
                    bkn_put_pixel_alpha(px, py, border_color, blend_a);
                } else {
                    uint8_t final_alpha = (uint8_t)((float)bg_alpha * alpha_factor);
                    bkn_put_pixel_alpha(px, py, bg_color, final_alpha);
                }
            }
        }
    }
}

void bkn_draw_sdf_circle(uint32_t cx, uint32_t cy, float radius, uint32_t color, uint8_t alpha) {
    uint32_t min_x = (uint32_t)((float)cx > radius + 1.0f ? (float)cx - radius - 1.0f : 0.0f);
    uint32_t min_y = (uint32_t)((float)cy > radius + 1.0f ? (float)cy - radius - 1.0f : 0.0f);
    uint32_t max_x = (uint32_t)((float)cx + radius + 1.0f);
    uint32_t max_y = (uint32_t)((float)cy + radius + 1.0f);

    for (uint32_t py = min_y; py <= max_y && py < g_fb_height; py++) {
        for (uint32_t px = min_x; px <= max_x && px < g_fb_width; px++) {
            float dx = (float)px + 0.5f - (float)cx;
            float dy = (float)py + 0.5f - (float)cy;
            float dist = bkn_sqrt(dx * dx + dy * dy) - radius;
            float coverage = sdf_smoothstep(dist, 0.8f);
            if (coverage > 0.01f) {
                bkn_put_pixel_alpha(px, py, color, (uint8_t)((float)alpha * coverage));
            }
        }
    }
}

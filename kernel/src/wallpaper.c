/*
 * Baken OS - Implementação do Papel de Parede Mesh Gradient (wallpaper.c)
 */

#include "../include/wallpaper.h"

void bkn_render_mesh_wallpaper(void) {
    if (!g_fb_base || g_fb_width == 0 || g_fb_height == 0) return;

    for (uint32_t y = 0; y < g_fb_height; y++) {
        float ny = (float)y / (float)g_fb_height;
        for (uint32_t x = 0; x < g_fb_width; x++) {
            float nx = (float)x / (float)g_fb_width;

            // Interpolação trilinear: Ciano (#00D2FF) -> Rosa/Lilás (#D946EF) -> Dourado (#FDE047)
            float w_cyan = (1.0f - nx) * (1.0f - ny);
            float w_pink = (nx * 0.75f + ny * 0.55f) * (1.0f - (nx * ny * 0.8f));
            float w_gold = nx * ny * 1.35f;
            if (w_gold > 1.0f) w_gold = 1.0f;

            float r = (0x00 * w_cyan) + (0xE8 * w_pink) + (0xFD * w_gold);
            float g = (0xD2 * w_cyan) + (0x79 * w_pink) + (0xC4 * w_gold);
            float b = (0xFF * w_cyan) + (0xF9 * w_pink) + (0x67 * w_gold);

            if (r > 255.0f) r = 255.0f;
            if (g > 255.0f) g = 255.0f;
            if (b > 255.0f) b = 255.0f;

            g_fb_base[y * g_fb_pitch + x] = (0xFF << 24) | (((uint32_t)r) << 16) | (((uint32_t)g) << 8) | (uint32_t)b;
        }
    }
}

/*
 * Baken OS - Implementação do Motor Gráfico com Dual Kawase Blur (gpu.c)
 */

#include "../include/gpu.h"

uint32_t *g_fb_base = NULL;
uint32_t g_fb_width = 0;
uint32_t g_fb_height = 0;
uint32_t g_fb_pitch = 0;

void bkn_kernel_gpu_init(BakenBootInfo *info) {
    if (!info || !info->framebuffer_base) return;
    g_fb_base = info->framebuffer_base;
    g_fb_width = info->screen_width;
    g_fb_height = info->screen_height;
    g_fb_pitch = info->pixels_per_scanline;
}

void bkn_put_pixel(uint32_t x, uint32_t y, uint32_t color) {
    if (x < g_fb_width && y < g_fb_height) {
        g_fb_base[y * g_fb_pitch + x] = color;
    }
}

// Alpha Blending Rápido por Bitwise
uint32_t bkn_blend(uint32_t src, uint32_t dst, uint8_t alpha) {
    if (alpha == 0) return dst;
    if (alpha == 255) return src;

    uint32_t rb = ((src & 0x00FF00FF) * alpha + (dst & 0x00FF00FF) * (255 - alpha)) >> 8;
    uint32_t g  = ((src & 0x0000FF00) * alpha + (dst & 0x0000FF00) * (255 - alpha)) >> 8;

    return (0xFF << 24) | (rb & 0x00FF00FF) | (g & 0x0000FF00);
}

void bkn_put_pixel_alpha(uint32_t x, uint32_t y, uint32_t color, uint8_t alpha) {
    if (x < g_fb_width && y < g_fb_height) {
        uint32_t dst = g_fb_base[y * g_fb_pitch + x];
        g_fb_base[y * g_fb_pitch + x] = bkn_blend(color, dst, alpha);
    }
}

void bkn_draw_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t color) {
    for (uint32_t py = y; py < y + h && py < g_fb_height; py++) {
        for (uint32_t px = x; px < x + w && px < g_fb_width; px++) {
            g_fb_base[py * g_fb_pitch + px] = color;
        }
    }
}

void bkn_draw_rect_alpha(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t color, uint8_t alpha) {
    for (uint32_t py = y; py < y + h && py < g_fb_height; py++) {
        for (uint32_t px = x; px < x + w && px < g_fb_width; px++) {
            bkn_put_pixel_alpha(px, py, color, alpha);
        }
    }
}

// Dual Kawase Blur para Vidro Fosco Real (Frosted Glass Effect)
void bkn_dual_kawase_blur(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t passes) {
    if (!g_fb_base) return;

    for (uint32_t pass = 0; pass < passes; pass++) {
        uint32_t offset = pass + 2;
        for (uint32_t py = y + offset; py < y + h - offset && py < g_fb_height - offset; py++) {
            uint32_t row_up = (py - offset) * g_fb_pitch;
            uint32_t row_down = (py + offset) * g_fb_pitch;
            uint32_t row_curr = py * g_fb_pitch;

            for (uint32_t px = x + offset; px < x + w - offset && px < g_fb_width - offset; px++) {
                uint32_t c1 = g_fb_base[row_up + (px - offset)];
                uint32_t c2 = g_fb_base[row_up + (px + offset)];
                uint32_t c3 = g_fb_base[row_down + (px - offset)];
                uint32_t c4 = g_fb_base[row_down + (px + offset)];

                uint32_t r = (((c1 >> 16) & 0xFF) + ((c2 >> 16) & 0xFF) + ((c3 >> 16) & 0xFF) + ((c4 >> 16) & 0xFF)) >> 2;
                uint32_t g = (((c1 >> 8)  & 0xFF) + ((c2 >> 8)  & 0xFF) + ((c3 >> 8)  & 0xFF) + ((c4 >> 8)  & 0xFF)) >> 2;
                uint32_t b = ((c1 & 0xFF)         + (c2 & 0xFF)         + (c3 & 0xFF)         + (c4 & 0xFF)) >> 2;

                g_fb_base[row_curr + px] = (0xFF << 24) | (r << 16) | (g << 8) | b;
            }
        }
    }
}

float bkn_sqrt(float n) {
    if (n <= 0.0f) return 0.0f;
    float x = n;
    float y = 1.0f;
    float e = 0.0001f;
    while (x - y > e) {
        x = (x + y) / 2.0f;
        y = n / x;
    }
    return x;
}

float bkn_abs(float v) {
    return v < 0.0f ? -v : v;
}

size_t strlen(const char *s) {
    size_t len = 0;
    while (s && s[len] != '\0') len++;
    return len;
}

void* memset(void *s, int c, size_t n) {
    uint8_t *p = (uint8_t*)s;
    while (n--) *p++ = (uint8_t)c;
    return s;
}

void* memcpy(void *dest, const void *src, size_t n) {
    uint8_t *d = (uint8_t*)dest;
    const uint8_t *s = (const uint8_t*)src;
    while (n--) *d++ = *s++;
    return dest;
}

size_t bkn_strlen(const char *s) {
    return strlen(s);
}

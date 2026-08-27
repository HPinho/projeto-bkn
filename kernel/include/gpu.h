/*
 * Baken OS - Motor Gráfico Base com Dual Kawase Blur (gpu.h)
 */

#ifndef BAKEN_GPU_H
#define BAKEN_GPU_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef struct {
    uint32_t *framebuffer_base;
    uint64_t framebuffer_size;
    uint32_t screen_width;
    uint32_t screen_height;
    uint32_t pixels_per_scanline;
    void *memory_map;
    uint64_t memory_map_size;
} BakenBootInfo;

extern uint32_t *g_fb_base;
extern uint32_t g_fb_width;
extern uint32_t g_fb_height;
extern uint32_t g_fb_pitch;

void bkn_kernel_gpu_init(BakenBootInfo *info);
void bkn_put_pixel(uint32_t x, uint32_t y, uint32_t color);
uint32_t bkn_blend(uint32_t src, uint32_t dst, uint8_t alpha);
void bkn_put_pixel_alpha(uint32_t x, uint32_t y, uint32_t color, uint8_t alpha);
void bkn_draw_rect(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t color);
void bkn_draw_rect_alpha(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t color, uint8_t alpha);

// Efeito Vidro Fosco de Alta Fidelidade (Dual Kawase Blur)
void bkn_dual_kawase_blur(uint32_t x, uint32_t y, uint32_t w, uint32_t h, uint32_t passes);

float bkn_sqrt(float n);
float bkn_abs(float v);
size_t bkn_strlen(const char *s);

#endif // BAKEN_GPU_H

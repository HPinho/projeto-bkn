/*
 * Baken OS - Implementação da Top Bar com Tipografia Proporcional (topbar.c)
 */

#include "../include/topbar.h"

void bkn_render_topbar(void) {
    if (!g_fb_base) return;

    // 1. Aplica Dual Kawase Blur sob a barra superior
    bkn_dual_kawase_blur(0, 0, g_fb_width, 28, 2);

    // 2. Fundo translúcido branco suave
    for (uint32_t y = 0; y < 28; y++) {
        for (uint32_t x = 0; x < g_fb_width; x++) {
            bkn_put_pixel_alpha(x, y, 0xFFFFFFFF, 120);
        }
    }
    for (uint32_t x = 0; x < g_fb_width; x++) {
        bkn_put_pixel_alpha(x, 27, 0xFFFFFFFF, 180);
    }

    // Logo Vortex + Título em Negrito
    bkn_draw_vortex_icon(18, 14, 9.0f);
    bkn_draw_text_bold(34, 6, "Baken OS", 0xFF0F172A);

    // Menus Proporcionais
    bkn_draw_text(110, 6, "Arquivo", 0xFF334155);
    bkn_draw_text(168, 6, "Editar", 0xFF334155);
    bkn_draw_text(218, 6, "Exibir", 0xFF334155);
    bkn_draw_text(268, 6, "Janela", 0xFF334155);
    bkn_draw_text(320, 6, "Ajuda", 0xFF334155);

    // Badges da Direita
    // Badge Q-HAL AI
    bkn_draw_sdf_glass_card(g_fb_width - 410, 3, 84, 22, 11.0f, 0xFF00E5FF, 220, 0xFF8B5CF6, 1.0f);
    bkn_draw_text_bold(g_fb_width - 402, 6, "* Q-HAL AI", 0xFFFFFFFF);

    // Botão de Voz
    bkn_draw_sdf_glass_card(g_fb_width - 320, 3, 46, 22, 11.0f, 0xFFFFFFFF, 200, 0x88FFFFFF, 1.0f);
    bkn_draw_text(g_fb_width - 310, 6, "Voz", 0xFF0284C7);

    // Escudo de Privacidade
    bkn_draw_sdf_glass_card(g_fb_width - 268, 3, 22, 22, 11.0f, 0xFF10B981, 240, 0xFF059669, 1.0f);
    bkn_draw_text(g_fb_width - 262, 6, "o", 0xFFFFFFFF);

    // Indicador PT-BR
    bkn_draw_sdf_glass_card(g_fb_width - 240, 3, 56, 22, 11.0f, 0xFFFFFFFF, 180, 0x66FFFFFF, 1.0f);
    bkn_draw_text(g_fb_width - 232, 6, "PT-BR", 0xFF1E293B);

    // Relógio
    bkn_draw_text(g_fb_width - 174, 6, "10:36 AM  26/08", 0xFF0F172A);
}

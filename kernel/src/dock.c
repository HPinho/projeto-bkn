/*
 * Baken OS - Doca Flutuante com Tipografia Proporcional (dock.c)
 */

#include "../include/dock.h"

void bkn_render_dock(void) {
    if (!g_fb_base || g_fb_width < 900) return;

    uint32_t dock_w = 880;
    uint32_t dock_h = 48;
    uint32_t dock_x = (g_fb_width - dock_w) / 2;
    uint32_t dock_y = g_fb_height - 58;

    // 1. Cápsula de vidro fosco translúcida com Dual Kawase Blur
    bkn_draw_sdf_glass_card(dock_x, dock_y, dock_w, dock_h, 16.0f, 0xFFFFFFFF, 175, 0x88FFFFFF, 1.2f);

    // 2. Botão Iniciar Vortex à esquerda
    bkn_draw_vortex_icon(dock_x + 24, dock_y + 24, 13.0f);

    // 3. Os 15 Blocos de Aplicativos com seus Glifos Vetoriais
    uint32_t tile_colors[15] = {
        0xFFC084FC, 0xFF38BDF8, 0xFFA855F7, 0xFFF97316, 0xFFF43F5E,
        0xFF00E5FF, 0xFF60A5FA, 0xFF34D399, 0xFFFBBF24, 0xFF1E293B,
        0xFF8B5CF6, 0xFF64748B, 0xFF0284C7, 0xFF10B981, 0xFFF59E0B
    };

    for (int i = 0; i < 15; i++) {
        uint32_t tx = dock_x + 48 + (i * 38);
        bkn_draw_sdf_glass_card(tx, dock_y + 7, 32, 32, 8.0f, tile_colors[i], 255, 0xFFFFFFFF, 1.0f);
        bkn_draw_dock_app_glyph(tx + 16, dock_y + 23, i);
    }

    // 4. Controles Rápidos: Busca, Mixer, Microfone
    uint32_t ctrl_x = dock_x + 48 + (15 * 38) + 8;
    bkn_draw_text(ctrl_x, dock_y + 16, "Q", 0xFF64748B);
    bkn_draw_text(ctrl_x + 14, dock_y + 16, "=", 0xFF64748B);
    bkn_draw_text(ctrl_x + 28, dock_y + 16, "Y", 0xFF64748B);

    // 5. Pílula de Perfil do Usuário
    uint32_t prof_x = dock_x + dock_w - 146;
    bkn_draw_sdf_glass_card(prof_x, dock_y + 5, 138, 38, 12.0f, 0xFFFFFFFF, 200, 0x66FFFFFF, 1.0f);

    // Avatar HP
    bkn_draw_sdf_circle(prof_x + 20, dock_y + 24, 12.0f, 0xFF00E5FF, 255);
    bkn_draw_text_bold(prof_x + 13, dock_y + 16, "HP", 0xFFFFFFFF);

    bkn_draw_text_bold(prof_x + 38, dock_y + 9, "Hiago Pinho", 0xFF0F172A);
    bkn_draw_text(prof_x + 38, dock_y + 23, "Ring 0 Sovereign", 0xFF64748B);
}

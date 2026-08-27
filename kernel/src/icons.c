/*
 * Baken OS - Ícones Vetoriais Nativos com Tipografia Proporcional (icons.c)
 */

#include "../include/icons.h"

void bkn_draw_vector_folder(uint32_t x, uint32_t y, const char *label, uint32_t color) {
    // Sombra suave
    bkn_draw_sdf_glass_card(x + 2, y + 4, 46, 36, 6.0f, 0xFF000000, 60, 0, 0.0f);

    // Aba da pasta
    bkn_draw_sdf_glass_card(x + 2, y, 22, 12, 4.0f, color, 255, 0xFFFFFFFF, 1.0f);

    // Corpo da pasta
    bkn_draw_sdf_glass_card(x, y + 6, 46, 34, 6.0f, color, 255, 0xFFFFFFFF, 1.2f);

    // Folha branca interna
    bkn_draw_sdf_glass_card(x + 8, y + 14, 30, 18, 3.0f, 0xFFFFFFFF, 220, 0xFFFFFFFF, 0.5f);

    // Label perfeitamente centralizado com espaçamento proporcional
    bkn_draw_text_centered(x + 23, y + 44, label, 0xFFFFFFFF);
}

void bkn_draw_system_core_card(uint32_t x, uint32_t y) {
    bkn_draw_sdf_glass_card(x, y, 46, 38, 8.0f, 0xFF090D16, 250, 0xFF00E5FF, 1.2f);
    bkn_draw_vortex_icon(x + 23, y + 19, 11.0f);
    bkn_draw_text_centered(x + 23, y + 44, "System Core", 0xFFFFFFFF);
}

void bkn_draw_vortex_icon(uint32_t cx, uint32_t cy, float radius) {
    bkn_draw_sdf_circle(cx, cy, radius, 0xFF000000, 255);
    bkn_draw_sdf_circle(cx, cy, radius - 3.0f, 0xFF00E5FF, 255);
    bkn_draw_sdf_circle(cx, cy, radius - 6.0f, 0xFF000000, 255);
    bkn_draw_sdf_circle(cx, cy, 3.0f, 0xFF00E5FF, 255);
}

void bkn_draw_weather_sun(uint32_t cx, uint32_t cy) {
    bkn_draw_sdf_circle(cx, cy, 8.0f, 0xFFF59E0B, 255);
    float angles[8][2] = {{0, -12}, {9, -9}, {12, 0}, {9, 9}, {0, 12}, {-9, 9}, {-12, 0}, {-9, -9}};
    for (int i = 0; i < 8; i++) {
        bkn_put_pixel((uint32_t)((float)cx + angles[i][0]), (uint32_t)((float)cy + angles[i][1]), 0xFFFBBF24);
    }
}

// Renderizador dos 15 Glifos Vetoriais da Doca
void bkn_draw_dock_app_glyph(uint32_t cx, uint32_t cy, int app_id) {
    switch (app_id) {
        case 0: // BakenFS: Pasta
            bkn_draw_rect(cx - 7, cy - 3, 14, 10, 0xFFFFFFFF);
            bkn_draw_rect(cx - 7, cy - 6, 6, 3, 0xFFFFFFFF);
            break;
        case 1: // Web Browser: Globo
            bkn_draw_sdf_circle(cx, cy, 7.0f, 0xFFFFFFFF, 255);
            bkn_draw_sdf_circle(cx, cy, 5.0f, 0xFF38BDF8, 255);
            bkn_draw_rect(cx - 5, cy, 10, 1, 0xFFFFFFFF);
            bkn_draw_rect(cx, cy - 5, 1, 10, 0xFFFFFFFF);
            break;
        case 2: // Hi-Res Media: Nota Musical
            bkn_draw_sdf_circle(cx - 3, cy + 3, 3.0f, 0xFFFFFFFF, 255);
            bkn_draw_rect(cx, cy - 5, 2, 8, 0xFFFFFFFF);
            bkn_draw_rect(cx, cy - 5, 5, 3, 0xFFFFFFFF);
            break;
        case 3: // Synth DAW: Teclado
            bkn_draw_rect(cx - 7, cy - 4, 14, 9, 0xFFFFFFFF);
            bkn_draw_rect(cx - 4, cy - 4, 2, 5, 0xFF000000);
            bkn_draw_rect(cx - 1, cy - 4, 2, 5, 0xFF000000);
            bkn_draw_rect(cx + 2, cy - 4, 2, 5, 0xFF000000);
            break;
        case 4: // Paint 2D: Pincel
            bkn_draw_rect(cx - 5, cy - 5, 4, 10, 0xFFFFFFFF);
            bkn_draw_rect(cx + 1, cy - 2, 5, 7, 0xFFFFFFFF);
            break;
        case 5: // 3D Studio: Cubo Isométrico
            bkn_draw_rect(cx - 5, cy - 5, 10, 10, 0xFFFFFFFF);
            bkn_draw_rect(cx - 3, cy - 3, 6, 6, 0xFF00E5FF);
            break;
        case 6: // Writer: Documento
            bkn_draw_rect(cx - 5, cy - 6, 10, 12, 0xFFFFFFFF);
            bkn_draw_rect(cx - 3, cy - 3, 6, 2, 0xFF60A5FA);
            bkn_draw_rect(cx - 3, cy - 0, 6, 2, 0xFF60A5FA);
            bkn_draw_rect(cx - 3, cy + 3, 4, 2, 0xFF60A5FA);
            break;
        case 7: // Sheets: Grade de Tabela
            bkn_draw_rect(cx - 6, cy - 6, 12, 12, 0xFFFFFFFF);
            bkn_draw_rect(cx - 5, cy - 2, 10, 1, 0xFF34D399);
            bkn_draw_rect(cx - 5, cy + 2, 10, 1, 0xFF34D399);
            bkn_draw_rect(cx - 1, cy - 5, 1, 10, 0xFF34D399);
            break;
        case 8: // Presenter: Slide
            bkn_draw_rect(cx - 6, cy - 4, 12, 9, 0xFFFFFFFF);
            bkn_draw_rect(cx - 2, cy - 2, 4, 4, 0xFFFBBF24);
            break;
        case 9: // Visual Studio: Tags < >
            bkn_draw_text(cx - 7, cy - 7, "<>", 0xFFFFFFFF);
            break;
        case 10: // Notepad++: Arquivo de Código
            bkn_draw_rect(cx - 5, cy - 6, 10, 12, 0xFFFFFFFF);
            bkn_draw_text(cx - 4, cy - 6, "++", 0xFF8B5CF6);
            break;
        case 11: // Configurações: Engrenagem
            bkn_draw_sdf_circle(cx, cy, 6.0f, 0xFFFFFFFF, 255);
            bkn_draw_sdf_circle(cx, cy, 3.0f, 0xFF64748B, 255);
            break;
        case 12: // OriginPro Studio: Curva e Gráfico
            bkn_draw_rect(cx - 6, cy + 4, 12, 1, 0xFFFFFFFF);
            bkn_draw_rect(cx - 6, cy - 5, 1, 10, 0xFFFFFFFF);
            bkn_put_pixel(cx - 3, cy + 2, 0xFF00E5FF);
            bkn_put_pixel(cx - 1, cy - 2, 0xFF00E5FF);
            bkn_put_pixel(cx + 2, cy - 1, 0xFF00E5FF);
            bkn_put_pixel(cx + 4, cy + 3, 0xFF00E5FF);
            break;
        case 13: // Antigravity AI: Escudo
            bkn_draw_rect(cx - 5, cy - 5, 10, 7, 0xFFFFFFFF);
            bkn_draw_rect(cx - 3, cy + 2, 6, 3, 0xFFFFFFFF);
            bkn_draw_rect(cx - 1, cy + 5, 2, 2, 0xFFFFFFFF);
            break;
        case 14: // Loja BakenPKG: Sacola
            bkn_draw_rect(cx - 5, cy - 2, 10, 9, 0xFFFFFFFF);
            bkn_draw_rect(cx - 3, cy - 5, 6, 3, 0xFFFFFFFF);
            break;
    }
}

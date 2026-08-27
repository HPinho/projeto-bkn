/*
 * Baken OS - Widgets com Ajuste Fino de Tipografia e Layout (widgets.c)
 */

#include "../include/widgets.h"

void bkn_draw_progress_bar(uint32_t x, uint32_t y, uint32_t w, uint32_t h, float percent, uint32_t color) {
    bkn_draw_sdf_glass_card(x, y, w, h, (float)h * 0.5f, 0xFF1E293B, 200, 0x33FFFFFF, 0.8f);
    uint32_t fill_w = (uint32_t)((float)w * percent);
    if (fill_w > 4) {
        bkn_draw_sdf_glass_card(x, y, fill_w, h, (float)h * 0.5f, color, 255, 0xFFFFFFFF, 0.5f);
    }
}

void bkn_render_side_widgets(void) {
    if (!g_fb_base || g_fb_width < 250) return;

    uint32_t widget_w = 216;
    uint32_t wx = g_fb_width - widget_w - 20;

    // WIDGET 1: CLIMA (Teresina 32°C - H: 70px)
    bkn_draw_sdf_glass_card(wx, 38, widget_w, 70, 10.0f, 0xFFFFFFFF, 210, 0xFFFFFFFF, 1.0f);
    bkn_draw_text_bold(wx + 10, 44, "Teresina, Piaui", 0xFFEA580C);
    bkn_draw_weather_sun(wx + 20, 68);
    bkn_draw_text_bold(wx + 38, 60, "32*C", 0xFF0F172A);
    bkn_draw_text_bold(wx + 86, 60, "Ensolarado", 0xFF059669);
    bkn_draw_text(wx + 10, 86, "Umid: 68% | Vento: 14km/h", 0xFF475569);

    // WIDGET 2: MUSIC PLAYER (Sovereign Symphonia - H: 64px)
    bkn_draw_sdf_glass_card(wx, 116, widget_w, 64, 10.0f, 0xFF0F172A, 240, 0xFF38BDF8, 1.0f);
    bkn_draw_sdf_glass_card(wx + 8, 122, 24, 24, 6.0f, 0xFF38BDF8, 255, 0xFFFFFFFF, 0.8f);
    bkn_draw_text_bold(wx + 16, 126, ">", 0xFF000000);
    bkn_draw_text_bold(wx + 38, 122, "Sovereign Symphonia", 0xFFFFFFFF);
    bkn_draw_text(wx + 38, 138, "Baken Synthesizer", 0xFF94A3B8);
    bkn_draw_progress_bar(wx + 38, 154, 160, 3, 0.45f, 0xFF00E5FF);
    bkn_draw_text(wx + 72, 162, "|<   ||   >|", 0xFF38BDF8);

    // WIDGET 3: CALENDÁRIO (Agosto 2026 - H: 90px)
    bkn_draw_sdf_glass_card(wx, 188, widget_w, 90, 10.0f, 0xFFFFFFFF, 220, 0xFFFFFFFF, 1.0f);
    bkn_draw_text_bold(wx + 10, 194, "Agosto 2026", 0xFF0F172A);
    bkn_draw_text(wx + 140, 194, "Baken OS", 0xFF64748B);
    bkn_draw_text(wx + 12, 210, " D   S   T   Q   Q   S   S", 0xFF64748B);
    bkn_draw_text(wx + 12, 226, " 2   3   4   5   6   7   8", 0xFF334155);
    bkn_draw_text(wx + 12, 240, " 9  10  11  12  13  14  15", 0xFF334155);
    bkn_draw_text(wx + 12, 254, "16  17  18  19  20  21  22", 0xFF334155);

    // Destaque do dia 26
    bkn_draw_sdf_glass_card(wx + 110, 264, 20, 14, 4.0f, 0xFF0284C7, 255, 0xFF00E5FF, 0.8f);
    bkn_draw_text(wx + 12, 266, "23  24  25      27  28  29", 0xFF334155);
    bkn_draw_text_bold(wx + 112, 264, "26", 0xFFFFFFFF);

    // WIDGET 4: HARDWARE LIVE MONITOR (H: 75px)
    bkn_draw_sdf_glass_card(wx, 286, widget_w, 75, 10.0f, 0xFF090D18, 240, 0xFF10B981, 1.0f);
    bkn_draw_text_bold(wx + 10, 292, "Hardware Live Monitor", 0xFF34D399);
    bkn_draw_text(wx + 10, 308, "CPU: Ryzen 7 7700X 18%", 0xFFE2E8F0);
    bkn_draw_progress_bar(wx + 10, 320, 194, 3, 0.18f, 0xFF10B981);
    bkn_draw_text(wx + 10, 326, "GPU: Radeon   120 FPS", 0xFF38BDF8);
    bkn_draw_text(wx + 10, 342, "RAM: 8.9GB  NVMe: 74GB", 0xFFFCD34D);

    // WIDGET 5: NOTAS RÁPIDAS (H: 70px)
    bkn_draw_sdf_glass_card(wx, 369, widget_w, 70, 10.0f, 0xFFFEF08A, 230, 0xFFFFFFFF, 1.0f);
    bkn_draw_text_bold(wx + 10, 375, "* Notas Rapidas", 0xFF854D0E);
    bkn_draw_text(wx + 10, 391, "Lembrete Baken OS:", 0xFF713F12);
    bkn_draw_text(wx + 10, 405, "- Compilacao BKNC v2.0", 0xFF713F12);
    bkn_draw_text(wx + 10, 419, "- Q-HAL 20 Fases 100%", 0xFF713F12);
}

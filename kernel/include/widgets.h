/*
 * Baken OS - Widgets do Painel Lateral Direito (widgets.h)
 */

#ifndef BAKEN_WIDGETS_H
#define BAKEN_WIDGETS_H

#include "gpu.h"
#include "sdf.h"
#include "font.h"
#include "icons.h"

void bkn_draw_progress_bar(uint32_t x, uint32_t y, uint32_t w, uint32_t h, float percent, uint32_t color);
void bkn_render_side_widgets(void);

#endif // BAKEN_WIDGETS_H

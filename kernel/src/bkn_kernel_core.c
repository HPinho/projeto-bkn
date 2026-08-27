/*
 * Baken OS - Kernel Desktop Orchestrator (bkn_kernel_core.c)
 * Integração modular de todos os componentes da interface gráfica nativa:
 * GPU Base, SDF Engine, Fontes, Wallpaper, Top Bar, Desktop Folders, Widgets e Dock.
 */

#include "../include/gpu.h"
#include "../include/sdf.h"
#include "../include/font.h"
#include "../include/icons.h"
#include "../include/wallpaper.h"
#include "../include/topbar.h"
#include "../include/widgets.h"
#include "../include/dock.h"

void bkn_render_desktop_folders(void) {
    // Coluna 1 (X = 36)
    bkn_draw_vector_folder(36, 60, "BakenFS", 0xFFC084FC);
    bkn_draw_vector_folder(36, 150, "Web Browser", 0xFF38BDF8);
    bkn_draw_system_core_card(36, 244);
    bkn_draw_vector_folder(36, 330, "Writer", 0xFF60A5FA);
    bkn_draw_vector_folder(36, 420, "Sheets", 0xFF34D399);
    bkn_draw_vector_folder(36, 510, "Presenter", 0xFFFBBF24);

    // Coluna 2 (X = 146)
    bkn_draw_vector_folder(146, 60, "3D Studio", 0xFF38BDF8);
    bkn_draw_vector_folder(146, 150, "Paint 2D", 0xFFF43F5E);
    bkn_draw_vector_folder(146, 240, "Hi-Res Media", 0xFFA855F7);
    bkn_draw_vector_folder(146, 330, "Synth DAW", 0xFFF97316);
}

void bkn_kernel_main(BakenBootInfo *boot_info) {
    // 1. Inicializa o hardware de vídeo e framebuffer GOP
    bkn_kernel_gpu_init(boot_info);

    // 2. Renderiza o papel de parede Mesh Gradient
    bkn_render_mesh_wallpaper();

    // 3. Renderiza a Top Bar translúcida
    bkn_render_topbar();

    // 4. Renderiza as pastas e ícones do Desktop
    bkn_render_desktop_folders();

    // 5. Renderiza a coluna dos 5 Widgets laterais
    bkn_render_side_widgets();

    // 6. Renderiza a Doca Flutuante com perfil Hiago Pinho
    bkn_render_dock();
}

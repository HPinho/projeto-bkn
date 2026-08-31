// Compositor canônico do desktop Cq.
//
// Esta é a única fachada que kernel::main pode usar para renderizar a sessão
// gráfica. Ela impede que o boot, widgets e aplicativos inicializem motores de
// vídeo concorrentes ou escrevam diretamente no framebuffer.

module kernel::desktop_compositor;

import kernel::desktop_shell::*;

static mut COMPOSITOR_READY: bool = false;

@system
pub fn desktop_compositor_init(screen_w: u32, screen_h: u32) -> void {
    unsafe {
        if COMPOSITOR_READY { return; }

        // graphics_engine já recebeu o framebuffer no início de kernel::main.
        // A integração de BakenUI e WindowManager volta aqui quando ambos
        // estiverem no build Cq validado; o shell continua sendo a única
        // superfície renderizada nesta rota inicial.
        desktop_shell_init(screen_w, screen_h);
        COMPOSITOR_READY = true;
    }
}

@system
pub fn desktop_compositor_render_frame() -> void {
    unsafe {
        if !COMPOSITOR_READY { return; }
        desktop_shell_render_frame();
    }
}

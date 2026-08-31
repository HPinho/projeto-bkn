module kernel::minimal;
import core::mem::*;
import core::fmt::*;
import core::serial::*;
import core::vga::*;

@repr(C)
@packed
pub struct BootFrame {
    framebuffer: *mut u32;
    framebuffer_size: usize;
    width: u32;
    height: u32;
    pitch: u32;
    tag: [u8; 8];
}

@system
pub fn init_frame(frame: *mut BootFrame, fb: *mut u32, width: u32, height: u32, pitch: u32) -> MemStatus {
    if fb == null {
        return MemStatus::OutOfMemory;
    }
    let size: usize = (height as usize * pitch as usize);
    zero_memory(fb as *mut u8, size);
    if frame != null {
        frame.framebuffer = fb;
        frame.framebuffer_size = size;
        frame.width = width;
        frame.height = height;
        frame.pitch = pitch;
    }
    return MemStatus::Ok;
}

@export
@system
pub fn kernel_main(frame: *mut BootFrame) -> u64 {
    serial_init(COM1);
    serial_write_line(COM1, "[Baken OS] Kernel Cq 0.1 Minimal inicializado com sucesso!");

    if frame != null && frame.framebuffer != null {
        let mut fb: Framebuffer = 0;
        fb.base = frame.framebuffer;
        fb.width = frame.width;
        fb.height = frame.height;
        fb.pitch = frame.pitch;

        // Fundo cósmico escuro
        let bg_color: u32 = rgb(15, 23, 42);
        clear(&fb, bg_color);

        // Top bar ciano
        let top_color: u32 = rgb(6, 182, 212);
        fill_rect(&fb, 0, 0, fb.width, 32, top_color);

        // Superfície de janela
        let win_color: u32 = rgb(30, 41, 59);
        fill_rect(&fb, 80, 80, 480, 320, win_color);

        // Barra de título da janela
        let title_color: u32 = rgb(51, 65, 85);
        fill_rect(&fb, 80, 80, 480, 36, title_color);

        serial_write_line(COM1, "[Baken OS] Tela e janela de teste renderizadas no framebuffer.");
    }

    return 0;
}

@export
pub fn available_memory(capacity: usize, used: usize) -> usize {
    return remaining(capacity, used);
}



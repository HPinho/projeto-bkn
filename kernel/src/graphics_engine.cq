// Baken OS - Motor Gráfico de Pixels de Alta Definição em Cq (@system)
// Renderização Linear 32-bit ARGB8888.
// A rota gráfica inicial usa o framebuffer GOP diretamente. Double buffering
// só pode ser ligado após o PMM ser inicializado com um mapa de memória UEFI
// válido; alocar páginas antes disso corrompe a inicialização.

module kernel::graphics_engine;


pub struct FramebufferConfig {
    pub base: *mut u32;
    pub backbuffer: *mut u32;
    pub width: u32;
    pub height: u32;
    pub pitch: u32;
    pub use_double_buffering: bool;
}

static mut FB: FramebufferConfig = FramebufferConfig {
    base: null as *mut u32,
    backbuffer: null as *mut u32,
    width: 1920,
    height: 1080,
    pitch: 1920,
    use_double_buffering: false
};

@system
pub fn gfx_init(base: *mut u32, width: u32, height: u32, pitch: u32) -> void {
    unsafe {
        FB.base = base;
        FB.width = width;
        FB.height = height;
        FB.pitch = pitch;

        FB.backbuffer = base;
        FB.use_double_buffering = false;
    }
}

@system
pub fn gfx_get_backbuffer() -> *mut u32 {
    unsafe {
        return FB.backbuffer;
    }
}

@system
pub fn gfx_get_pitch() -> u32 {
    unsafe {
        return FB.pitch;
    }
}

@system
pub fn gfx_get_width() -> u32 {
    unsafe {
        return FB.width;
    }
}

@system
pub fn gfx_get_height() -> u32 {
    unsafe {
        return FB.height;
    }
}

// Mantém o contrato da API. Na fase GOP direta não há buffer secundário.
@system
pub fn gfx_swap_buffers() -> void {
    unsafe {
        if (!FB.use_double_buffering || FB.backbuffer == null as *mut u32 || FB.base == null as *mut u32) { return; }
        
        let total_u64 = (FB.width * FB.height * 4 / 8) as usize;
        let src_u64 = FB.backbuffer as *const u64;
        let dst_u64 = FB.base as *mut u64;

        for mut i in 0 .. total_u64 {
            *(dst_u64 + i) = *(src_u64 + i);
        }
    }
}

@system
pub fn gfx_put_pixel(x: u32, y: u32, color: u32) -> void {
    unsafe {
        if (x < FB.width && y < FB.height) {
            let offset = (y * FB.pitch + x) as usize;
            *(FB.backbuffer + offset) = color;
        }
    }
}

@system
pub fn gfx_get_pixel(x: u32, y: u32) -> u32 {
    unsafe {
        if (x < FB.width && y < FB.height) {
            let offset = (y * FB.pitch + x) as usize;
            return *(FB.backbuffer + offset);
        }
        return 0;
    }
}

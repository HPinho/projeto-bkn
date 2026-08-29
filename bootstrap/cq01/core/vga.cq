module core::vga;

@repr(C)
pub struct Framebuffer {
    base: *mut u32;
    width: u32;
    height: u32;
    pitch: u32;
}

pub fn rgb(r: u8, g: u8, b: u8) -> u32 {
    let r32: u32 = r as u32;
    let g32: u32 = g as u32;
    let b32: u32 = b as u32;
    return (r32 << 16) | (g32 << 8) | b32;
}

@system
pub fn put_pixel(fb: *mut Framebuffer, x: u32, y: u32, color: u32) -> void {
    if fb == null {
        return;
    }
    if x >= fb.width || y >= fb.height {
        return;
    }
    unsafe {
        let offset: usize = (y as usize * (fb.pitch as usize / 4)) + x as usize;
        fb.base[offset] = color;
    }
}

@system
pub fn clear(fb: *mut Framebuffer, color: u32) -> void {
    if fb == null {
        return;
    }
    let mut y: u32 = 0;
    while y < fb.height {
        let mut x: u32 = 0;
        while x < fb.width {
            put_pixel(fb, x, y, color);
            x = x + 1;
        }
        y = y + 1;
    }
}

@system
pub fn fill_rect(fb: *mut Framebuffer, rx: u32, ry: u32, rw: u32, rh: u32, color: u32) -> void {
    if fb == null {
        return;
    }
    let mut y: u32 = ry;
    let max_y: u32 = ry + rh;
    let max_x: u32 = rx + rw;
    while y < max_y && y < fb.height {
        let mut x: u32 = rx;
        while x < max_x && x < fb.width {
            put_pixel(fb, x, y, color);
            x = x + 1;
        }
        y = y + 1;
    }
}

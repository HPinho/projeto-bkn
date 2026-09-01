module core::serial;

pub const COM1: u16 = 0x3F8;

@system
pub fn serial_init(port: u16) -> bool {
    __outb(port + 1, 0x00);
    __outb(port + 3, 0x80);
    __outb(port + 0, 0x03);
    __outb(port + 1, 0x00);
    __outb(port + 3, 0x03);
    __outb(port + 2, 0xC7);
    __outb(port + 4, 0x0B);
    return true;
}

@system
pub fn serial_is_transmit_empty(port: u16) -> bool {
    let status: u8 = __inb(port + 5);
    return (status & 0x20) != 0;
}

@system
pub fn serial_write_byte(port: u16, b: u8) -> void {
    while !serial_is_transmit_empty(port) {
    }
    __outb(port, b);
}

@system
pub fn serial_write_str(port: u16, str: *const u8) -> void {
    if str == null {
        return;
    }
    let mut i: usize = 0;
    unsafe {
        while str[i] != 0 {
            serial_write_byte(port, str[i]);
            i = i + 1;
        }
    }
}

@system
pub fn serial_write_line(port: u16, str: *const u8) -> void {
    serial_write_str(port, str);
    serial_write_byte(port, 13);
    serial_write_byte(port, 10);
}

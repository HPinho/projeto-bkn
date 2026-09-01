module core::fmt;

pub fn str_len(str: *const u8) -> usize {
    let mut len: usize = 0;
    if str == null {
        return 0;
    }
    unsafe {
        while str[len] != 0 {
            len = len + 1;
        }
    }
    return len;
}

pub fn hex_digit(digit: u8) -> u8 {
    if digit < 10 {
        return 48 + digit;
    } else {
        return 65 + (digit - 10);
    }
}

pub fn u64_to_hex(val: u64, buf: *mut u8, max_len: usize) -> usize {
    if buf == null {
        return 0;
    }
    if max_len < 19 {
        return 0;
    }
    unsafe {
        buf[0] = 48;
        buf[1] = 120;
        let mut i: usize = 0;
        let mut shift: u64 = 60;
        while i < 16 {
            let nibble: u8 = ((val / (1 as u64 << shift)) % 16) as u8;
            buf[2 + i] = hex_digit(nibble);
            if shift >= 4 {
                shift = shift - 4;
            }
            i = i + 1;
        }
        buf[18] = 0;
    }
    return 18;
}

pub fn u64_to_dec(val: u64, buf: *mut u8, max_len: usize) -> usize {
    if buf == null {
        return 0;
    }
    if max_len < 21 {
        return 0;
    }
    if val == 0 {
        unsafe {
            buf[0] = 48;
            buf[1] = 0;
        }
        return 1;
    }
    let mut temp: [u8; 32] = 0;
    let mut count: usize = 0;
    let mut current: u64 = val;
    while current > 0 {
        let rem: u8 = (current % 10) as u8;
        temp[count] = 48 + rem;
        count = count + 1;
        current = current / 10;
    }
    let mut pos: usize = 0;
    unsafe {
        while pos < count {
            buf[pos] = temp[count - 1 - pos];
            pos = pos + 1;
        }
        buf[count] = 0;
    }
    return count;
}

pub fn str_eq(a: *const u8, b: *const u8) -> bool {
    if a == null || b == null {
        return a == b;
    }
    let mut i: usize = 0;
    unsafe {
        while a[i] != 0 && b[i] != 0 {
            if a[i] != b[i] {
                return false;
            }
            i = i + 1;
        }
        return a[i] == b[i];
    }
}

pub fn str_copy(dest: *mut u8, src: *const u8, max_len: usize) -> usize {
    if dest == null || src == null || max_len == 0 {
        return 0;
    }
    let mut i: usize = 0;
    unsafe {
        while src[i] != 0 && i < (max_len - 1) {
            dest[i] = src[i];
            i = i + 1;
        }
        dest[i] = 0;
    }
    return i;
}

pub fn str_concat(dest: *mut u8, src: *const u8, max_len: usize) -> usize {
    if dest == null || src == null || max_len == 0 {
        return 0;
    }
    let dest_len: usize = str_len(dest);
    if dest_len >= (max_len - 1) {
        return dest_len;
    }
    let mut i: usize = 0;
    unsafe {
        while src[i] != 0 && (dest_len + i) < (max_len - 1) {
            dest[dest_len + i] = src[i];
            i = i + 1;
        }
        dest[dest_len + i] = 0;
    }
    return dest_len + i;
}


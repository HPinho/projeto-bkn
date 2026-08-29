module core::mem;

pub enum MemStatus {
    Ok = 0,
    OutOfMemory = 1,
    InvalidAlignment = 2
}

pub const DEFAULT_PAGE_SIZE: usize = 4096;

pub struct Buffer {
    base: *mut u8;
    capacity: usize;
    used: usize;
}

pub fn zero_memory(dest: *mut u8, count: usize) -> void {
    let mut i: usize = 0;
    unsafe {
        while i < count {
            dest[i] = 0;
            i = i + 1;
        }
    }
}

pub fn get_default_page_size() -> usize {
    return DEFAULT_PAGE_SIZE;
}

pub fn remaining(capacity: usize, used: usize) -> usize {
    if used < capacity {
        return capacity - used;
    } else {
        return 0;
    }
}


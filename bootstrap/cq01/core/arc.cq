module core::arc;
import core::mem::*;

@repr(C)
pub struct ArcHeader {
    ref_count: usize;
    data_size: usize;
}

pub fn arc_init(header: *mut ArcHeader, size: usize) {
    if header != null {
        unsafe {
            header.ref_count = 1;
            header.data_size = size;
        }
    }
}

pub fn arc_retain(header: *mut ArcHeader) -> *mut ArcHeader {
    if header != null {
        unsafe {
            header.ref_count = header.ref_count + 1;
        }
    }
    return header;
}

pub fn arc_release(header: *mut ArcHeader) -> bool {
    if header != null {
        unsafe {
            if header.ref_count > 0 {
                header.ref_count = header.ref_count - 1;
            }
            return header.ref_count == 0;
        }
    }
    return false;
}

pub fn arc_count(header: *const ArcHeader) -> usize {
    if header == null {
        return 0;
    }
    unsafe {
        return header.ref_count;
    }
}

pub class SharedCounter {
    header: ArcHeader;
    value: u64;

    pub fn new(initial: u64) -> SharedCounter {
        let mut sc: SharedCounter = 0;
        arc_init(&sc.header, 8);
        sc.value = initial;
        return sc;
    }

    pub fn increment(self: *mut SharedCounter) {
        if self != null {
            unsafe {
                self.value = self.value + 1;
            }
        }
    }

    pub fn get_value(self: *const SharedCounter) -> u64 {
        if self == null {
            return 0;
        }
        unsafe {
            return self.value;
        }
    }

    pub fn retain(self: *mut SharedCounter) {
        if self != null {
            unsafe {
                arc_retain(&self.header);
            }
        }
    }

    pub fn release(self: *mut SharedCounter) -> bool {
        if self != null {
            unsafe {
                return arc_release(&self.header);
            }
        }
        return false;
    }
}

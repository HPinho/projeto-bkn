module core::option;

pub class OptionU32 {
    has_value: bool;
    value: u32;

    pub fn some(val: u32) -> OptionU32 {
        let mut opt: OptionU32 = 0;
        opt.has_value = true;
        opt.value = val;
        return opt;
    }

    pub fn none() -> OptionU32 {
        let mut opt: OptionU32 = 0;
        opt.has_value = false;
        opt.value = 0;
        return opt;
    }

    pub fn is_some(self: *const OptionU32) -> bool {
        if self == null {
            return false;
        }
        unsafe {
            return self.has_value;
        }
    }

    pub fn is_none(self: *const OptionU32) -> bool {
        if self == null {
            return true;
        }
        unsafe {
            return !self.has_value;
        }
    }

    pub fn unwrap_or(self: *const OptionU32, default_val: u32) -> u32 {
        if self == null {
            return default_val;
        }
        unsafe {
            if self.has_value {
                return self.value;
            }
        }
        return default_val;
    }
}

pub class OptionPtr {
    has_value: bool;
    ptr: *mut u8;

    pub fn some(p: *mut u8) -> OptionPtr {
        let mut opt: OptionPtr = 0;
        opt.has_value = (p != null);
        opt.ptr = p;
        return opt;
    }

    pub fn none() -> OptionPtr {
        let mut opt: OptionPtr = 0;
        opt.has_value = false;
        opt.ptr = null;
        return opt;
    }

    pub fn is_some(self: *const OptionPtr) -> bool {
        if self == null {
            return false;
        }
        unsafe {
            return self.has_value;
        }
    }

    pub fn unwrap(self: *const OptionPtr) -> *mut u8 {
        if self == null {
            return null;
        }
        unsafe {
            return self.ptr;
        }
    }
}

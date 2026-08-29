module core::result;

pub enum ResultCode {
    Ok = 0,
    Error = 1,
    OutOfMemory = 2,
    InvalidParam = 3,
    NotFound = 4
}

pub class ResultU32 {
    status: ResultCode;
    value: u32;

    pub fn ok(val: u32) -> ResultU32 {
        let mut r: ResultU32 = 0;
        r.status = ResultCode::Ok;
        r.value = val;
        return r;
    }

    pub fn err(code: ResultCode) -> ResultU32 {
        let mut r: ResultU32 = 0;
        r.status = code;
        r.value = 0;
        return r;
    }

    pub fn is_ok(self: *const ResultU32) -> bool {
        if self == null {
            return false;
        }
        unsafe {
            return self.status == ResultCode::Ok;
        }
    }

    pub fn is_err(self: *const ResultU32) -> bool {
        if self == null {
            return true;
        }
        unsafe {
            return self.status != ResultCode::Ok;
        }
    }

    pub fn unwrap_or(self: *const ResultU32, default_val: u32) -> u32 {
        if self == null {
            return default_val;
        }
        unsafe {
            if self.status == ResultCode::Ok {
                return self.value;
            }
        }
        return default_val;
    }
}

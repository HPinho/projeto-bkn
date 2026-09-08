"""Normative guardrails for Sotlas raw-pointer, @system and C-ABI safety."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.sotlas_compile import bootstrap


def parse_check(source: str):
    module = bootstrap.parse(source, filename="<unsafe-ffi>")
    bootstrap.check(module)
    return module


class SotlasUnsafeBoundaryTests(unittest.TestCase):
    def test_system_function_is_not_implicitly_unsafe(self):
        source = """
module contract::unsafe_system;
@system
fn write(ptr: *mut u32) -> void {
    *ptr = 42;
}
"""
        with self.assertRaisesRegex(
            bootstrap.SotlasBootstrapError,
            "desreferenciamento de ponteiro cru exige bloco unsafe explícito",
        ):
            parse_check(source)

    def test_integer_to_raw_pointer_cast_requires_unsafe(self):
        source = """
module contract::bad_cast;
@system
fn write() -> void {
    let ptr: *mut u32 = 0xDEADBEEF as *mut u32;
}
"""
        with self.assertRaisesRegex(
            bootstrap.SotlasBootstrapError,
            "criação/conversão para ponteiro cru exige bloco unsafe explícito",
        ):
            parse_check(source)

    def test_raw_pointer_cast_and_deref_are_accepted_inside_unsafe(self):
        source = """
module contract::good_cast;
@system
fn write() -> void {
    unsafe {
        let ptr: *mut u32 = 0xDEADBEEF as *mut u32;
        *ptr = 42;
    }
}
"""
        parse_check(source)

    def test_null_raw_pointer_sentinel_does_not_require_unsafe(self):
        source = """
module contract::null_pointer;
fn none() -> *mut u8 {
    return null as *mut u8;
}
"""
        parse_check(source)

    def test_safe_wrapper_may_call_system_abstraction(self):
        source = """
module contract::system_wrapper;
@system
fn implementation() -> u32 { return 7; }
fn safe_wrapper() -> u32 { return implementation(); }
"""
        parse_check(source)

    def test_safe_layer_cannot_call_privileged_intrinsic_directly(self):
        source = """
module contract::system_intrinsic;
fn safe_layer() -> void { __hlt(); }
"""
        with self.assertRaisesRegex(
            bootstrap.SotlasBootstrapError,
            "intrínseco privilegiado exige função @system",
        ):
            parse_check(source)

    def test_safe_reference_deref_does_not_require_unsafe(self):
        source = """
module contract::safe_reference;
fn read(value: &u32) -> u32 { return *value; }
"""
        parse_check(source)


class SotlasCAbiTests(unittest.TestCase):
    def test_extern_c_single_declaration_parses_and_emits_prototype_only(self):
        source = """
module contract::ffi;
extern "C" fn foreign_sum(left: u32, right: u32) -> u32;
@system
pub fn call_sum(left: u32, right: u32) -> u32 {
    return foreign_sum(left, right);
}
"""
        module = parse_check(source)
        foreign = next(fn for fn in module.functions if fn.name == "foreign_sum")
        self.assertIn("@extern(C)", foreign.attributes)
        c = bootstrap.emit_c(module)
        self.assertIn("extern uint32_t foreign_sum(uint32_t left, uint32_t right);", c)
        self.assertNotIn("foreign_sum(uint32_t left, uint32_t right) {", c)

    def test_extern_c_call_requires_system_layer(self):
        source = """
module contract::ffi_safe_layer;
extern "C" fn foreign_tick() -> u64;
fn safe_layer() -> u64 { return foreign_tick(); }
"""
        with self.assertRaisesRegex(
            bootstrap.SotlasBootstrapError,
            'FFI extern "C" exige função @system',
        ):
            parse_check(source)

    def test_unsafe_extern_function_requires_unsafe_at_call_site(self):
        source = """
module contract::ffi_unsafe;
extern "C" {
    unsafe fn driver_map_mmio(base: u64) -> *mut u8;
}
@system
fn map(base: u64) -> *mut u8 {
    return driver_map_mmio(base);
}
"""
        with self.assertRaisesRegex(
            bootstrap.SotlasBootstrapError,
            "chamada FFI marcada unsafe exige bloco unsafe explícito",
        ):
            parse_check(source)

    def test_unsafe_extern_function_is_accepted_inside_unsafe(self):
        source = """
module contract::ffi_unsafe_ok;
extern "C" {
    unsafe fn driver_map_mmio(base: u64) -> *mut u8;
}
@system
fn map(base: u64) -> *mut u8 {
    unsafe { return driver_map_mmio(base); }
}
"""
        module = parse_check(source)
        foreign = next(fn for fn in module.functions if fn.name == "driver_map_mmio")
        self.assertIn("@unsafe", foreign.attributes)
        self.assertTrue(getattr(foreign.result, "_sotlas_foreign_pointer", False))

    def test_foreign_raw_pointer_stays_unsafe_after_return(self):
        source = """
module contract::ffi_pointer;
extern "C" {
    fn driver_buffer() -> *mut u8;
}
@system
fn read_first() -> u8 {
    let ptr = driver_buffer();
    return *ptr;
}
"""
        with self.assertRaisesRegex(
            bootstrap.SotlasBootstrapError,
            "desreferenciamento de ponteiro cru exige bloco unsafe explícito",
        ):
            parse_check(source)

    def test_only_c_abi_is_currently_stable(self):
        source = """
module contract::ffi_bad_abi;
extern "Objective-C" fn objc_msg_send() -> u64;
"""
        with self.assertRaisesRegex(
            bootstrap.SotlasBootstrapError,
            "ABI externa não suportada",
        ):
            bootstrap.parse(source, filename="<unsafe-ffi>")


if __name__ == "__main__":
    unittest.main()

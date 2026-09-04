#!/usr/bin/env python3
"""Contratos do lowering privilegiado x86-64 do Sotlas."""

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = ROOT / "tools" / "sotlas_compile" / "bootstrap.py"
EXT_PATH = ROOT / "tools" / "sotlas_compile" / "x86_intrinsics.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bootstrap = _load("baken_test_bootstrap_x86", BOOTSTRAP_PATH)
x86_intrinsics = _load("baken_test_x86_intrinsics", EXT_PATH)
x86_intrinsics.install(bootstrap)


class X86PrivilegedIntrinsicTests(unittest.TestCase):
    def test_signatures_are_registered(self):
        builtins = bootstrap.BUILTIN_FUNCTIONS
        self.assertEqual(builtins["__lgdt"].params[0][1].name, "u64")
        self.assertEqual(builtins["__lidt"].params[0][1].name, "u64")
        self.assertEqual(builtins["__gdt_activate_segments"].params[0][1].name, "u64")
        self.assertEqual(builtins["__gdt_activate_segments"].params[1][1].name, "u16")
        self.assertEqual(builtins["__gdt_activate_segments"].params[2][1].name, "u16")
        self.assertEqual(builtins["__gdt_activate_segments"].params[3][1].name, "u16")
        self.assertEqual(builtins["__lidt_table"].params[0][1].name, "u64")
        self.assertEqual(builtins["__lidt_table"].params[1][1].name, "u16")
        self.assertEqual(builtins["__ltr"].params[0][1].name, "u16")
        self.assertEqual(builtins["__read_cr2"].result.name, "u64")
        self.assertEqual(builtins["__read_cr3"].result.name, "u64")
        self.assertEqual(builtins["__write_cr3"].params[0][1].name, "u64")
        self.assertEqual(builtins["__write_cr3"].result.name, "void")
        self.assertEqual(builtins["__stack_switch_to_post_cutover"].params[0][1].name, "u64")
        self.assertEqual(builtins["__stack_switch_to_post_cutover"].params[1][1].name, "u64")
        self.assertEqual(builtins["__invlpg"].params[0][1].name, "u64")
        self.assertEqual(builtins["__exception_stub_address"].params[0][1].name, "u16")
        self.assertEqual(builtins["__exception_stub_address"].result.name, "u64")
        self.assertEqual(builtins["__irq_stub_address"].params[0][1].name, "u16")
        self.assertEqual(builtins["__irq_stub_address"].result.name, "u64")

    def test_preamble_contains_real_privileged_instructions(self):
        preamble = bootstrap.PREAMBLE
        self.assertIn('"lgdt (%0)"', preamble)
        self.assertIn('"lidt (%0)"', preamble)
        self.assertIn('"lgdt %0\\n\\t"', preamble)
        self.assertIn('"lretq\\n\\t"', preamble)
        self.assertIn('"lidt %0"', preamble)
        self.assertIn('"ltr %w0"', preamble)
        self.assertIn('"mov %%cr2, %0"', preamble)
        self.assertIn('"mov %%cr3, %0"', preamble)
        self.assertIn('"mov %0, %%cr3"', preamble)
        self.assertIn('"movq %rcx, %rsp\\n\\t"', preamble)
        self.assertIn('"invlpg (%0)"', preamble)
        self.assertIn('"iretq\\n\\t"', preamble)
        self.assertIn("static inline uint64_t __exception_stub_address", preamble)
        self.assertIn("static inline uint64_t __irq_stub_address", preamble)
        self.assertIn("sotlas_x86_irq_dispatch", preamble)

    def test_install_is_idempotent(self):
        x86_intrinsics.install(bootstrap)
        x86_intrinsics.install(bootstrap)
        self.assertEqual(
            bootstrap.PREAMBLE.count("SOTLAS_X86_64_PRIVILEGED_INTRINSICS"),
            1,
        )

    def test_system_function_can_typecheck_intrinsics(self):
        source = """
module kernel::arch::x86_64::intrinsic_fixture;

@system
pub fn exercise(gdt_base: u64, gdt_limit: u16, code: u16, data: u16,
                idt_base: u64, idt_limit: u16, page: u64, vector: u16,
                stack_top: u64, argument: u64) -> u64 {
    __gdt_activate_segments(gdt_base, gdt_limit, code, data);
    __lidt_table(idt_base, idt_limit);
    __ltr(data);
    let old_cr3: u64 = __read_cr3();
    __write_cr3(old_cr3);
    __invlpg(page);
    let stub: u64 = __exception_stub_address(vector);
    let irq_stub: u64 = __irq_stub_address(vector);
    if stack_top == 0 { __stack_switch_to_post_cutover(stack_top, argument); }
    if irq_stub != 0 { return irq_stub; }
    if stub != 0 { return stub; }
    return __read_cr2();
}
"""
        module = bootstrap.parse(source, filename="intrinsic_fixture.sotlas")
        bootstrap.check(module)
        generated = bootstrap.emit_c(module)
        self.assertIn("__gdt_activate_segments(gdt_base, gdt_limit, code, data)", generated)
        self.assertIn("__lidt_table(idt_base, idt_limit)", generated)
        self.assertIn("__ltr(data)", generated)
        self.assertIn("__read_cr3()", generated)
        self.assertIn("__write_cr3(old_cr3)", generated)
        self.assertIn("__stack_switch_to_post_cutover(stack_top, argument)", generated)
        self.assertIn("__invlpg(page)", generated)
        self.assertIn("__exception_stub_address(vector)", generated)
        self.assertIn("__irq_stub_address(vector)", generated)
        self.assertIn("__read_cr2()", generated)


if __name__ == "__main__":
    unittest.main()

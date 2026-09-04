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
        self.assertEqual(builtins["__ltr"].params[0][1].name, "u16")
        self.assertEqual(builtins["__read_cr2"].result.name, "u64")
        self.assertEqual(builtins["__invlpg"].params[0][1].name, "u64")

    def test_preamble_contains_real_privileged_instructions(self):
        preamble = bootstrap.PREAMBLE
        self.assertIn('"lgdt (%0)"', preamble)
        self.assertIn('"lidt (%0)"', preamble)
        self.assertIn('"ltr %w0"', preamble)
        self.assertIn('"mov %%cr2, %0"', preamble)
        self.assertIn('"invlpg (%0)"', preamble)

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
pub fn exercise(gdt: u64, idt: u64, selector: u16, page: u64) -> u64 {
    __lgdt(gdt);
    __lidt(idt);
    __ltr(selector);
    __invlpg(page);
    return __read_cr2();
}
"""
        module = bootstrap.parse(source, filename="intrinsic_fixture.sotlas")
        bootstrap.check(module)
        generated = bootstrap.emit_c(module)
        self.assertIn("__lgdt(gdt)", generated)
        self.assertIn("__lidt(idt)", generated)
        self.assertIn("__ltr(selector)", generated)
        self.assertIn("__invlpg(page)", generated)
        self.assertIn("__read_cr2()", generated)


if __name__ == "__main__":
    unittest.main()

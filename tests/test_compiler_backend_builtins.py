#!/usr/bin/env python3
"""Contratos entre o validador modular e os builtins registrados pelo backend."""

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPILER_PATH = ROOT / "tools/sotlas_compile/compiler.py"

spec = importlib.util.spec_from_file_location("baken_compiler_backend_builtin_test", COMPILER_PATH)
assert spec is not None and spec.loader is not None
compiler = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = compiler
spec.loader.exec_module(compiler)


class CompilerBackendBuiltinTests(unittest.TestCase):
    def _validate(self, source: str) -> None:
        ast = compiler.parse_module_ast(source)
        manifest = {"units": [{"module": ast.name, "imports": []}]}
        compiler.validate_module_interfaces({ast.name: ast}, manifest)

    def test_registered_cr3_builtin_is_callable_without_manual_whitelist(self):
        self._validate("""
module kernel::fixture;
@system
pub fn read_root() -> u64 {
    return __read_cr3();
}
""")

    def test_unknown_call_is_still_rejected(self):
        with self.assertRaises(compiler.SotlasError):
            self._validate("""
module kernel::fixture;
@system
pub fn broken() -> u64 {
    return __definitely_not_a_backend_builtin();
}
""")

    def test_validator_derives_backend_builtin_set(self):
        text = COMPILER_PATH.read_text(encoding="utf-8")
        self.assertIn("backend_builtins = set(_bootstrap_backend().BUILTIN_FUNCTIONS)", text)
        self.assertIn("language_calls.update(backend_builtins)", text)
        self.assertNotIn('"__read_cr3", "__write_cr3"', text)


if __name__ == "__main__":
    unittest.main()

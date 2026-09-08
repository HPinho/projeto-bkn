"""Guardrails that keep Sotlas on one production frontend."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import sotlas
import sotlas_compile


class SotlasFrontendUnificationTests(unittest.TestCase):
    def test_public_compile_source_matches_canonical_pipeline(self):
        source = """
module contract::canonical;
pub fn add(left: u32, right: u32) -> u32 {
    return left + right;
}
"""
        self.assertEqual(
            sotlas.compile_source(source, "<canonical>"),
            sotlas_compile.compile_source(source, "<canonical>"),
        )

    def test_historical_codegen_is_explicitly_named_legacy(self):
        self.assertTrue(callable(sotlas.compile_legacy_source))
        package_source = (ROOT / "tools" / "sotlas" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("def compile_legacy_source", package_source)
        self.assertIn("_canonical_compile_source", package_source)

    def test_cli_does_not_rebuild_legacy_lexer_parser_sema_pipeline(self):
        cli = (ROOT / "tools" / "sotlas" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("production_frontend.parse", cli)
        self.assertIn("production_frontend.check", cli)
        self.assertNotIn("from sotlas.parser import Parser", cli)
        self.assertNotIn("from sotlas.sema import Sema", cli)
        self.assertNotIn("tokens = Lexer(", cli)

    def test_baken_compiler_uses_same_bootstrap_package(self):
        compiler = (ROOT / "tools" / "sotlas_compile" / "compiler.py").read_text(encoding="utf-8")
        self.assertIn("from tools.sotlas_compile import bootstrap", compiler)
        package = (ROOT / "tools" / "sotlas_compile" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("compile_source = bootstrap.compile_source", package)


if __name__ == "__main__":
    unittest.main()
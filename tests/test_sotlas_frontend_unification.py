"""Guardrails that keep Sotlas on one production frontend."""
from pathlib import Path
import json
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

    def test_direct_compiler_bootstrap_installs_same_safety_pass(self):
        compiler = (ROOT / "tools" / "sotlas_compile" / "compiler.py").read_text(encoding="utf-8")
        extensions = (ROOT / "tools" / "sotlas_compile" / "frontend_extensions.py").read_text(encoding="utf-8")
        self.assertIn("frontend_extensions.install(bootstrap)", compiler)
        self.assertIn("install_language_safety(bootstrap)", extensions)
        self.assertIn("_LANGUAGE_SAFETY_INSTALLED", (ROOT / "tools" / "sotlas_compile" / "language_safety.py").read_text(encoding="utf-8"))

    def test_baken_compiler_uses_same_bootstrap_package(self):
        compiler = (ROOT / "tools" / "sotlas_compile" / "compiler.py").read_text(encoding="utf-8")
        self.assertIn("from tools.sotlas_compile import bootstrap", compiler)
        package = (ROOT / "tools" / "sotlas_compile" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("compile_source = bootstrap.compile_source", package)

    def test_baken_declares_exact_toolchain_contract(self):
        lock_path = ROOT / "toolchain" / "sotlas.lock.json"
        contract = json.loads(lock_path.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"], 1)
        self.assertEqual(contract["toolchain"], "sotlas")
        self.assertEqual(contract["source_kind"], "in-tree")
        self.assertEqual(contract["source_path"], "tools/sotlas_compile")
        self.assertIsNone(contract["repository"])
        self.assertIsNone(contract["revision"])
        self.assertEqual(contract["language_version"], sotlas.SOTLAS_LANG_VERSION)
        self.assertEqual(contract["compiler_api"], "canonical-v1")
        self.assertIn("extern-c", contract["required_features"])
        self.assertEqual(contract["compatibility_entry"], "kernel/src/main.sotlas")


if __name__ == "__main__":
    unittest.main()
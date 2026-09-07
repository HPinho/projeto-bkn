#!/usr/bin/env python3
"""Testes do resolvedor Sotlas: grafo real, import ausente e ciclos."""

import importlib.util
import json
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compiler", ROOT / "tools" / "sotlas_compile" / "compiler.py")
assert SPEC is not None and SPEC.loader is not None
sotlas_compile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sotlas_compile)


class SotlasResolverTests(unittest.TestCase):
    def fixture(self, name):
        return ROOT / "tests" / "fixtures" / "sotlas" / name / "kernel" / "src" / "main.sotlas"

    def test_configured_cross_compiler_is_honored(self):
        with patch.dict(os.environ, {"SOTLAS_CC": sys.executable}):
            self.assertEqual(sotlas_compile.find_gcc(ROOT), Path(sys.executable))

    def test_real_kernel_graph_has_single_entry_and_graphical_compositor(self):
        manifest = sotlas_compile.analyze(ROOT / "kernel/src/main.sotlas")
        self.assertEqual(manifest["entry"], "kernel::main")
        self.assertEqual(manifest["audited_modules"], len(manifest["compile_order"]))
        for module in (
            "kernel::desktop_compositor", "kernel::graphics_engine", "kernel::window_manager",
            "kernel::memory::pmm", "kernel::memory::memory_map_policy",
            "kernel::arch::x86_64::post_cutover", "kernel::drivers::pci_bus",
        ):
            self.assertIn(module, manifest["compile_order"])
        self.assertNotIn("kernel::memory::cutover_plan", manifest["compile_order"])
        self.assertGreaterEqual(len(manifest["compile_order"]), 6)
        self.assertEqual(manifest["unreachable_modules"], [])
        self.assertEqual(manifest["orphan_roots"], [])

    def test_missing_import_is_reported(self):
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(ROOT / "tests/fixtures/sotlas/missing/kernel/src/main.sotlas")

    def test_circular_import_is_reported(self):
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(ROOT / "tests/fixtures/sotlas/cycle/kernel/src/main.sotlas")

    def test_kernel_graph_requires_one_exported_entry(self):
        manifest = sotlas_compile.analyze(ROOT / "kernel/src/main.sotlas")
        self.assertIn("kernel::arch::x86_64::post_cutover::sotlas_x86_post_cutover_entry", manifest["exports"])

    def test_build_modular_compiles_kernel_objects(self):
        manifest = sotlas_compile.analyze(ROOT / "kernel/src/main.sotlas")
        result = sotlas_compile.build_modular(ROOT / "kernel/src/main.sotlas")
        module_count = len(manifest["compile_order"])
        self.assertIn("compiled_objects", result)
        # One object per module, plus compiler memory ABI and UEFI entry.
        self.assertEqual(len(result["compiled_objects"]), module_count + 2)
        objects = {Path(path).name for path in result["compiled_objects"]}
        self.assertIn("sotlas_freestanding_memory.o", objects)
        self.assertIn("uefi_bootloader.o", objects)
        self.assertEqual(len(result["generated_sources"]), module_count)
        self.assertEqual(len(result["generated_headers"]), module_count)
        self.assertTrue(all(Path(path).is_file() for path in result["generated_headers"]))
        self.assertEqual(len(result["generated_interfaces"]), module_count)
        main_interface = next(Path(path) for path in result["generated_interfaces"] if path.endswith("kernel__main.soti.json"))
        self.assertEqual(json.loads(main_interface.read_text(encoding="utf-8"))["module"], "kernel::main")
        graphics_c = next(Path(path) for path in result["generated_sources"] if path.endswith("kernel__graphics_engine.c"))
        self.assertIn("void display_init", graphics_c.read_text(encoding="utf-8"))
        self.assertNotIn("bridge_runtime", result)

    def test_self_import_is_reported(self):
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(self.fixture("self_import"))

    def test_module_cannot_hide_c_preprocessor_directives(self):
        units = {"kernel::bad": {"path": ROOT / "kernel/src/bad.sotlas", "text": "module kernel::bad;\n#include <stdio.h>\n"}}
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.validate_module_dialect(units, ROOT)

    def test_module_file_cannot_declare_two_modules(self):
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(self.fixture("two_modules"))

    def test_import_must_target_an_entire_module_with_wildcard(self):
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(self.fixture("bad_import"))

    def test_kernel_route_rejects_two_exported_entries(self):
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(self.fixture("two_entries"))

    def test_ast_parsing_and_typechecking(self):
        source = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
        ast = sotlas_compile.parse_module_ast(source)
        self.assertEqual(ast.name, "kernel::main")
        for module in ("kernel::graphics_engine", "kernel::desktop_compositor", "kernel::memory::pmm", "kernel::memory::memory_map_policy", "kernel::drivers::pci_bus"):
            self.assertIn(module, ast.imports)
        self.assertNotIn("kernel::memory::cutover_plan", ast.imports)
        self.assertEqual(ast.functions, [])
        post_source = (ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas").read_text(encoding="utf-8")
        post_ast = sotlas_compile.parse_module_ast(post_source)
        entry_fn = next(f for f in post_ast.functions if f.name == "sotlas_x86_post_cutover_entry")
        self.assertIn("@export", entry_fn.attributes)
        self.assertIn("@system", entry_fn.attributes)
        self.assertEqual(entry_fn.return_type.name, "!")
        self.assertTrue(sotlas_compile.typecheck_ast(ast))

    def test_typechecker_rejects_unknown_signature_type(self):
        ast = sotlas_compile.parse_module_ast("module kernel::bad;\npub fn run(value: MissingType) -> void { }\n")
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.typecheck_ast(ast)

    def test_ui_parser_collects_public_dock_fields(self):
        source = (ROOT / "kernel/src/baken_ui_oop.sotlas").read_text(encoding="utf-8")
        ast = sotlas_compile.parse_module_ast(source)
        dock = next((item for item in ast.structs if item.name == "DesktopDock"), None)
        self.assertIsNotNone(dock)
        self.assertTrue(dock.is_pub)
        self.assertTrue(any(field.name == "item_count" for field in dock.fields))

    def test_interface_checker_rejects_unknown_function_call(self):
        ast = sotlas_compile.parse_module_ast("module kernel::bad;\npub fn run() -> void { missing_call(); }\n")
        manifest = {"units": [{"module": "kernel::bad", "imports": []}]}
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.validate_module_interfaces({"kernel::bad": ast}, manifest)


if __name__ == "__main__": unittest.main()

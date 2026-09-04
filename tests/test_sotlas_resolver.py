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
        manifest = sotlas_compile.analyze(ROOT / "kernel" / "src" / "main.sotlas")
        self.assertEqual(manifest["entry"], "kernel::main")
        self.assertEqual(manifest["audited_modules"], len(manifest["compile_order"]))
        self.assertIn("kernel::desktop_compositor", manifest["compile_order"])
        self.assertGreaterEqual(len(manifest["compile_order"]), 6)
        self.assertIn("kernel::graphics_engine", manifest["compile_order"])
        self.assertIn("kernel::window_manager", manifest["compile_order"])
        self.assertIn("kernel::memory::pmm", manifest["compile_order"])
        self.assertIn("kernel::memory::cutover_plan", manifest["compile_order"])
        self.assertIn("kernel::drivers::pci_bus", manifest["compile_order"])
        self.assertEqual(manifest["unreachable_modules"], [])
        self.assertEqual(manifest["orphan_roots"], [])

    def test_missing_import_is_reported(self):
        source = ROOT / "tests" / "fixtures" / "sotlas" / "missing" / "kernel" / "src" / "main.sotlas"
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(source)

    def test_circular_import_is_reported(self):
        source = ROOT / "tests" / "fixtures" / "sotlas" / "cycle" / "kernel" / "src" / "main.sotlas"
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(source)

    def test_kernel_graph_requires_one_exported_entry(self):
        manifest = sotlas_compile.analyze(ROOT / "kernel" / "src" / "main.sotlas")
        self.assertIn("kernel::main::baken_kernel_main", manifest["exports"])

    def test_build_modular_compiles_kernel_objects(self):
        manifest = sotlas_compile.analyze(ROOT / "kernel" / "src" / "main.sotlas")
        result = sotlas_compile.build_modular(ROOT / "kernel" / "src" / "main.sotlas")
        module_count = len(manifest["compile_order"])
        self.assertIn("compiled_objects", result)
        self.assertEqual(len(result["compiled_objects"]), module_count + 1)
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
        source = ROOT / "tests" / "fixtures" / "sotlas" / "self_import" / "kernel" / "src" / "main.sotlas"
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.analyze(source)

    def test_module_cannot_hide_c_preprocessor_directives(self):
        units = {
            "kernel::bad": {
                "path": ROOT / "kernel" / "src" / "bad.sotlas",
                "text": "module kernel::bad;\n#include <stdio.h>\n",
            }
        }
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
        source = (ROOT / "kernel" / "src" / "main.sotlas").read_text(encoding="utf-8")
        ast = sotlas_compile.parse_module_ast(source)
        self.assertEqual(ast.name, "kernel::main")
        self.assertIn("kernel::graphics_engine", ast.imports)
        self.assertIn("kernel::desktop_compositor", ast.imports)
        self.assertIn("kernel::memory::pmm", ast.imports)
        self.assertIn("kernel::memory::cutover_plan", ast.imports)
        self.assertIn("kernel::drivers::pci_bus", ast.imports)

        boot_info_struct = next((s for s in ast.structs if s.name == "BakenBootInfo"), None)
        self.assertIsNotNone(boot_info_struct)
        self.assertTrue(boot_info_struct.is_pub)
        self.assertEqual(
            [field.name for field in boot_info_struct.fields],
            [
                "framebuffer_base", "framebuffer_size", "screen_width", "screen_height",
                "pixels_per_scanline", "memory_map_base", "memory_map_size", "system_table",
                "pointer_protocol", "block_io_protocol", "install_target_block_io_protocol",
                "version", "struct_size", "flags", "memory_descriptor_size",
                "memory_descriptor_version", "pixel_format", "acpi_rsdp",
                "page_table_arena_physical_base", "page_table_arena_virtual_base",
                "page_table_arena_page_count",
                "loaded_image_physical_base", "loaded_image_virtual_base", "loaded_image_size",
                "transition_stack_physical_base", "transition_stack_virtual_base",
                "transition_stack_page_count",
            ],
        )

        main_fn = next((f for f in ast.functions if f.name == "baken_kernel_main"), None)
        self.assertIsNotNone(main_fn)
        self.assertTrue(main_fn.is_pub)
        self.assertIn("@export", main_fn.attributes)
        self.assertIn("@system", main_fn.attributes)
        self.assertEqual(main_fn.return_type.name, "!")
        self.assertTrue(sotlas_compile.typecheck_ast(ast))

    def test_typechecker_rejects_unknown_signature_type(self):
        ast = sotlas_compile.parse_module_ast(
            "module kernel::bad;\npub fn run(value: MissingType) -> void { }\n"
        )
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.typecheck_ast(ast)

    def test_ui_parser_collects_public_dock_fields(self):
        source = (ROOT / "kernel" / "src" / "baken_ui_oop.sotlas").read_text(encoding="utf-8")
        ast = sotlas_compile.parse_module_ast(source)
        dock = next((item for item in ast.structs if item.name == "DesktopDock"), None)
        self.assertIsNotNone(dock)
        self.assertTrue(dock.is_pub)
        self.assertTrue(any(field.name == "item_count" for field in dock.fields))

    def test_interface_checker_rejects_unknown_function_call(self):
        ast = sotlas_compile.parse_module_ast(
            "module kernel::bad;\npub fn run() -> void { missing_call(); }\n"
        )
        manifest = {"units": [{"module": "kernel::bad", "imports": []}]}
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.validate_module_interfaces({"kernel::bad": ast}, manifest)


if __name__ == "__main__":
    unittest.main()

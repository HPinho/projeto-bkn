#!/usr/bin/env python3
"""Testes do resolvedor Sotlas: grafo real, import ausente e ciclos."""

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compiler", ROOT / "tools" / "sotlas_compile" / "compiler.py")
assert SPEC is not None and SPEC.loader is not None
sotlas_compile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sotlas_compile)


class SotlasResolverTests(unittest.TestCase):
    def fixture(self, name):
        return ROOT / "tests" / "fixtures" / "sotlas" / name / "kernel" / "src" / "main.sotlas"

    def test_real_kernel_graph_has_single_entry_and_graphical_compositor(self):
        manifest = sotlas_compile.analyze(ROOT / "kernel" / "src" / "main.sotlas")
        self.assertEqual(manifest["entry"], "kernel::main")
        self.assertEqual(manifest["audited_modules"], len(manifest["compile_order"]))
        self.assertIn("kernel::desktop_compositor", manifest["compile_order"])
        # A entrada inicial deve ser pequena e verific├ível: framebuffer,
        # rasteriza├º├úo, shell e compositor. Drivers incompletos n├úo pertencem
        # ao grafo at├® que tenham testes de hardware/I-O.
        self.assertGreaterEqual(len(manifest["compile_order"]), 6)
        self.assertIn("kernel::graphics_engine", manifest["compile_order"])
        self.assertIn("kernel::window_manager", manifest["compile_order"])
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

    def test_build_modular_compiles_and_links_kernel_objects(self):
        output = ROOT / "build" / "test_modular_bootx64.efi"
        result = sotlas_compile.build_modular(ROOT / "kernel" / "src" / "main.sotlas", output)
        self.assertIn("compiled_objects", result)
        self.assertEqual(len(result["compiled_objects"]), 15)
        self.assertEqual(len(result["generated_sources"]), 14)
        self.assertEqual(len(result["generated_headers"]), 14)
        self.assertTrue(all(Path(path).is_file() for path in result["generated_headers"]))
        self.assertEqual(len(result["generated_interfaces"]), 14)
        main_interface = next(Path(path) for path in result["generated_interfaces"] if path.endswith("kernel__main.soti.json"))
        self.assertEqual(json.loads(main_interface.read_text(encoding="utf-8"))["module"], "kernel::main")
        graphics_c = next(Path(path) for path in result["generated_sources"] if path.endswith("kernel__graphics_engine.c"))
        self.assertIn("void gfx_init", graphics_c.read_text(encoding="utf-8"))
        self.assertNotIn("bridge_runtime", result)
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 1000)
        output.unlink(missing_ok=True)

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
        
        # Verifica struct BakenBootInfo
        boot_info_struct = next((s for s in ast.structs if s.name == "BakenBootInfo"), None)
        self.assertIsNotNone(boot_info_struct)
        self.assertTrue(boot_info_struct.is_pub)
        self.assertGreaterEqual(len(boot_info_struct.fields), 7)
        self.assertEqual(
            [field.name for field in boot_info_struct.fields],
            ["framebuffer_base", "framebuffer_size", "screen_width", "screen_height",
             "pixels_per_scanline", "memory_map_base", "memory_map_size", "system_table",
             "pointer_protocol", "block_io_protocol", "install_target_block_io_protocol"],
        )
        
        # Verifica fun├º├úo baken_kernel_main
        main_fn = next((f for f in ast.functions if f.name == "baken_kernel_main"), None)
        self.assertIsNotNone(main_fn)
        self.assertTrue(main_fn.is_pub)
        self.assertIn("@export", main_fn.attributes)
        self.assertIn("@system", main_fn.attributes)
        self.assertEqual(main_fn.return_type.name, "!")
        
        # Valida├º├úo de tipos
        self.assertTrue(sotlas_compile.typecheck_ast(ast))

    def test_typechecker_rejects_unknown_signature_type(self):
        ast = sotlas_compile.parse_module_ast(
            "module kernel::bad;\npub fn run(value: MissingType) -> void { }\n"
        )
        with self.assertRaisesRegex(sotlas_compile.SotlasError, ".+"):
            sotlas_compile.typecheck_ast(ast)

    def test_class_parser_collects_public_class_fields(self):
        source = (ROOT / "kernel" / "src" / "baken_ui_oop.sotlas").read_text(encoding="utf-8")
        ast = sotlas_compile.parse_module_ast(source)
        dock = next((item for item in ast.classes if item.name == "DesktopDock"), None)
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

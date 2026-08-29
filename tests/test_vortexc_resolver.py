#!/usr/bin/env python3
"""Testes do resolvedor Cq: grafo real, import ausente e ciclos."""

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vortexc", ROOT / "tools" / "vortexc" / "vortexc.py")
vortexc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vortexc)


class VortexResolverTests(unittest.TestCase):
    def fixture(self, name):
        return ROOT / "tests" / "fixtures" / "vortexc" / name / "kernel" / "src" / "main.cq"

    def test_real_kernel_graph_has_single_entry_and_graphical_compositor(self):
        manifest = vortexc.analyze(ROOT / "kernel" / "src" / "main.cq")
        self.assertEqual(manifest["entry"], "kernel::main")
        self.assertEqual(manifest["audited_modules"], len(manifest["compile_order"]))
        self.assertIn("kernel::desktop_compositor", manifest["compile_order"])
        # A entrada inicial deve ser pequena e verificável: framebuffer,
        # rasterização, shell e compositor. Drivers incompletos não pertencem
        # ao grafo até que tenham testes de hardware/I-O.
        self.assertGreaterEqual(len(manifest["compile_order"]), 6)
        self.assertIn("kernel::graphics_engine", manifest["compile_order"])
        self.assertIn("kernel::window_manager", manifest["compile_order"])
        self.assertEqual(manifest["unreachable_modules"], [])
        self.assertEqual(manifest["orphan_roots"], [])

    def test_missing_import_is_reported(self):
        source = ROOT / "tests" / "fixtures" / "vortexc" / "missing" / "kernel" / "src" / "main.cq"
        with self.assertRaisesRegex(vortexc.CqError, "import não resolvido"):
            vortexc.analyze(source)

    def test_circular_import_is_reported(self):
        source = ROOT / "tests" / "fixtures" / "vortexc" / "cycle" / "kernel" / "src" / "main.cq"
        with self.assertRaisesRegex(vortexc.CqError, "dependência circular"):
            vortexc.analyze(source)

    def test_kernel_graph_requires_one_exported_entry(self):
        manifest = vortexc.analyze(ROOT / "kernel" / "src" / "main.cq")
        self.assertIn("kernel::main::baken_kernel_main", manifest["exports"])

    def test_build_modular_compiles_and_links_kernel_objects(self):
        output = ROOT / "build" / "test_modular_bootx64.efi"
        result = vortexc.build_modular(ROOT / "kernel" / "src" / "main.cq", output)
        self.assertIn("compiled_objects", result)
        self.assertEqual(len(result["compiled_objects"]), 9)
        self.assertEqual(len(result["generated_sources"]), 8)
        self.assertEqual(len(result["generated_headers"]), 8)
        self.assertTrue(all(Path(path).is_file() for path in result["generated_headers"]))
        self.assertEqual(len(result["generated_interfaces"]), 8)
        main_interface = next(Path(path) for path in result["generated_interfaces"] if path.endswith("kernel__main.cqi.json"))
        self.assertEqual(json.loads(main_interface.read_text(encoding="utf-8"))["module"], "kernel::main")
        graphics_c = next(Path(path) for path in result["generated_sources"] if path.endswith("kernel__graphics_engine.c"))
        self.assertIn("void gfx_init", graphics_c.read_text(encoding="utf-8"))
        self.assertNotIn("bridge_runtime", result)
        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 1000)
        output.unlink(missing_ok=True)

    def test_self_import_is_reported(self):
        source = ROOT / "tests" / "fixtures" / "vortexc" / "self_import" / "kernel" / "src" / "main.cq"
        with self.assertRaisesRegex(vortexc.CqError, "importar a si mesmo"):
            vortexc.analyze(source)

    def test_module_cannot_hide_c_preprocessor_directives(self):
        units = {
            "kernel::bad": {
                "path": ROOT / "kernel" / "src" / "bad.cq",
                "text": "module kernel::bad;\n#include <stdio.h>\n",
            }
        }
        with self.assertRaisesRegex(vortexc.CqError, "pré-processador C"):
            vortexc.validate_module_dialect(units, ROOT)

    def test_module_file_cannot_declare_two_modules(self):
        with self.assertRaisesRegex(vortexc.CqError, "exatamente um módulo"):
            vortexc.analyze(self.fixture("two_modules"))

    def test_import_must_target_an_entire_module_with_wildcard(self):
        with self.assertRaisesRegex(vortexc.CqError, "import Cq inválido"):
            vortexc.analyze(self.fixture("bad_import"))

    def test_kernel_route_rejects_two_exported_entries(self):
        with self.assertRaisesRegex(vortexc.CqError, "símbolo exportado duas vezes|exatamente um baken_kernel_main"):
            vortexc.analyze(self.fixture("two_entries"))

    def test_ast_parsing_and_typechecking(self):
        source = (ROOT / "kernel" / "src" / "main.cq").read_text(encoding="utf-8")
        ast = vortexc.parse_module_ast(source)
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
        
        # Verifica função baken_kernel_main
        main_fn = next((f for f in ast.functions if f.name == "baken_kernel_main"), None)
        self.assertIsNotNone(main_fn)
        self.assertTrue(main_fn.is_pub)
        self.assertIn("@export", main_fn.attributes)
        self.assertIn("@system", main_fn.attributes)
        self.assertEqual(main_fn.return_type.name, "!")
        
        # Validação de tipos
        self.assertTrue(vortexc.typecheck_ast(ast))

    def test_typechecker_rejects_unknown_signature_type(self):
        ast = vortexc.parse_module_ast(
            "module kernel::bad;\npub fn run(value: MissingType) -> void { }\n"
        )
        with self.assertRaisesRegex(vortexc.CqError, "tipo desconhecido"):
            vortexc.typecheck_ast(ast)

    def test_class_parser_collects_public_class_fields(self):
        source = (ROOT / "kernel" / "src" / "baken_ui_oop.cq").read_text(encoding="utf-8")
        ast = vortexc.parse_module_ast(source)
        dock = next((item for item in ast.classes if item.name == "DesktopDock"), None)
        self.assertIsNotNone(dock)
        self.assertTrue(dock.is_pub)
        self.assertTrue(any(field.name == "item_count" for field in dock.fields))

    def test_interface_checker_rejects_unknown_function_call(self):
        ast = vortexc.parse_module_ast(
            "module kernel::bad;\npub fn run() -> void { missing_call(); }\n"
        )
        manifest = {"units": [{"module": "kernel::bad", "imports": []}]}
        with self.assertRaisesRegex(vortexc.CqError, "chamada não resolvida"):
            vortexc.validate_module_interfaces({"kernel::bad": ast}, manifest)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Testes de integridade do SOTLAS Graphics Core (Fase 1)."""

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("compiler", ROOT / "tools" / "sotlas_compile" / "compiler.py")
assert SPEC is not None and SPEC.loader is not None
sotlas_compile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sotlas_compile)


class SotlasGraphicsCoreTests(unittest.TestCase):
    def test_sotlas_graphics_module_parses_cleanly(self):
        source_path = ROOT / "kernel" / "src" / "sotlas_graphics.sotlas"
        self.assertTrue(source_path.is_file())
        source = source_path.read_text(encoding="utf-8")
        ast = sotlas_compile.parse_module_ast(source)
        self.assertEqual(ast.name, "kernel::sotlas_graphics")

        # Verifica estruturas fundamentais (Fase 1 e Fase 2)
        struct_names = {s.name for s in ast.structs}
        for expected in ("Point", "Rect", "Color", "Paint", "Surface", "ClipState", "CanvasState", "Canvas", "LinearGradient", "Bitmap"):
            self.assertIn(expected, struct_names, f"Estrutura {expected} ausente no AST")

        # Verifica funções e métodos do Canvas e Renderer
        fn_names = {f.name for f in ast.functions}
        for expected_fn in (
            "color_rgba", "color_from_u32", "color_to_u32",
            "rect_make", "Rect_contains", "Rect_intersect",
            "paint_fill", "paint_stroke",
            "linear_gradient_make", "bitmap_make",
            "surface_from_buffer", "surface_from_backbuffer",
            "Canvas_init", "Canvas_save", "Canvas_restore", "Canvas_translate", "Canvas_scale_milli",
            "Canvas_clip_rect", "Canvas_clear", "Canvas_draw_rect",
            "Canvas_draw_round_rect", "Canvas_draw_capsule", "Canvas_draw_squircle",
            "Canvas_draw_circle", "Canvas_draw_oval", "Canvas_draw_linear_gradient",
            "Canvas_draw_bitmap", "Canvas_draw_text", "Canvas_draw_image",
            "Canvas_draw_vector_icon"
        ):
            self.assertIn(expected_fn, fn_names, f"Função {expected_fn} ausente no AST de sotlas_graphics")

    def test_compositor_integrates_sotlas_canvas(self):
        compositor_source = (ROOT / "kernel" / "src" / "desktop_compositor.sotlas").read_text(encoding="utf-8")
        self.assertIn("import kernel::sotlas_graphics::*;", compositor_source)
        self.assertIn("ROOT_CANVAS: Canvas", compositor_source)
        self.assertIn("ROOT_SURFACE: Surface", compositor_source)
        self.assertIn("pub fn compositor_get_canvas() -> *mut Canvas", compositor_source)
        self.assertIn("Canvas_init(&mut ROOT_CANVAS, &mut ROOT_SURFACE);", compositor_source)

    def test_main_imports_sotlas_graphics(self):
        main_source = (ROOT / "kernel" / "src" / "main.sotlas").read_text(encoding="utf-8")
        self.assertIn("import kernel::sotlas_graphics::*;", main_source)

    def test_sotlas_graphics_has_zero_gfx_calls(self):
        source = (ROOT / "kernel" / "src" / "sotlas_graphics.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("gfx_", source, "sotlas_graphics.sotlas ainda contém chamadas procedurais gfx_!")


if __name__ == "__main__":
    unittest.main()

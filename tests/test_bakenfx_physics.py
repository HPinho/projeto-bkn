"""Testes unitários para o motor físico contínuo e infraestrutura avançada do BakenFx."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class BakenFxPhysicsTests(unittest.TestCase):
    def setUp(self):
        self.bakenfx = (ROOT / "kernel/src/bakenfx.sotlas").read_text(encoding="utf-8")
        self.sotlas_ui = (ROOT / "kernel/src/sotlas_ui.sotlas").read_text(encoding="utf-8")

    def test_anim_state_and_physical_interruptions_exist(self):
        self.assertIn("pub struct AnimState", self.bakenfx)
        self.assertIn("pub fn bakenfx_anim_init", self.bakenfx)
        self.assertIn("pub fn bakenfx_anim_configure_material", self.bakenfx)
        self.assertIn("pub fn bakenfx_interrupt_and_redirect", self.bakenfx)
        self.assertIn("pub fn bakenfx_tick_spring_physics", self.bakenfx)

    def test_simd_blur_and_premium_panel_exist(self):
        self.assertIn("pub fn bakenfx_blur_backdrop_simd", self.bakenfx)
        self.assertIn("pub fn bakenfx_draw_premium_panel", self.bakenfx)
        self.assertIn("BAKENFX_CORNER_CURVE_CONTINUOUS", self.bakenfx)

    def test_magnetic_cursor_state_and_dispatch_exist(self):
        self.assertIn("pub struct MagneticCursorState", self.bakenfx)
        self.assertIn("pub fn bakenfx_magnetic_cursor_init", self.bakenfx)
        self.assertIn("pub fn bakenfx_magnetic_cursor_tick", self.bakenfx)
        self.assertIn("pub fn bakenfx_cursor_update_pointer", self.bakenfx)
        self.assertIn("pub fn bakenfx_draw_magnetic_cursor", self.bakenfx)
        self.assertIn("pub fn bakenfx_hittest_rect", self.bakenfx)

    def test_liquid_progress_bar_with_wave_distortion_exists(self):
        self.assertIn("pub struct LiquidProgressBarState", self.bakenfx)
        self.assertIn("pub fn bakenfx_liquid_progress_init", self.bakenfx)
        self.assertIn("pub fn bakenfx_liquid_progress_set", self.bakenfx)
        self.assertIn("pub fn bakenfx_liquid_progress_tick", self.bakenfx)
        self.assertIn("pub fn bakenfx_draw_liquid_progress_bar", self.bakenfx)

    def test_scene_render_tree_hit_test_dispatcher_exists(self):
        self.assertIn("RenderTree_hittest_magnetic_cursor", self.sotlas_ui)
        self.assertIn("NODE_BUTTON", self.sotlas_ui)


if __name__ == "__main__":
    unittest.main()

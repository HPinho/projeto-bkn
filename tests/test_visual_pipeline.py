import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VisualPipelineTests(unittest.TestCase):
    def test_gop_mode_cannot_keep_an_unbuffered_4k_default(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertIn("uint64_t best_area = 0", boot)
        self.assertIn("found_budget_mode", boot)
        self.assertIn("HorizontalResolution <= 1920", boot)
        self.assertIn("VerticalResolution <= 1200", boot)

    def test_runtime_uses_real_frame_time_and_not_cpu_dependent_spin_delay(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        self.assertIn("cycles_per_us", compiler)
        self.assertIn("desktop_shell_set_frame_delta(frame_dt)", compiler)
        self.assertIn("frame_stall(16667u - work_us)", compiler)
        self.assertNotIn("for (volatile int d = 0; d < 40000; ++d)", compiler)

    def test_expensive_background_and_blur_are_bounded(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        self.assertIn("g_wallpaper_cache", compiler)
        self.assertIn("janela deslizante", compiler)
        self.assertIn("estritamente O(w*h)", compiler)

    def test_installer_and_oobe_have_continuous_transitions(self):
        installer = (ROOT / "kernel/src/baken_installer.sotlas").read_text(encoding="utf-8")
        oobe = (ROOT / "kernel/src/baken_oobe_screen.sotlas").read_text(encoding="utf-8")
        self.assertIn("installer_go_to", installer)
        self.assertIn("transition_tick", installer)
        self.assertIn("gfx_smoothstep_u8", installer)
        self.assertIn("oobe_go_to", oobe)
        self.assertIn("transition_tick", oobe)
        self.assertIn("gfx_smoothstep_u8", oobe)

    def test_resampling_and_springs_tolerate_fractional_scale_and_slow_frames(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        animation = (ROOT / "kernel/src/baken_animation.sotlas").read_text(encoding="utf-8")
        rasterizer = (ROOT / "kernel/src/baken_rasterizer.sotlas").read_text(encoding="utf-8")
        self.assertIn("BKN_BILERP_CH", compiler)
        self.assertIn("bilerp_channel", rasterizer)
        self.assertIn("safe_dt", animation)
        self.assertIn("ease_smooth_surface", animation)


if __name__ == "__main__":
    unittest.main()

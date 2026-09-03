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
        runtime = (ROOT / "kernel/src/baken_runtime.sotlas").read_text(encoding="utf-8")
        self.assertIn("CYCLES_PER_US", runtime.upper())
        self.assertIn("desktop_shell_set_frame_delta(dt)", runtime)
        self.assertIn("1000000 / refresh_hz as u64", runtime)
        self.assertNotIn("for (volatile int d = 0; d < 40000; ++d)", runtime)

    def test_runtime_supports_simple_and_absolute_uefi_pointers(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        runtime = (ROOT / "kernel/src/baken_runtime.sotlas").read_text(encoding="utf-8")
        simple = boot.index("LocateProtocol(&EFI_SIMPLE_POINTER_PROTOCOL_GUID")
        absolute = boot.index("LocateProtocol(&EFI_ABSOLUTE_POINTER_PROTOCOL_GUID")
        self.assertLess(simple, absolute)
        self.assertIn("EfiSimplePointerState", runtime)
        self.assertIn("EfiAbsolutePointerState", runtime)
        self.assertIn("LocateProtocol(&G_ABSOLUTE_GUID", runtime)
        self.assertIn("raw_x > range_x", runtime)

    def test_background_is_a_static_bakenfx_composition(self):
        bakenfx = (ROOT / "kernel/src/bakenfx.sotlas").read_text(encoding="utf-8")
        shell = (ROOT / "kernel/src/desktop_shell.sotlas").read_text(encoding="utf-8")
        installer = (ROOT / "kernel/src/baken_installer.sotlas").read_text(encoding="utf-8")
        self.assertIn("bakenfx_draw_desktop_background", bakenfx)
        self.assertIn("bakenfx_draw_desktop_background", shell)
        self.assertIn("bakenfx_draw_desktop_background", installer)
        self.assertNotIn("raster_draw_mesh_wallpaper();", shell)
        self.assertNotIn("raster_draw_aurora_parallax_bg", installer)

    def test_installer_and_oobe_have_continuous_transitions(self):
        installer = (ROOT / "kernel/src/baken_installer.sotlas").read_text(encoding="utf-8")
        oobe = (ROOT / "kernel/src/baken_oobe_screen.sotlas").read_text(encoding="utf-8")
        self.assertIn("installer_go_to", installer)
        self.assertIn("transition_tick", installer)
        self.assertIn("raster_smoothstep_u8", installer)
        self.assertIn("oobe_go_to", oobe)
        self.assertIn("transition_tick", oobe)
        self.assertIn("raster_smoothstep_u8", oobe)

    def test_resampling_and_springs_tolerate_fractional_scale_and_slow_frames(self):
        animation = (ROOT / "kernel/src/baken_animation.sotlas").read_text(encoding="utf-8")
        rasterizer = (ROOT / "kernel/src/baken_rasterizer.sotlas").read_text(encoding="utf-8")
        self.assertIn("bilerp_channel", rasterizer)
        self.assertIn("safe_dt", animation)
        self.assertIn("ease_smooth_surface", animation)

    def test_visual_fixes_are_connected_to_the_executable_route(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        main = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
        shell = (ROOT / "kernel/src/desktop_shell.sotlas").read_text(encoding="utf-8")
        dock = (ROOT / "kernel/src/baken_ui_oop.sotlas").read_text(encoding="utf-8")
        windows = (ROOT / "kernel/src/window_manager.sotlas").read_text(encoding="utf-8")

        # Firmware escolhe o modo antes do handoff; não é apenas um helper órfão.
        self.assertIn("choose_high_density_gop_mode(gop, bs);", boot)
        # Efeitos otimizados são chamados pelo material e pelo frame do shell.
        self.assertIn("baken_runtime_init_assets();", main)
        self.assertIn("baken_runtime_run(", main)
        self.assertIn("bakenfx_draw_desktop_background", shell)
        # O dt medido alcança as molas do dock e o installer é despachado pelo WM.
        self.assertIn("desktop_shell_update(SHELL.frame_delta)", shell)
        self.assertIn("dock_update(&mut MAIN_DOCK, dt", shell)
        self.assertIn("spring_update(&mut (*dock).item_springs", dock)
        self.assertIn("baken_installer_render(content_x, content_y", windows)

    def test_ui_routes_use_bakenfx_not_the_pixel_backend(self):
        for name in (
            "desktop_shell.sotlas", "window_manager.sotlas", "baken_materials.sotlas",
            "app_files.sotlas", "app_notes.sotlas", "app_settings.sotlas", "app_terminal.sotlas",
        ):
            source = (ROOT / "kernel/src" / name).read_text(encoding="utf-8")
            self.assertIn("bakenfx", source, name)
            self.assertNotIn("raster_", source, name)

    def test_baken_design_defines_shared_accessibility_and_material_tokens(self):
        design = (ROOT / "kernel/src/baken_design.sotlas").read_text(encoding="utf-8")
        self.assertIn("BAKEN_MIN_HIT_TARGET", design)
        self.assertIn("BAKEN_MIN_TEXT_CONTRAST", design)
        self.assertIn("baken_material_glass_dark", design)
        self.assertIn("BAKEN_MOTION_STANDARD_MS", design)


if __name__ == "__main__":
    unittest.main()

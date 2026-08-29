#!/usr/bin/env python3
"""Regressões de arquitetura e segurança do MVP Baken OS."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class LegacySafetyTests(unittest.TestCase):
    CANONICAL_CQ_MODULES = {
        "kernel/src/main.cq",
        "kernel/src/graphics_engine.cq",
        "kernel/src/baken_rasterizer.cq",
        "kernel/src/baken_animation.cq",
        "kernel/src/baken_ui_oop.cq",
        "kernel/src/window_manager.cq",
        "kernel/src/desktop_shell.cq",
        "kernel/src/desktop_compositor.cq",
    }

    def test_cq_tree_contains_only_the_canonical_desktop_route(self):
        discovered = {
            path.relative_to(ROOT).as_posix()
            for root in (ROOT / "kernel", ROOT / "libbkn", ROOT / "boot", ROOT / "apps")
            if root.is_dir()
            for path in root.rglob("*.cq")
            if "module " in path.read_text(encoding="utf-8")
        }
        self.assertEqual(discovered, self.CANONICAL_CQ_MODULES)

    def test_no_unlinked_cq_test_module_remains(self):
        for path in (ROOT / "tests").rglob("*.cq"):
            self.assertIn("fixtures", path.parts, path)

    def test_active_uefi_bridge_clips_and_does_not_display_fake_telemetry(self):
        bridge = source("kernel/src/baken_kernel_all.c")
        self.assertIn("g_framebuffer_width", bridge)
        self.assertIn("g_framebuffer_height", bridge)
        self.assertIn("_Static_assert(sizeof(BakenFsHeader) == 512", bridge)
        self.assertIn("g_left_button_down", bridge)
        self.assertIn("storage_can_read", bridge)
        self.assertIn("bakenfs_mount", bridge)
        self.assertIn("bakenfs_save_notes", bridge)
        self.assertNotIn("INSTALL1", bridge)
        self.assertIn("x == 7 || ((row >> (6 - x))", bridge)
        self.assertNotIn("hal_init_all", bridge)
        self.assertNotIn("0b", bridge)
        self.assertNotIn("CPU: Ryzen 7", bridge)
        self.assertNotIn("Teresina, Piaui", bridge)
        self.assertNotIn("Hardware Live Monitor", bridge)
        self.assertNotIn("Q-HAL AI", bridge)
        self.assertIn("static SystemMode g_current_mode = MODE_LIVE_DESKTOP;", bridge)
        self.assertNotIn('"Hiago"', bridge)
        self.assertNotIn("bakenfs_mount_root", bridge)
        build = source("tools/build_uefi_desktop.ps1")
        self.assertIn("vortex build", build)
        self.assertNotIn("baken_kernel_all.c", build)

    def test_uefi_handoff_has_one_shared_contract(self):
        header = source("kernel/include/baken_boot_info.h")
        bridge = source("kernel/src/baken_kernel_all.c")
        bootloader = source("boot/uefi_bootloader.cq")
        self.assertIn("_Static_assert(sizeof(BakenBootInfo) == 80", header)
        self.assertIn("install_target_block_io_protocol", header)
        self.assertIn('#include "baken_boot_info.h"', bridge)
        self.assertIn('#include "baken_boot_info.h"', bootloader)
        self.assertIn("PIXEL_BLUE_GREEN_RED_RESERVED_8BIT_PER_COLOR", bootloader)
        self.assertIn("PixelsPerScanLine >=", bootloader)
        self.assertIn("return EFI_UNSUPPORTED;", bootloader)
        self.assertIn("return EFI_ABORTED;", bootloader)
        self.assertIn("find_install_target", bootloader)
        self.assertIn("install_target_block_io_protocol = install_target", bootloader)
        self.assertNotIn('"hlt"', bootloader)

    def test_cmake_delegates_build_to_the_cq_backend(self):
        cmake = source("CMakeLists.txt")
        self.assertIn("project(BakenEcosystem LANGUAGES NONE)", cmake)
        self.assertIn("add_custom_target(cq_check", cmake)
        self.assertIn("add_custom_target(cq_build", cmake)
        self.assertIn("vortexc.py", cmake)
        self.assertNotIn("add_library(baken_qhal", cmake)
        self.assertNotIn("qhal_reference", cmake)

    def test_there_is_one_cq_editor_definition_without_quantum_tooling(self):
        legacy_extension = ROOT / "tools/vscode-bkn"
        self.assertFalse(
            any(path.is_file() for path in legacy_extension.rglob("*"))
            if legacy_extension.exists() else False
        )
        package = source("tools/vscode-cq/package.json")
        self.assertIn('"name": "baken-cq"', package)
        self.assertNotIn("Quantum", package)
        grammar = source("spec/cq_grammar.ebnf")
        self.assertIn("contrato de módulos do MVP", grammar)
        self.assertNotIn("QuantumFunctionDeclaration", grammar)
        self.assertNotIn("QuantumStatement", grammar)

    def test_obsolete_parallel_ui_documentation_is_absent(self):
        self.assertFalse((ROOT / "docs/baken_os_developer_guide.md").exists())
        self.assertFalse((ROOT / "spec/baken_ui_framework_spec.md").exists())

    def test_orphaned_cq_contracts_are_absent(self):
        stale_contracts = (
            "kernel/include/baken_kernel.cqh",
            "kernel/include/bkn_font.cqh",
            "kernel/include/syscall.cqh",
            "kernel/qhal/quantum_simulator.cqh",
        )
        for relative in stale_contracts:
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_removed_subsystem_specs_and_quantum_test_harness_are_absent(self):
        obsolete_specs = (
            "spec/baken_app_engine.md", "spec/baken_audio_spec.md",
            "spec/baken_font_and_animation_spec.md", "spec/baken_net_spec.md",
            "spec/baken_peripherals_spec.md", "spec/baken_shell_spec.md",
            "spec/bakenfs_spec.md", "spec/bakenfx_graphics_api.md",
            "spec/grammar.ebnf", "tests/test_quantum_simulator.cq",
            "tools/scripts/test_quantum_suite.py",
        )
        for relative in obsolete_specs:
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main()

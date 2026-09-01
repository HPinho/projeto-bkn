#!/usr/bin/env python3
"""Regressões de arquitetura e identidade da rota Sotlas."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LegacySafetyTests(unittest.TestCase):
    CANONICAL_SOTLAS_MODULES = {
        "kernel/src/main.sotlas",
        "kernel/src/graphics_engine.sotlas",
        "kernel/src/baken_rasterizer.sotlas",
        "kernel/src/baken_animation.sotlas",
        "kernel/src/baken_ui_oop.sotlas",
        "kernel/src/window_manager.sotlas",
        "kernel/src/desktop_shell.sotlas",
        "kernel/src/desktop_compositor.sotlas",
        "kernel/src/app_files.sotlas",
        "kernel/src/app_notes.sotlas",
        "kernel/src/app_settings.sotlas",
        "kernel/src/app_terminal.sotlas",
        "kernel/src/app_about.sotlas",
    }

    def test_sotlas_tree_contains_only_the_canonical_desktop_route(self):
        discovered = {
            path.relative_to(ROOT).as_posix()
            for root in (ROOT / "kernel", ROOT / "libbkn", ROOT / "boot", ROOT / "apps")
            if root.is_dir()
            for path in root.rglob("*.sotlas")
            if "module " in path.read_text(encoding="utf-8")
        }
        self.assertEqual(discovered, self.CANONICAL_SOTLAS_MODULES)

    def test_no_unlinked_sotlas_test_module_remains(self):
        for path in (ROOT / "tests").rglob("*.sotlas"):
            self.assertIn("fixtures", path.parts, path)

    def test_sotlas_toolchain_and_vscode_extension_are_canonical(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        extension = (ROOT / "tools/vscode-sotlas/package.json").read_text(encoding="utf-8")
        self.assertIn("class SotlasError", compiler)
        self.assertIn("tools/sotlas_compile/compiler.py", cmake)
        self.assertIn('".sotlas"', extension)
        self.assertIn('".sth"', extension)
        self.assertIn('"icon": "./icons/sotlas-icon.svg"', extension)
        self.assertTrue((ROOT / "tools/vscode-sotlas/icons/sotlas-icon.svg").is_file())
        self.assertTrue((ROOT / "tools/vscode-sotlas/icons/sotlas-logo.svg").is_file())

    def test_uefi_handoff_uses_one_shared_contract(self):
        header = (ROOT / "kernel/include/baken_boot_info.h").read_text(encoding="utf-8")
        bootloader = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertIn("_Static_assert(sizeof(BakenBootInfo) == 80", header)
        self.assertIn('#include "baken_boot_info.h"', bootloader)
        self.assertIn("return EFI_UNSUPPORTED;", bootloader)
        self.assertIn("return EFI_ABORTED;", bootloader)


if __name__ == "__main__":
    unittest.main()

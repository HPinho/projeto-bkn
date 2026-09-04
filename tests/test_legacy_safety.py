#!/usr/bin/env python3
"""Regressões de arquitetura e identidade da rota Sotlas."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LegacySafetyTests(unittest.TestCase):
    CANONICAL_SOTLAS_MODULES = {
        "kernel/src/main.sotlas", "kernel/src/graphics_engine.sotlas",
        "kernel/src/baken_rasterizer.sotlas", "kernel/src/baken_animation.sotlas",
        "kernel/src/baken_materials.sotlas", "kernel/src/baken_cursor.sotlas",
        "kernel/src/baken_i18n.sotlas", "kernel/src/baken_runtime.sotlas",
        "kernel/src/baken_native_runtime.sotlas", "kernel/src/baken_ui_oop.sotlas",
        "kernel/src/window_manager.sotlas", "kernel/src/desktop_shell.sotlas",
        "kernel/src/desktop_compositor.sotlas", "kernel/src/app_files.sotlas",
        "kernel/src/app_notes.sotlas", "kernel/src/app_settings.sotlas",
        "kernel/src/app_terminal.sotlas", "kernel/src/app_about.sotlas",
        "kernel/src/baken_installer.sotlas", "kernel/src/install_engine.sotlas",
        "kernel/src/baken_oobe_screen.sotlas", "kernel/src/sotlas_graphics.sotlas",
        "kernel/src/sotlas_ui.sotlas", "kernel/src/bakenfx.sotlas",
        "kernel/src/baken_design.sotlas", "kernel/src/acpi/tables.sotlas",
        "kernel/src/acpi/madt.sotlas", "kernel/src/acpi/mcfg.sotlas",
        "kernel/src/acpi/hpet.sotlas", "kernel/src/acpi/fadt.sotlas",
        "kernel/src/acpi/pm_timer.sotlas", "kernel/src/interrupts/route.sotlas",
        "kernel/src/drivers/display_driver.sotlas",
        "kernel/src/drivers/pci_bus.sotlas", "kernel/src/drivers/storage_discovery.sotlas",
        "kernel/src/drivers/xhci_discovery.sotlas", "kernel/src/drivers/xhci_ring.sotlas",
        "kernel/src/drivers/xhci_trb.sotlas", "kernel/src/drivers/xhci_event.sotlas",
        "kernel/src/drivers/xhci_erst.sotlas", "kernel/src/drivers/xhci_event_ring.sotlas",
        "kernel/src/drivers/i8042.sotlas", "kernel/src/drivers/ps2_mouse.sotlas",
        "kernel/src/drivers/ps2_keyboard.sotlas",
        "kernel/src/storage/block_device.sotlas", "kernel/src/storage/gpt.sotlas",
        "kernel/src/storage/fat32.sotlas", "kernel/src/storage/crc32.sotlas",
        "kernel/src/memory/pmm.sotlas", "kernel/src/memory/pmm_allocator.sotlas",
        "kernel/src/memory/vmm.sotlas", "kernel/src/memory/memory_map_policy.sotlas",
        "kernel/src/memory/direct_map.sotlas", "kernel/src/memory/direct_map_ranges.sotlas",
        "kernel/src/memory/page_table_arena.sotlas", "kernel/src/memory/page_table_writer.sotlas",
        "kernel/src/memory/page_table_mapper.sotlas", "kernel/src/memory/page_table_builder.sotlas",
        "kernel/src/memory/transition_map.sotlas", "kernel/src/memory/transition_stack.sotlas",
        "kernel/src/memory/transition_stack_map.sotlas", "kernel/src/memory/pe_image.sotlas",
        "kernel/src/memory/pe_wx_policy.sotlas", "kernel/src/memory/transition_image_map.sotlas",
        "kernel/src/memory/transition_image_wx.sotlas", "kernel/src/memory/transition_page_tables.sotlas",
        "kernel/src/memory/mmu_activate.sotlas", "kernel/src/memory/cutover_plan.sotlas",
        "kernel/src/memory/dma.sotlas",
        "kernel/src/arch/x86_64/gdt.sotlas", "kernel/src/arch/x86_64/tss.sotlas",
        "kernel/src/arch/x86_64/idt.sotlas", "kernel/src/arch/x86_64/cpu.sotlas",
        "kernel/src/arch/x86_64/paging.sotlas", "kernel/src/arch/x86_64/pat.sotlas",
        "kernel/src/arch/x86_64/timer.sotlas", "kernel/src/arch/x86_64/exceptions.sotlas",
    }

    def test_sotlas_tree_contains_only_known_canonical_modules(self):
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

    def test_uefi_handoff_uses_one_shared_versioned_contract(self):
        header = (ROOT / "kernel/include/baken_boot_info.h").read_text(encoding="utf-8")
        bootloader = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertIn("BAKEN_BOOT_INFO_VERSION 2U", header)
        self.assertIn("offsetof(BakenBootInfo, version) == 80", header)
        self.assertIn("offsetof(BakenBootInfo, page_table_arena_physical_base) == 120", header)
        self.assertIn("offsetof(BakenBootInfo, loaded_image_physical_base) == 144", header)
        self.assertIn("offsetof(BakenBootInfo, transition_stack_physical_base) == 168", header)
        self.assertIn("_Static_assert(sizeof(BakenBootInfo) == 192", header)
        self.assertIn('#include "baken_boot_info.h"', bootloader)
        self.assertIn("boot_info.version = BAKEN_BOOT_INFO_VERSION", bootloader)
        self.assertIn("return EFI_UNSUPPORTED;", bootloader)
        self.assertIn("return EFI_ABORTED;", bootloader)

    def test_kernel_has_zero_gfx_occurrences(self):
        kernel_src = ROOT / "kernel" / "src"
        files = list(kernel_src.glob("*.sotlas")) + list(kernel_src.glob("*.c"))
        offenders = {}
        for f in files:
            content = f.read_text(encoding="utf-8", errors="ignore")
            count = content.count("gfx_")
            if count > 0:
                offenders[f.name] = count
        self.assertEqual(offenders, {}, f"Ainda existem chamadas gfx_ no kernel: {offenders}")

if __name__ == "__main__":
    unittest.main()

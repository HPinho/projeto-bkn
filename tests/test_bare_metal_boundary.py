#!/usr/bin/env python3
"""Guardrails for the Baken OS migration from UEFI runtime to bare metal."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BareMetalBoundaryTests(unittest.TestCase):
    def test_architecture_declares_uefi_bootstrap_only(self):
        text = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        self.assertIn("UEFI é apenas bootstrap", text)
        self.assertIn("ExitBootServices()", text)
        self.assertIn("O compilador não desenha o sistema operacional", text)

    def test_final_bootinfo_contract_forbids_runtime_uefi_pointers(self):
        text = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        section = text.split("## BootInfo alvo", 1)[1].split("## Fundação x86-64", 1)[0]
        for token in (
            "EFI_SYSTEM_TABLE*",
            "EFI_SIMPLE_POINTER_PROTOCOL*",
            "EFI_ABSOLUTE_POINTER_PROTOCOL*",
            "EFI_BLOCK_IO_PROTOCOL*",
            "EFI_BOOT_SERVICES*",
        ):
            with self.subTest(token=token):
                self.assertIn(token, section)

    def test_bootinfo_v2_has_versioned_bare_metal_metadata(self):
        header = (ROOT / "kernel/include/baken_boot_info.h").read_text(encoding="utf-8")
        for token in (
            "BAKEN_BOOT_INFO_VERSION 2U",
            "struct_size",
            "memory_descriptor_size",
            "memory_descriptor_version",
            "pixel_format",
            "acpi_rsdp",
            "page_table_arena_physical_base",
            "page_table_arena_virtual_base",
            "page_table_arena_page_count",
            "BAKEN_BOOT_INFO_FLAG_MEMORY_MAP_VALID",
            "BAKEN_BOOT_INFO_FLAG_ACPI_RSDP_VALID",
            "BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID",
        ):
            with self.subTest(token=token):
                self.assertIn(token, header)

    def test_bootinfo_v2_preserves_legacy_offsets_during_transition(self):
        header = (ROOT / "kernel/include/baken_boot_info.h").read_text(encoding="utf-8")
        for assertion in (
            "offsetof(BakenBootInfo, framebuffer_base) == 0",
            "offsetof(BakenBootInfo, memory_map_base) == 32",
            "offsetof(BakenBootInfo, system_table) == 48",
            "offsetof(BakenBootInfo, install_target_block_io_protocol) == 72",
            "offsetof(BakenBootInfo, version) == 80",
            "offsetof(BakenBootInfo, acpi_rsdp) == 112",
            "offsetof(BakenBootInfo, page_table_arena_physical_base) == 120",
            "offsetof(BakenBootInfo, page_table_arena_virtual_base) == 128",
            "offsetof(BakenBootInfo, page_table_arena_page_count) == 136",
            "sizeof(BakenBootInfo) == 144",
        ):
            with self.subTest(assertion=assertion):
                self.assertIn(assertion, header)

    def test_sotlas_entry_mirrors_and_validates_bootinfo_v2(self):
        main = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
        for field in (
            "version: u32",
            "struct_size: u32",
            "flags: u64",
            "memory_descriptor_size: u64",
            "memory_descriptor_version: u32",
            "pixel_format: u32",
            "acpi_rsdp: *const u8",
            "page_table_arena_physical_base: u64",
            "page_table_arena_virtual_base: *mut u8",
            "page_table_arena_page_count: u64",
        ):
            with self.subTest(field=field):
                self.assertIn(field, main)
        self.assertIn("baken_bootinfo_v2_valid", main)
        self.assertIn("boot_info.version != 2", main)
        self.assertIn("boot_info.struct_size < 120", main)
        self.assertIn("boot_info.struct_size < 144", main)
        self.assertIn("BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID", main)
        self.assertIn("import kernel::memory::pmm::*;", main)
        self.assertIn("pmm_inventory_init", main)

    def test_pmm_inventory_parses_real_uefi_descriptors_without_allocating(self):
        pmm = (ROOT / "kernel/src/memory/pmm.sotlas").read_text(encoding="utf-8")
        for token in (
            "pub struct EfiMemoryDescriptor",
            "descriptor_size < 40",
            "EFI_CONVENTIONAL_MEMORY",
            "largest_conventional_base",
            "highest_physical_address",
            "pmm_inventory_init",
        ):
            with self.subTest(token=token):
                self.assertIn(token, pmm)
        self.assertNotRegex(pmm, r"pub\s+fn\s+pmm_(?:alloc|free)")
        self.assertIn("NAO aloca paginas ainda", pmm)

    def test_display_backend_reports_only_real_capabilities(self):
        display = (ROOT / "kernel/src/drivers/display_driver.sotlas").read_text(encoding="utf-8")
        self.assertIn("is_hardware_accelerated: false", display)
        self.assertIn("framebuffer_wc_active: false", display)
        self.assertIn("display_driver_promote_hardware_backend", display)
        self.assertIn("Vendor ID isolado nao basta", display)
        self.assertNotIn("__wrmsr(0x0277", display)
        self.assertNotIn("0x0007010600070106", display)
        self.assertNotIn("pci_scan_all();", display)
        self.assertNotRegex(display, r"vendor_id\s*==\s*0x(?:8086|1002|10DE|1AF4).*is_hardware_accelerated\s*=\s*true")

    def test_bootloader_populates_real_v2_platform_metadata(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        for token in (
            "capture_memory_map",
            "EFI_BUFFER_TOO_SMALL",
            "GetMemoryMap",
            "memory_descriptor_size",
            "memory_descriptor_version",
            "find_acpi_rsdp",
            "BAKEN_BOOT_INFO_FLAG_MEMORY_MAP_VALID",
            "BAKEN_BOOT_INFO_FLAG_ACPI_RSDP_VALID",
            "boot_info.version = BAKEN_BOOT_INFO_VERSION",
        ):
            with self.subTest(token=token):
                self.assertIn(token, boot)

    def test_bootloader_labels_uefi_bridge_as_transitional(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertIn("BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE", boot)
        self.assertIn("Ainda não chamamos ExitBootServices", boot)

    def test_compiler_remains_host_tool_not_ui_runtime(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        forbidden = {
            "wallpaper": r"\bwallpaper\b",
            "dock": r"\bdock\b",
            "shimmer": r"\bshimmer\b",
            "installer UI": r"\binstaller_(?:screen|ui)\b",
            "OOBE UI": r"\boobe_(?:screen|ui)\b",
        }
        for label, pattern in forbidden.items():
            with self.subTest(label=label):
                self.assertIsNone(re.search(pattern, compiler, re.IGNORECASE))

    @unittest.expectedFailure
    def test_bootloader_has_completed_exit_boot_services_cutover(self):
        """Flip to a normal test once native input/storage replace UEFI bridges."""
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE", boot)
        self.assertNotIn("pointer_protocol", boot)
        self.assertNotIn("block_io_protocol", boot)
        self.assertNotIn("system_table", boot)
        self.assertRegex(boot, r"ExitBootServices\s*\(")


if __name__ == "__main__":
    unittest.main()

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
            "loaded_image_physical_base",
            "loaded_image_virtual_base",
            "loaded_image_size",
            "transition_stack_physical_base",
            "transition_stack_virtual_base",
            "transition_stack_page_count",
            "BAKEN_BOOT_INFO_FLAG_MEMORY_MAP_VALID",
            "BAKEN_BOOT_INFO_FLAG_ACPI_RSDP_VALID",
            "BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID",
            "BAKEN_BOOT_INFO_FLAG_LOADED_IMAGE_VALID",
            "BAKEN_BOOT_INFO_FLAG_TRANSITION_STACK_VALID",
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
            "offsetof(BakenBootInfo, loaded_image_physical_base) == 144",
            "offsetof(BakenBootInfo, loaded_image_virtual_base) == 152",
            "offsetof(BakenBootInfo, loaded_image_size) == 160",
            "offsetof(BakenBootInfo, transition_stack_physical_base) == 168",
            "offsetof(BakenBootInfo, transition_stack_virtual_base) == 176",
            "offsetof(BakenBootInfo, transition_stack_page_count) == 184",
            "sizeof(BakenBootInfo) == 192",
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
            "loaded_image_physical_base: u64",
            "loaded_image_virtual_base: *mut u8",
            "loaded_image_size: u64",
            "transition_stack_physical_base: u64",
            "transition_stack_virtual_base: *mut u8",
            "transition_stack_page_count: u64",
        ):
            with self.subTest(field=field):
                self.assertIn(field, main)
        self.assertIn("baken_bootinfo_v2_valid", main)
        self.assertIn("boot_info.version != 2", main)
        self.assertIn("boot_info.struct_size < 120", main)
        self.assertIn("boot_info.struct_size < 144", main)
        self.assertIn("boot_info.struct_size < 192", main)
        self.assertIn("BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID", main)
        self.assertIn("BAKEN_BOOT_INFO_FLAG_LOADED_IMAGE_VALID", main)
        self.assertIn("BAKEN_BOOT_INFO_FLAG_TRANSITION_STACK_VALID", main)
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

    def test_bootloader_reserves_cutover_resources_before_memory_map_snapshot(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        for token in (
            "reserve_page_table_arena",
            "capture_loaded_image",
            "reserve_transition_stack",
            "EFI_LOADED_IMAGE_PROTOCOL_GUID",
            "BAKEN_BOOT_INFO_FLAG_LOADED_IMAGE_VALID",
            "BAKEN_BOOT_INFO_FLAG_TRANSITION_STACK_VALID",
        ):
            with self.subTest(token=token):
                self.assertIn(token, boot)
        self.assertLess(boot.index("reserve_page_table_arena(bs, &boot_info)"), boot.index("capture_memory_map(bs,"))
        self.assertLess(boot.index("capture_loaded_image(bs, ImageHandle, &boot_info)"), boot.index("capture_memory_map(bs,"))
        self.assertLess(boot.index("reserve_transition_stack(bs, &boot_info)"), boot.index("capture_memory_map(bs,"))

    def test_transition_mapper_keeps_physical_and_virtual_addresses_separate(self):
        transition = (ROOT / "kernel/src/memory/transition_map.sotlas").read_text(encoding="utf-8")
        self.assertIn("pub fn transition_map_range", transition)
        self.assertIn("virtual_address: u64", transition)
        self.assertIn("physical_address: u64", transition)
        self.assertIn("virtual_cursor", transition)
        self.assertIn("physical_cursor", transition)
        self.assertIn("page_table_map_4k(arena, root, virtual_cursor, physical_cursor, clean_flags)", transition)
        self.assertIn("return transition_map_range(arena, root, address, address, size, flags);", transition)
        self.assertNotIn("write_cr3", transition)

    def test_bootloader_executes_real_cutover_without_transporting_runtime_bridge(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("boot_info.flags = BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE", boot)
        self.assertIn("boot_info.flags = 0;", boot)
        for assignment in (
            "boot_info.system_table =",
            "boot_info.pointer_protocol =",
            "boot_info.block_io_protocol =",
            "boot_info.install_target_block_io_protocol =",
        ):
            with self.subTest(assignment=assignment):
                self.assertNotIn(assignment, boot)
        self.assertIn("baken_exit_boot_services_final(", boot)
        self.assertIn("baken_prepare_cutover_from_final_map", boot)
        self.assertIn("x86_stack_switch_to_post_cutover_raw(", boot)
        self.assertNotIn("baken_kernel_main(&boot_info);", boot)

    def test_transition_resources_remain_metadata_only_in_hybrid_entry(self):
        main = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
        self.assertIn("continuam apenas como metadados", main)
        self.assertNotIn("write_cr3(", main)
        self.assertNotIn("transition_map_identity_range(", main)
        self.assertNotIn("transition_map_range(", main)

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
    def test_bootloader_has_removed_all_transitional_uefi_bridge_fields(self):
        """Passará quando a descoberta UEFI transitória também for removida do loader."""
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE", boot)
        self.assertNotIn("pointer_protocol", boot)
        self.assertNotIn("block_io_protocol", boot)
        self.assertNotIn("system_table", boot)


if __name__ == "__main__":
    unittest.main()

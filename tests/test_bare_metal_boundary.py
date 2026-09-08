#!/usr/bin/env python3
"""Guardrails for the Baken OS UEFI-bootstrap / bare-metal boundary."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class BareMetalBoundaryTests(unittest.TestCase):
    def test_architecture_declares_uefi_bootstrap_only(self):
        text = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        self.assertIn("UEFI é apenas bootstrap", text)
        self.assertIn("ExitBootServices()", text)
        self.assertIn("O compilador não desenha o sistema operacional", text)

    def test_final_bootinfo_contract_forbids_runtime_uefi_pointers(self):
        text = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        section = text.split("## BootInfo alvo", 1)[1].split("## Fundação x86-64", 1)[0]
        for token in ("EFI_SYSTEM_TABLE*", "EFI_SIMPLE_POINTER_PROTOCOL*", "EFI_ABSOLUTE_POINTER_PROTOCOL*", "EFI_BLOCK_IO_PROTOCOL*", "EFI_BOOT_SERVICES*"):
            self.assertIn(token, section)

    def test_bootinfo_v2_has_versioned_bare_metal_metadata(self):
        header = (ROOT / "kernel/include/baken_boot_info.h").read_text(encoding="utf-8")
        for token in ("BAKEN_BOOT_INFO_VERSION 2U", "struct_size", "memory_descriptor_size", "memory_descriptor_version", "pixel_format", "acpi_rsdp", "page_table_arena_physical_base", "page_table_arena_virtual_base", "page_table_arena_page_count", "loaded_image_physical_base", "loaded_image_virtual_base", "loaded_image_size", "transition_stack_physical_base", "transition_stack_virtual_base", "transition_stack_page_count", "BAKEN_BOOT_INFO_FLAG_MEMORY_MAP_VALID", "BAKEN_BOOT_INFO_FLAG_ACPI_RSDP_VALID", "BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID", "BAKEN_BOOT_INFO_FLAG_LOADED_IMAGE_VALID", "BAKEN_BOOT_INFO_FLAG_TRANSITION_STACK_VALID"):
            self.assertIn(token, header)

    def test_bootinfo_v2_preserves_abi_offsets_without_legacy_names(self):
        header = (ROOT / "kernel/include/baken_boot_info.h").read_text(encoding="utf-8")
        for assertion in ("offsetof(BakenBootInfo, framebuffer_base) == 0", "offsetof(BakenBootInfo, memory_map_base) == 32", "offsetof(BakenBootInfo, reserved_abi_0) == 48", "offsetof(BakenBootInfo, reserved_abi_1) == 56", "offsetof(BakenBootInfo, reserved_abi_2) == 64", "offsetof(BakenBootInfo, reserved_abi_3) == 72", "offsetof(BakenBootInfo, version) == 80", "offsetof(BakenBootInfo, acpi_rsdp) == 112", "offsetof(BakenBootInfo, page_table_arena_physical_base) == 120", "offsetof(BakenBootInfo, page_table_arena_virtual_base) == 128", "offsetof(BakenBootInfo, page_table_arena_page_count) == 136", "offsetof(BakenBootInfo, loaded_image_physical_base) == 144", "offsetof(BakenBootInfo, loaded_image_virtual_base) == 152", "offsetof(BakenBootInfo, loaded_image_size) == 160", "offsetof(BakenBootInfo, transition_stack_physical_base) == 168", "offsetof(BakenBootInfo, transition_stack_virtual_base) == 176", "offsetof(BakenBootInfo, transition_stack_page_count) == 184", "sizeof(BakenBootInfo) == 192"):
            self.assertIn(assertion, header)
        self.assertNotIn("reserved_legacy_", header)

    def test_post_cutover_context_contains_only_stable_handoff_data(self):
        header = (ROOT / "kernel/include/baken_boot_info.h").read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        struct = post.split("pub struct PostCutoverContext {", 1)[1].split("}", 1)[0]
        self.assertNotIn("BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE", header)
        for forbidden in ("system_table", "pointer_protocol", "block_io_protocol", "install_target_block_io_protocol", "BootServices", "RuntimeServices", "reserved_abi_"):
            self.assertNotIn(forbidden, struct)
        for required in ("root_physical", "stack_top", "framebuffer_base", "framebuffer_size", "screen_width", "screen_height", "pixels_per_scanline", "memory_map_base", "memory_map_size", "memory_descriptor_size", "acpi_rsdp", "page_table_arena_physical_base", "page_table_arena_page_count", "page_table_pages_used", "valid"):
            self.assertIn(required, struct)

    def test_post_cutover_entry_validates_and_activates_native_foundations(self):
        post = POST.read_text(encoding="utf-8")
        for token in ("pub fn post_cutover_context_valid", "post_cutover_memory_map_virtual(context)", "post_cutover_acpi_rsdp_virtual(context)", "x86_mmu_activate_root(snapshot.root_physical)", "pmm_inventory_init(", "pmm_allocator_activate_after_exit_boot_services()", "vmm_activate_current_tables(snapshot.root_physical, BAKEN_DIRECT_MAP_BASE)", "acpi_init_post_cutover(rsdp)", "baken_native_kernel_run("):
            self.assertIn(token, post)

    def test_pmm_inventory_uses_baken_owned_boot_descriptors_without_allocating(self):
        pmm = (ROOT / "kernel/src/memory/pmm.sotlas").read_text(encoding="utf-8")
        for token in ("pub struct BootMemoryDescriptor", "descriptor_size < 40", "BAKEN_BOOT_MEMORY_CONVENTIONAL", "largest_conventional_base", "highest_physical_address", "pmm_inventory_init"):
            self.assertIn(token, pmm)
        code = "\n".join(line.split("//", 1)[0] for line in pmm.splitlines())
        for forbidden in ("EfiMemoryDescriptor", "EFI_", "uefi_", "BootServices", "RuntimeServices"):
            self.assertNotIn(forbidden, code)
        self.assertNotRegex(pmm, r"pub\s+fn\s+pmm_(?:alloc|free)")

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
        for token in ("capture_memory_map", "EFI_BUFFER_TOO_SMALL", "GetMemoryMap", "memory_descriptor_size", "memory_descriptor_version", "find_acpi_rsdp", "BAKEN_BOOT_INFO_FLAG_MEMORY_MAP_VALID", "BAKEN_BOOT_INFO_FLAG_ACPI_RSDP_VALID", "boot_info.version = BAKEN_BOOT_INFO_VERSION"):
            self.assertIn(token, boot)

    def test_bootloader_reserves_cutover_resources_before_memory_map_snapshot(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        for token in ("reserve_page_table_arena", "capture_loaded_image", "reserve_transition_stack", "EFI_LOADED_IMAGE_PROTOCOL_GUID", "BAKEN_BOOT_INFO_FLAG_LOADED_IMAGE_VALID", "BAKEN_BOOT_INFO_FLAG_TRANSITION_STACK_VALID"):
            self.assertIn(token, boot)
        self.assertLess(boot.index("reserve_page_table_arena(bs, &boot_info)"), boot.index("capture_memory_map(bs,"))
        self.assertLess(boot.index("capture_loaded_image(bs, ImageHandle, &boot_info)"), boot.index("capture_memory_map(bs,"))
        self.assertLess(boot.index("reserve_transition_stack(bs, &boot_info)"), boot.index("capture_memory_map(bs,"))

    def test_transition_mapper_keeps_physical_and_virtual_addresses_separate(self):
        transition = (ROOT / "kernel/src/memory/transition_map.sotlas").read_text(encoding="utf-8")
        for token in ("pub fn transition_map_range", "virtual_address: u64", "physical_address: u64", "virtual_cursor", "physical_cursor", "page_table_map_4k(arena, root, virtual_cursor, physical_cursor, clean_flags)", "return transition_map_range(arena, root, address, address, size, flags);"):
            self.assertIn(token, transition)
        self.assertNotIn("write_cr3", transition)

    def test_bootloader_executes_real_cutover_without_transporting_runtime_bridge(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("boot_info.flags = BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE", boot)
        self.assertIn("boot_info.flags = 0;", boot)
        for assignment in ("boot_info.system_table =", "boot_info.pointer_protocol =", "boot_info.block_io_protocol =", "boot_info.install_target_block_io_protocol ="):
            self.assertNotIn(assignment, boot)
        self.assertIn("baken_exit_boot_services_final(", boot)
        self.assertIn("baken_prepare_cutover_from_final_map", boot)
        self.assertIn("x86_stack_switch_to_post_cutover_raw(", boot)
        self.assertNotIn("baken_kernel_main(&boot_info);", boot)

    def test_main_is_graph_root_and_post_cutover_owns_privileged_activation(self):
        main = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::arch::x86_64::post_cutover::*;", main)
        self.assertNotIn("baken_kernel_main", main)
        self.assertNotIn("write_cr3(", main)
        self.assertNotIn("transition_map_identity_range(", main)
        self.assertIn("x86_mmu_activate_root(snapshot.root_physical)", post)
        self.assertIn("x86_gdt_activate_segments_raw(", post)
        self.assertIn("x86_lidt_table_raw(", post)

    def test_compiler_remains_host_tool_not_ui_runtime(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        forbidden = {"wallpaper": r"\bwallpaper\b", "dock": r"\bdock\b", "shimmer": r"\bshimmer\b", "installer UI": r"\binstaller_(?:screen|ui)\b", "OOBE UI": r"\boobe_(?:screen|ui)\b"}
        for label, pattern in forbidden.items(): self.assertIsNone(re.search(pattern, compiler, re.IGNORECASE), label)

    def test_bootloader_has_removed_transitional_input_and_storage_protocols(self):
        boot = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        for forbidden in ("BAKEN_BOOT_INFO_FLAG_UEFI_BRIDGE_ACTIVE", "EFI_SIMPLE_POINTER_PROTOCOL_GUID", "EFI_ABSOLUTE_POINTER_PROTOCOL_GUID", "EFI_BLOCK_IO_PROTOCOL_GUID", "EFI_BLOCK_IO_PROTOCOL", "find_pointer_protocol", "find_boot_media", "find_install_target", "is_baken_boot_media", "ReadBlocks", "WriteBlocks"):
            self.assertNotIn(forbidden, boot)
        self.assertIn("EFI_SYSTEM_TABLE", boot)
        self.assertIn("EFI_GRAPHICS_OUTPUT_PROTOCOL_GUID", boot)
        self.assertIn("EFI_LOADED_IMAGE_PROTOCOL_GUID", boot)
        self.assertIn("baken_exit_boot_services_final(", boot)


if __name__ == "__main__": unittest.main()

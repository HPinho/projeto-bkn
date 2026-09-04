#!/usr/bin/env python3
"""Guardrails da reserva UEFI da arena bootstrap de page tables."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "boot" / "uefi_bootloader.sotlas"
HEADER = ROOT / "kernel" / "include" / "baken_boot_info.h"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class UefiPageTableArenaTests(unittest.TestCase):
    def setUp(self):
        self.boot = BOOT.read_text(encoding="utf-8")
        self.header = HEADER.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_bootloader_uses_allocate_pages_loader_data(self):
        for token in (
            "typedef EFI_STATUS (*EFI_ALLOCATE_PAGES)",
            "ALLOCATE_ANY_PAGES",
            "EFI_LOADER_DATA",
            "BAKEN_PAGE_TABLE_ARENA_PAGES 1024ULL",
            "reserve_page_table_arena",
        ):
            self.assertIn(token, self.boot)
        helper = self.boot.split("static EFI_STATUS reserve_page_table_arena", 1)[1]
        helper = helper.split("/* Captura um snapshot real", 1)[0]
        self.assertIn("allocate_pages(", helper)
        self.assertNotIn("AllocatePool", helper)

    def test_bootloader_records_physical_and_temporary_virtual_identity(self):
        self.assertIn("boot_info->page_table_arena_physical_base = physical_base", self.boot)
        self.assertIn("boot_info->page_table_arena_virtual_base = (void*)(uintptr_t)physical_base", self.boot)
        self.assertIn("boot_info->page_table_arena_page_count = BAKEN_PAGE_TABLE_ARENA_PAGES", self.boot)
        self.assertIn("BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID", self.boot)

    def test_arena_is_reserved_before_memory_map_snapshot(self):
        reserve_call = self.boot.index("reserve_page_table_arena(bs, &boot_info)")
        snapshot_call = self.boot.index("capture_memory_map(bs, &memory_map")
        self.assertLess(reserve_call, snapshot_call)

    def test_bootinfo_extension_preserves_legacy_prefix(self):
        self.assertIn("offsetof(BakenBootInfo, version) == 80", self.header)
        self.assertIn("offsetof(BakenBootInfo, acpi_rsdp) == 112", self.header)
        self.assertIn("offsetof(BakenBootInfo, page_table_arena_physical_base) == 120", self.header)
        self.assertIn("offsetof(BakenBootInfo, loaded_image_physical_base) == 144", self.header)
        self.assertIn("offsetof(BakenBootInfo, transition_stack_physical_base) == 168", self.header)
        self.assertIn("sizeof(BakenBootInfo) == 192", self.header)

    def test_kernel_validates_but_does_not_consume_arena_in_hybrid_path(self):
        self.assertIn("BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID", self.main)
        self.assertIn("boot_info.struct_size < 144", self.main)
        self.assertIn("page_table_arena_physical_base % X86_PAGE_SIZE", self.main)
        for token in (
            "page_table_arena_make(", "direct_map_build_from_uefi_ranges(",
            "page_table_build_direct_map(", "page_table_map_4k(", "page_table_map_2m(",
            "__write_cr3(", "x86_write_cr3(",
        ):
            self.assertNotIn(token, self.main)


if __name__ == "__main__":
    unittest.main()

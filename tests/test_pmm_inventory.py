#!/usr/bin/env python3
"""Contratos para inventário de regiões físicas após ExitBootServices."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PMM = ROOT / "kernel/src/memory/pmm.sotlas"


class PmmInventoryTests(unittest.TestCase):
    def setUp(self): self.code = PMM.read_text(encoding="utf-8")

    def test_inventory_retains_only_final_map_metadata(self):
        for token in ("memory_map_base: *const u8", "memory_map_size: usize", "descriptor_size: usize", "PMM_INVENTORY.memory_map_base = memory_map_base"):
            self.assertIn(token, self.code)

    def test_boot_descriptor_is_baken_owned_pod_contract(self):
        self.assertIn("pub struct BootMemoryDescriptor", self.code)
        for field in ("type_code: u32", "padding: u32", "physical_start: u64", "virtual_start: u64", "number_of_pages: u64", "attribute: u64"):
            self.assertIn(field, self.code)
        self.assertNotIn("EfiMemoryDescriptor", self.code)
        self.assertNotIn("EFI_", self.code)

    def test_conventional_regions_are_enumerated_with_a_typed_contract(self):
        self.assertIn("pub struct PmmPhysicalRegion", self.code)
        self.assertIn("pub fn pmm_get_conventional_region(index: u64) -> PmmPhysicalRegion", self.code)
        self.assertIn("descriptor.type_code == BAKEN_BOOT_MEMORY_CONVENTIONAL", self.code)
        self.assertIn("if ordinal == index", self.code)
        self.assertIn("return pmm_physical_region_invalid();", self.code)

    def test_physical_ranges_must_fit_one_conventional_region(self):
        self.assertIn("pub fn pmm_range_is_conventional(base: u64, page_count: u64) -> bool", self.code)
        self.assertIn("if end <= base { return false; }", self.code)
        self.assertIn("base >= region.base && end <= region_end", self.code)

    def test_inventory_stays_firmware_and_heap_independent(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.code.splitlines())
        for token in ("BootServices", "AllocatePages", "AllocatePool", "malloc(", "uefi_", "Efi", "EFI_"):
            self.assertNotIn(token, code)


if __name__ == "__main__": unittest.main()

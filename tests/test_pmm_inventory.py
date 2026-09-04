#!/usr/bin/env python3
"""Contratos para inventário de regiões físicas após ExitBootServices."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PMM = ROOT / "kernel" / "src" / "memory" / "pmm.sotlas"


class PmmInventoryTests(unittest.TestCase):
    def setUp(self):
        self.code = PMM.read_text(encoding="utf-8")

    def test_inventory_retains_only_final_map_metadata(self):
        self.assertIn("memory_map_base: *const u8", self.code)
        self.assertIn("memory_map_size: usize", self.code)
        self.assertIn("descriptor_size: usize", self.code)
        self.assertIn("PMM_INVENTORY.memory_map_base = memory_map_base", self.code)

    def test_conventional_regions_are_enumerated_with_a_typed_contract(self):
        self.assertIn("pub struct PmmPhysicalRegion", self.code)
        self.assertIn("pub fn pmm_get_conventional_region(index: u64) -> PmmPhysicalRegion", self.code)
        self.assertIn("descriptor.type_code == EFI_CONVENTIONAL_MEMORY", self.code)
        self.assertIn("if ordinal == index", self.code)
        self.assertIn("return pmm_physical_region_invalid();", self.code)

    def test_physical_ranges_must_fit_one_conventional_region(self):
        self.assertIn("pub fn pmm_range_is_conventional(base: u64, page_count: u64) -> bool", self.code)
        self.assertIn("if end <= base { return false; }", self.code)
        self.assertIn("base >= region.base && end <= region_end", self.code)

    def test_inventory_stays_firmware_and_heap_independent(self):
        for token in ("BootServices->", "AllocatePages", "AllocatePool", "malloc("):
            self.assertNotIn(token, self.code)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Guardrails do bootstrap PMM pós-ExitBootServices."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ALLOC = ROOT / "kernel" / "src" / "memory" / "pmm_allocator.sotlas"
MAIN = ROOT / "kernel" / "src" / "main.sotlas"


class PmmAllocatorTests(unittest.TestCase):
    def setUp(self):
        self.alloc = ALLOC.read_text(encoding="utf-8")
        self.main = MAIN.read_text(encoding="utf-8")

    def test_allocator_is_locked_by_default(self):
        self.assertIn("state: PMM_ALLOCATOR_STATE_LOCKED", self.alloc)
        self.assertIn("if PMM_ALLOCATOR.state != PMM_ALLOCATOR_STATE_ACTIVE { return 0; }", self.alloc)

    def test_allocator_requires_real_inventory(self):
        self.assertIn("if !pmm_inventory_is_valid() { return false; }", self.alloc)
        self.assertIn("pmm_get_conventional_region(source_index)", self.alloc)
        self.assertIn("PMM_BOOTSTRAP_MAX_REGIONS", self.alloc)

    def test_allocator_uses_page_aligned_monotonic_region(self):
        self.assertIn("pub fn pmm_alloc_page() -> u64", self.alloc)
        self.assertIn("return pmm_alloc_pages(1);", self.alloc)
        self.assertIn("pub fn pmm_alloc_pages(count: u64) -> u64", self.alloc)
        self.assertIn("while region < PMM_ALLOCATOR.active_region_count", self.alloc)
        self.assertIn("PMM_REGION_NEXT[region] = end", self.alloc)
        self.assertIn("PMM_ALLOCATOR.state = PMM_ALLOCATOR_STATE_EXHAUSTED", self.alloc)
        self.assertIn("pub fn pmm_alloc_pages_aligned(count: u64, alignment: u64)", self.alloc)
        self.assertIn("(alignment % BAKEN_PAGE_SIZE) != 0", self.alloc)
        self.assertIn("pub fn pmm_free_pages_lifo(base: u64, count: u64) -> bool", self.alloc)
        self.assertIn("base != PMM_ALLOCATOR.last_base", self.alloc)
        self.assertIn("PMM_ALLOCATOR.next_page = PMM_ALLOCATOR.last_previous_next", self.alloc)

    def test_bootstrap_bitmap_bounds_the_first_pmm_window(self):
        self.assertIn("import kernel::memory::pmm_bitmap::*;", self.alloc)
        self.assertIn("PMM_BOOTSTRAP_BITMAP_MAX_PAGES", self.alloc)
        self.assertIn("PMM_BOOTSTRAP_BITMAP_BYTES", self.alloc)
        self.assertIn("pmm_bitmap_make(", self.alloc)
        self.assertIn("pmm_bitmap_mark(&mut PMM_REGION_BITMAPS[slot], 0, true)", self.alloc)
        self.assertIn("pub fn pmm_allocator_bitmap_is_active() -> bool", self.alloc)
        self.assertIn("pub fn pmm_allocator_region_count() -> u64", self.alloc)

    def test_allocations_and_lifo_release_are_mirrored_in_bitmap(self):
        self.assertIn("fn pmm_allocator_mark_pages(base: u64, count: u64, used: bool) -> bool", self.alloc)
        self.assertGreaterEqual(self.alloc.count("pmm_allocator_mark_pages("), 4)
        self.assertIn("pmm_allocator_mark_pages(base, count, false)", self.alloc)

    def test_current_hybrid_main_must_not_activate_allocator(self):
        forbidden = "pmm_allocator_activate_after_exit_boot_services();"
        self.assertNotIn(forbidden, self.main)
        self.assertIn("pmm_allocator_is_active();", self.main)

    def test_allocator_has_no_uefi_or_heap_dependency(self):
        code = "\n".join(
            line.split("//", 1)[0] for line in self.alloc.splitlines()
        )
        for token in ("BootServices->", "AllocatePages", "AllocatePool", "malloc(", "free("):
            self.assertNotIn(token, code)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Guardrails do bootstrap PMM pós-ExitBootServices."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]; ALLOC=ROOT/"kernel/src/memory/pmm_allocator.sotlas"; POST=ROOT/"kernel/src/arch/x86_64/post_cutover.sotlas"
class PmmAllocatorTests(unittest.TestCase):
    def setUp(self): self.alloc=ALLOC.read_text(encoding="utf-8"); self.post=POST.read_text(encoding="utf-8")
    def test_allocator_is_locked_by_default(self): self.assertIn("state: PMM_ALLOCATOR_STATE_LOCKED",self.alloc); self.assertIn("if PMM_ALLOCATOR.state != PMM_ALLOCATOR_STATE_ACTIVE { return 0; }",self.alloc)
    def test_allocator_requires_real_inventory(self): self.assertIn("if !pmm_inventory_is_valid() { return false; }",self.alloc); self.assertIn("pmm_get_conventional_region(source_index)",self.alloc); self.assertIn("PMM_BOOTSTRAP_MAX_REGIONS",self.alloc)
    def test_allocator_uses_page_aligned_monotonic_region(self):
        for token in ("pub fn pmm_alloc_page() -> u64","return pmm_alloc_pages(1);","pub fn pmm_alloc_pages(count: u64) -> u64","while region < PMM_ALLOCATOR.active_region_count","PMM_REGION_NEXT[region] = end","PMM_ALLOCATOR.state = PMM_ALLOCATOR_STATE_EXHAUSTED","pub fn pmm_alloc_pages_aligned(count: u64, alignment: u64)","(alignment % BAKEN_PAGE_SIZE) != 0","pub fn pmm_free_pages_lifo(base: u64, count: u64) -> bool","base != PMM_ALLOCATOR.last_base","PMM_ALLOCATOR.next_page = PMM_ALLOCATOR.last_previous_next"): self.assertIn(token,self.alloc)
    def test_bootstrap_bitmap_bounds_the_first_pmm_window(self):
        for token in ("import kernel::memory::pmm_bitmap::*;","PMM_BOOTSTRAP_BITMAP_MAX_PAGES","PMM_BOOTSTRAP_BITMAP_BYTES","pmm_bitmap_make(","pmm_bitmap_mark(&mut PMM_REGION_BITMAPS[slot], 0, true)","pub fn pmm_allocator_bitmap_is_active() -> bool","pub fn pmm_allocator_region_count() -> u64"): self.assertIn(token,self.alloc)
    def test_allocations_and_lifo_release_are_mirrored_in_bitmap(self): self.assertIn("fn pmm_allocator_mark_pages(base: u64, count: u64, used: bool) -> bool",self.alloc); self.assertGreaterEqual(self.alloc.count("pmm_allocator_mark_pages("),4); self.assertIn("pmm_allocator_mark_pages(base, count, false)",self.alloc)
    def test_post_cutover_activates_allocator_after_inventory_and_before_vmm(self):
        body=self.post.split("pub fn post_cutover_activate_pmm",1)[1].split("pub fn post_cutover_pmm_active",1)[0]; inventory=body.index("pmm_inventory_init("); activate=body.index("pmm_allocator_activate_after_exit_boot_services()"); self.assertLess(inventory,activate); self.assertIn("pmm_allocator_bitmap_is_active()",body)
        entry=self.post.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !",1)[1]; pmm=entry.index("post_cutover_activate_pmm(context)"); vmm=entry.index("post_cutover_activate_vmm(context)",pmm); self.assertLess(pmm,vmm)
    def test_allocator_has_no_uefi_or_heap_dependency(self):
        code="\n".join(line.split("//",1)[0] for line in self.alloc.splitlines())
        for token in ("BootServices->","AllocatePages","AllocatePool","malloc(","free("): self.assertNotIn(token,code)
if __name__ == "__main__": unittest.main()

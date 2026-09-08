#!/usr/bin/env python3
"""Guardrails do PMM bitmap-backed pós-ExitBootServices."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
ALLOC = ROOT / "kernel/src/memory/pmm_allocator.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class PmmAllocatorTests(unittest.TestCase):
    def setUp(self):
        self.alloc = ALLOC.read_text(encoding="utf-8")
        self.post = POST.read_text(encoding="utf-8")

    def test_allocator_is_locked_by_default(self):
        self.assertIn("state: PMM_ALLOCATOR_STATE_LOCKED", self.alloc)
        self.assertIn("PMM_ALLOCATOR.state != PMM_ALLOCATOR_STATE_ACTIVE", self.alloc)

    def test_allocator_requires_real_inventory(self):
        self.assertIn("if !pmm_inventory_is_valid() { return false; }", self.alloc)
        self.assertIn("pmm_get_conventional_region(source_index)", self.alloc)
        self.assertIn("PMM_BOOTSTRAP_MAX_REGIONS", self.alloc)

    def test_all_allocation_modes_use_bitmap_free_run_policy(self):
        for token in (
            "fn pmm_allocator_find_run(region: u64, count: u64, alignment: u64",
            "pmm_allocator_run_is_free(region, page, count)",
            "pub fn pmm_alloc_pages(count: u64) -> u64",
            "pub fn pmm_alloc_pages_aligned(count: u64, alignment: u64) -> u64",
            "pub fn pmm_alloc_pages_constrained(count: u64, alignment: u64",
            "pmm_allocator_commit_allocation(region, base, count)",
            "pmm_bitmap_find_free_run(&PMM_REGION_BITMAPS[region], count)",
        ):
            self.assertIn(token, self.alloc)
        self.assertGreaterEqual(self.alloc.count("pmm_allocator_find_run(region, count"), 2)

    def test_arbitrary_free_rejects_double_and_partial_free(self):
        body = self.alloc.split("pub fn pmm_free_pages(base: u64, count: u64) -> bool", 1)[1]
        body = body.split("pub fn pmm_free_pages_lifo", 1)[0]
        for token in (
            "pmm_allocator_region_for_range(base, count)",
            "first == 0",
            "pmm_allocator_run_is_used(region, first, count)",
            "pmm_allocator_mark_pages(base, count, false)",
            "PMM_ALLOCATOR.allocated_pages -= count",
        ):
            self.assertIn(token, body)

    def test_general_allocator_reserves_legacy_low_memory(self):
        self.assertIn("PMM_GENERAL_ALLOC_MIN_PHYSICAL: u64 = 0x00100000", self.alloc)
        activate = self.alloc.split("pub fn pmm_allocator_activate_after_exit_boot_services", 1)[1]
        for token in (
            "reserved_physical >= PMM_GENERAL_ALLOC_MIN_PHYSICAL",
            "pmm_bitmap_mark(&mut PMM_REGION_BITMAPS[slot], reserved_page, true)",
            "next_candidate = PMM_GENERAL_ALLOC_MIN_PHYSICAL",
        ):
            self.assertIn(token, activate)
        free_body = self.alloc.split("pub fn pmm_free_pages(base: u64, count: u64) -> bool", 1)[1]
        free_body = free_body.split("pub fn pmm_free_pages_lifo", 1)[0]
        self.assertIn("base < PMM_GENERAL_ALLOC_MIN_PHYSICAL", free_body)

    def test_lifo_api_remains_compatible_without_recursive_lock(self):
        body = self.alloc.split("pub fn pmm_free_pages_lifo", 1)[1]
        body = body.split("fn pmm_allocator_self_test_reuse", 1)[0]
        self.assertIn("base != PMM_ALLOCATOR.last_base", body)
        self.assertIn("pmm_free_pages_locked(base, count)", body)
        self.assertNotIn("pmm_free_pages(base, count)", body)
        self.assertIn("PMM_REGION_NEXT[region] = previous_frontier", body)

    def test_runtime_mutations_are_serialized_across_cpus(self):
        self.assertIn("import kernel::sync::spinlock::*;", self.alloc)
        self.assertIn("static mut PMM_ALLOCATOR_LOCK: SpinLock", self.alloc)
        self.assertIn("static mut PMM_ALLOCATOR_LOCK_READY: bool = false", self.alloc)
        lock = self.alloc.split("fn pmm_allocator_lock_irq() -> u64", 1)[1]
        lock = lock.split("fn pmm_allocator_unlock_irq", 1)[0]
        self.assertLess(lock.index("x86_irq_save_disable()"), lock.index("spinlock_lock(&mut PMM_ALLOCATOR_LOCK)"))
        unlock = self.alloc.split("fn pmm_allocator_unlock_irq", 1)[1]
        unlock = unlock.split("pub fn pmm_allocator_is_active", 1)[0]
        self.assertLess(unlock.index("spinlock_unlock(&mut PMM_ALLOCATOR_LOCK)"), unlock.index("x86_irq_restore(flags)"))

        wrappers = (
            ("pub fn pmm_alloc_pages(count: u64) -> u64", "fn pmm_alloc_pages_locked", "pmm_alloc_pages_locked(count)"),
            ("pub fn pmm_alloc_pages_aligned(count: u64, alignment: u64) -> u64", "fn pmm_alloc_pages_aligned_locked", "pmm_alloc_pages_aligned_locked(count, alignment)"),
            ("pub fn pmm_alloc_pages_constrained(count: u64, alignment: u64", "fn pmm_alloc_pages_constrained_locked", "pmm_alloc_pages_constrained_locked(count, alignment, max_address, boundary)"),
            ("pub fn pmm_free_pages(base: u64, count: u64) -> bool", "fn pmm_free_pages_locked", "pmm_free_pages_locked(base, count)"),
            ("pub fn pmm_free_pages_lifo(base: u64, count: u64) -> bool", "fn pmm_free_pages_lifo_locked", "pmm_free_pages_lifo_locked(base, count)"),
        )
        for public, boundary, helper in wrappers:
            body = self.alloc.split(public, 1)[1].split(boundary, 1)[0]
            acquire = body.index("pmm_allocator_lock_irq()")
            call = body.index(helper)
            release = body.index("pmm_allocator_unlock_irq(flags)")
            self.assertLess(acquire, call)
            self.assertLess(call, release)

        activate = self.alloc.split("pub fn pmm_allocator_activate_after_exit_boot_services", 1)[1]
        self.assertLess(activate.index("spinlock_init(&mut PMM_ALLOCATOR_LOCK)"),
                        activate.index("PMM_ALLOCATOR.state = PMM_ALLOCATOR_STATE_ACTIVE"))

    def test_allocator_self_test_proves_out_of_order_reuse(self):
        body = self.alloc.split("fn pmm_allocator_self_test_reuse", 1)[1]
        body = body.split("pub fn pmm_allocator_activate_after_exit_boot_services", 1)[0]
        for token in (
            "let first = pmm_alloc_pages(2)",
            "let second = pmm_alloc_pages(2)",
            "pmm_free_pages(first, 2)",
            "let recycled = pmm_alloc_pages(2)",
            "recycled != first",
            "pmm_free_pages(second, 2)",
        ):
            self.assertIn(token, body)
        activate = self.alloc.split("pub fn pmm_allocator_activate_after_exit_boot_services", 1)[1]
        self.assertIn("if !pmm_allocator_self_test_reuse()", activate)
        self.assertIn("PMM_REUSE_SELF_TEST_PASSED = true", activate)

    def test_failed_large_or_aligned_request_does_not_poison_free_pages(self):
        self.assertIn("fn pmm_allocator_any_free_page() -> bool", self.alloc)
        self.assertIn("pmm_allocator_note_failure_if_empty()", self.alloc)
        self.assertIn("if pmm_allocator_any_free_page() { return; }", self.alloc)
        constrained = self.alloc.split("pub fn pmm_alloc_pages_constrained", 1)[1]
        constrained = constrained.split("pub fn pmm_free_pages", 1)[0]
        self.assertNotIn("PMM_ALLOCATOR_STATE_EXHAUSTED", constrained)

    def test_bootstrap_bitmap_bounds_pmm_regions(self):
        for token in (
            "import kernel::memory::pmm_bitmap::*;",
            "PMM_BOOTSTRAP_BITMAP_MAX_PAGES",
            "PMM_BOOTSTRAP_BITMAP_BYTES",
            "pmm_bitmap_make(",
            "pmm_bitmap_mark(&mut PMM_REGION_BITMAPS[slot], 0, true)",
            "pub fn pmm_allocator_bitmap_is_active() -> bool",
        ):
            self.assertIn(token, self.alloc)

    def test_post_cutover_activates_allocator_after_inventory_and_before_vmm(self):
        body = self.post.split("pub fn post_cutover_activate_pmm", 1)[1].split("pub fn post_cutover_pmm_active", 1)[0]
        inventory = body.index("pmm_inventory_init(")
        activate = body.index("pmm_allocator_activate_after_exit_boot_services()")
        self.assertLess(inventory, activate)
        self.assertIn("pmm_allocator_bitmap_is_active()", body)
        entry = self.post.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        pmm = entry.index("post_cutover_activate_pmm(context)")
        vmm = entry.index("post_cutover_activate_vmm(context)", pmm)
        self.assertLess(pmm, vmm)

    def test_allocator_has_no_uefi_or_host_heap_dependency(self):
        code = "\n".join(line.split("//", 1)[0] for line in self.alloc.splitlines())
        for token in ("BootServices->", "AllocatePages", "AllocatePool"):
            self.assertNotIn(token, code)
        self.assertIsNone(re.search(r"(?<![A-Za-z0-9_])(?:malloc|free)\s*\(", code))


if __name__ == "__main__":
    unittest.main()

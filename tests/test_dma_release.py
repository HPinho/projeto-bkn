#!/usr/bin/env python3
"""Guardrails do HID-4d.3b0: release DMA normal deve aceitar free fora de ordem."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DMA = ROOT / "kernel/src/memory/dma.sotlas"
PMM = ROOT / "kernel/src/memory/pmm_allocator.sotlas"


def function_body(text: str, signature: str, next_signature: str) -> str:
    return text.split(signature, 1)[1].split(next_signature, 1)[0]


class DmaReleaseTests(unittest.TestCase):
    def setUp(self):
        self.text = DMA.read_text(encoding="utf-8")
        self.release = function_body(
            self.text,
            "pub fn dma_release(buffer: *mut DmaBuffer) -> bool",
            "pub fn dma_alloc_for_device",
        )

    def test_release_uses_arbitrary_bitmap_backed_free(self):
        self.assertIn("if buffer == (null as *mut DmaBuffer) { return false; }", self.release)
        self.assertIn("if !dma_buffer_cpu_owned(buffer as *const DmaBuffer) { return false; }", self.release)
        self.assertIn("if !dma_allocator_available() { return false; }", self.release)
        self.assertIn("let page_count = (*buffer).size / BAKEN_PAGE_SIZE;", self.release)
        self.assertIn("pmm_free_pages((*buffer).physical_address, page_count)", self.release)
        self.assertNotIn("pmm_free_pages_lifo", self.release)

    def test_release_invalidates_only_after_pmm_accepts_free(self):
        free_call = self.release.index("pmm_free_pages((*buffer).physical_address, page_count)")
        invalidation = self.release.index("(*buffer) = dma_invalid_buffer();")
        self.assertLess(free_call, invalidation)
        between = self.release[free_call:invalidation]
        self.assertIn("return false;", between)

    def test_release_rejects_device_and_shared_ownership(self):
        owned = function_body(
            self.text,
            "pub fn dma_buffer_cpu_owned(buffer: *const DmaBuffer) -> bool",
            "pub fn dma_buffer_device_owned",
        )
        self.assertIn("(*buffer).owner == DMA_OWNER_CPU || (*buffer).owner == DMA_OWNER_COMPLETED", owned)
        self.assertNotIn("DMA_OWNER_DEVICE", owned)
        self.assertNotIn("DMA_OWNER_SHARED", owned)
        self.assertIn("dma_buffer_cpu_owned(buffer as *const DmaBuffer)", self.release)

    def test_allocator_immediate_rollbacks_remain_lifo(self):
        alloc = function_body(
            self.text,
            "pub fn dma_alloc(size: u64, alignment: u64) -> DmaBuffer",
            "pub fn dma_submit_to_device",
        )
        constrained = self.text.split("pub fn dma_alloc_for_device", 1)[1]
        self.assertGreaterEqual(alloc.count("pmm_free_pages_lifo(physical, page_count)"), 1)
        self.assertGreaterEqual(constrained.count("pmm_free_pages_lifo(physical, page_count)"), 1)

    def test_pmm_already_exposes_arbitrary_free_and_reuse_proof(self):
        pmm = PMM.read_text(encoding="utf-8")
        self.assertIn("pub fn pmm_free_pages(base: u64, count: u64) -> bool", pmm)
        self.assertIn("if !pmm_allocator_run_is_used(region, first, count) { return false; }", pmm)
        self.assertIn("if !pmm_free_pages(first, 2)", pmm)
        self.assertIn("let recycled = pmm_alloc_pages(2);", pmm)
        self.assertIn("recycled != first", pmm)


if __name__ == "__main__":
    unittest.main()

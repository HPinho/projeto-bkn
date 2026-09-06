#!/usr/bin/env python3
"""Guardrails do DMA físico pós-cutover, sem dependência UEFI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DMA = ROOT / "kernel/src/memory/dma.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def code_without_comments(path: Path) -> str:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        lines.append(raw.split("//", 1)[0])
    return "\n".join(lines)


class DmaContractTests(unittest.TestCase):
    def test_dma_buffer_carries_virtual_and_physical_addresses(self):
        text = DMA.read_text(encoding="utf-8")
        self.assertIn("pub struct DmaBuffer", text)
        self.assertIn("virtual_address: *mut u8", text)
        self.assertIn("physical_address: u64", text)
        self.assertIn("alignment: u64", text)
        self.assertIn("owner: u32", text)
        self.assertIn("fence: u64", text)
        self.assertIn("valid: bool", text)
        self.assertIn("pub fn dma_buffer_valid(buffer: *const DmaBuffer) -> bool", text)

    def test_dma_requires_active_pmm_and_vmm_before_exposing_memory(self):
        text = DMA.read_text(encoding="utf-8")
        self.assertIn("pub fn dma_allocator_available() -> bool", text)
        self.assertIn("pmm_allocator_is_active()", text)
        self.assertIn("vmm_is_active()", text)
        self.assertIn("vmm_direct_map_base() == BAKEN_DIRECT_MAP_BASE", text)
        self.assertIn("if !pmm_inventory_is_valid()", text)
        self.assertIn("if !dma_allocator_available()", text)
        self.assertIn("pmm_alloc_pages_aligned(page_count, alignment)", text)
        self.assertIn("direct_map_virtual_address(physical)", text)
        self.assertIn("if rounded < size { return dma_invalid_buffer(); }", text)

        alloc = text.split("pub fn dma_alloc(size: u64, alignment: u64)", 1)[1]
        alloc = alloc.split("pub fn dma_submit_to_device", 1)[0]
        self.assertIn("if !dma_buffer_valid(&buffer)", alloc)
        self.assertIn("pmm_free_pages_lifo(physical, page_count)", alloc)

        self.assertIn("valid: true", text)
        self.assertIn("pub fn dma_submit_to_device(buffer: *mut DmaBuffer, fence: u64) -> bool", text)
        self.assertIn("pub fn dma_complete_from_device(buffer: *mut DmaBuffer, fence: u64) -> bool", text)
        self.assertIn("pub fn dma_release(buffer: *mut DmaBuffer) -> bool", text)
        self.assertIn("pmm_free_pages_lifo((*buffer).physical_address, page_count)", text)

    def test_constrained_dma_applies_device_limits_before_exposing_buffer(self):
        text = DMA.read_text(encoding="utf-8")
        body = text.split("pub fn dma_alloc_for_device", 1)[1]
        self.assertIn("pmm_alloc_pages_constrained(page_count, alignment, max_address, boundary)", body)
        self.assertIn("last > max_address", body)
        self.assertIn("physical / boundary != last / boundary", body)
        self.assertIn("pmm_free_pages_lifo(physical, page_count)", body)
        self.assertNotIn("let mut buffer = dma_alloc(size, alignment)", body)

    def test_dma_ownership_supports_exclusive_and_shared_modes(self):
        text = DMA.read_text(encoding="utf-8")
        self.assertIn("DMA_OWNER_CPU", text)
        self.assertIn("DMA_OWNER_DEVICE", text)
        self.assertIn("DMA_OWNER_COMPLETED", text)
        self.assertIn("DMA_OWNER_SHARED", text)
        self.assertIn("if (*buffer).fence != fence { return false; }", text)
        self.assertIn("pub fn dma_share_with_device", text)
        self.assertIn("pub fn dma_unshare_from_device", text)
        self.assertIn("pub fn dma_buffer_cpu_accessible", text)
        self.assertIn("pub fn dma_buffer_device_accessible", text)
        self.assertIn("if !dma_buffer_cpu_owned(buffer as *const DmaBuffer)", text)
        self.assertIn("if !dma_buffer_device_owned(buffer as *const DmaBuffer)", text)

    def test_shared_mode_has_no_transfer_fence(self):
        text = DMA.read_text(encoding="utf-8")
        self.assertIn("if (*buffer).owner == DMA_OWNER_SHARED && (*buffer).fence != 0 { return false; }", text)
        self.assertIn("(*buffer).owner = DMA_OWNER_SHARED", text)
        self.assertIn("(*buffer).fence = 0", text)

    def test_dma_does_not_fabricate_memory_or_call_uefi(self):
        code = code_without_comments(DMA).lower()
        for token in (
            "bootservices", "allocatepages", "allocatepool", "freepool",
            "system_table", "efi_", "malloc", "calloc", "realloc",
            "0x100000", "0x200000", "identity_map",
        ):
            self.assertNotIn(token, code, token)

    def test_dma_alignment_is_power_of_two_and_page_sized(self):
        text = DMA.read_text(encoding="utf-8")
        self.assertIn("DMA_DEFAULT_ALIGNMENT: u64 = 4096", text)
        self.assertIn("(alignment & (alignment - 1)) == 0", text)

    def test_main_registers_dma_without_allocating_from_hybrid_path(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::memory::dma::*;", text)
        self.assertIn("dma_allocator_available();", text)
        self.assertNotIn("dma_alloc(", text)


if __name__ == "__main__":
    unittest.main()

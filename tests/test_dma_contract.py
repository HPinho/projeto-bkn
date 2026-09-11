#!/usr/bin/env python3
"""Guardrails do DMA físico pós-cutover, sem dependência UEFI."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
DMA=ROOT/"kernel/src/memory/dma.sotlas"; POST=ROOT/"kernel/src/arch/x86_64/post_cutover.sotlas"; PROBE=ROOT/"kernel/src/storage/foundation_probe.sotlas"
def code_without_comments(path): return "\n".join(raw.split("//",1)[0] for raw in path.read_text(encoding="utf-8").splitlines())
class DmaContractTests(unittest.TestCase):
    def test_dma_buffer_carries_virtual_and_physical_addresses(self):
        text=DMA.read_text(encoding="utf-8")
        for token in ("pub struct DmaBuffer","virtual_address: *mut u8","physical_address: u64","alignment: u64","owner: u32","fence: u64","valid: bool","pub fn dma_buffer_valid(buffer: *const DmaBuffer) -> bool"): self.assertIn(token,text)
    def test_dma_requires_active_pmm_and_vmm_before_exposing_memory(self):
        text=DMA.read_text(encoding="utf-8")
        for token in ("pub fn dma_allocator_available() -> bool","pmm_allocator_is_active()","vmm_is_active()","vmm_direct_map_base() == BAKEN_DIRECT_MAP_BASE","if !pmm_inventory_is_valid()","if !dma_allocator_available()","pmm_alloc_pages_aligned(page_count, alignment)","direct_map_virtual_address(physical)","if rounded < size { return dma_invalid_buffer(); }"): self.assertIn(token,text)
        alloc=text.split("pub fn dma_alloc(size: u64, alignment: u64)",1)[1].split("pub fn dma_submit_to_device",1)[0]
        self.assertIn("if !dma_buffer_valid(&buffer)",alloc); self.assertIn("pmm_free_pages_lifo(physical, page_count)",alloc)
        for token in ("valid: true","pub fn dma_submit_to_device(buffer: *mut DmaBuffer, fence: u64) -> bool","pub fn dma_complete_from_device(buffer: *mut DmaBuffer, fence: u64) -> bool","pub fn dma_release(buffer: *mut DmaBuffer) -> bool","pmm_free_pages((*buffer).physical_address, page_count)"): self.assertIn(token,text)
    def test_constrained_dma_applies_device_limits_before_exposing_buffer(self):
        body=DMA.read_text(encoding="utf-8").split("pub fn dma_alloc_for_device",1)[1]
        for token in ("pmm_alloc_pages_constrained(page_count, alignment, max_address, boundary)","last > max_address","physical / boundary != last / boundary","pmm_free_pages_lifo(physical, page_count)"): self.assertIn(token,body)
        self.assertNotIn("let mut buffer = dma_alloc(size, alignment)",body)
    def test_dma_ownership_supports_exclusive_and_shared_modes(self):
        text=DMA.read_text(encoding="utf-8")
        for token in ("DMA_OWNER_CPU","DMA_OWNER_DEVICE","DMA_OWNER_COMPLETED","DMA_OWNER_SHARED","if (*buffer).fence != fence { return false; }","pub fn dma_share_with_device","pub fn dma_unshare_from_device","pub fn dma_buffer_cpu_accessible","pub fn dma_buffer_device_accessible","if !dma_buffer_cpu_owned(buffer as *const DmaBuffer)","if !dma_buffer_device_owned(buffer as *const DmaBuffer)"): self.assertIn(token,text)
    def test_shared_mode_has_no_transfer_fence(self):
        text=DMA.read_text(encoding="utf-8"); self.assertIn("if (*buffer).owner == DMA_OWNER_SHARED && (*buffer).fence != 0 { return false; }",text); self.assertIn("(*buffer).owner = DMA_OWNER_SHARED",text); self.assertIn("(*buffer).fence = 0",text)
    def test_dma_does_not_fabricate_memory_or_call_uefi(self):
        code=code_without_comments(DMA).lower()
        for token in ("bootservices","allocatepages","allocatepool","freepool","system_table","efi_","malloc","calloc","realloc","0x100000","0x200000","identity_map"): self.assertNotIn(token,code,token)
    def test_dma_alignment_is_power_of_two_and_page_sized(self):
        text=DMA.read_text(encoding="utf-8"); self.assertIn("DMA_DEFAULT_ALIGNMENT: u64 = 4096",text); self.assertIn("(alignment & (alignment - 1)) == 0",text)
    def test_post_cutover_reaches_dma_probe_only_after_pmm_and_vmm_activation(self):
        entry=POST.read_text(encoding="utf-8").split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !",1)[1]
        pmm=entry.index("post_cutover_activate_pmm(context)"); vmm=entry.index("post_cutover_activate_vmm(context)",pmm); probe=entry.index("foundation_memory_probe()",vmm)
        self.assertLess(pmm,vmm); self.assertLess(vmm,probe); self.assertIn("dma_alloc_for_device(4096, 4096, 0xFFFFFFFF, 65536)",PROBE.read_text(encoding="utf-8"))
if __name__ == "__main__": unittest.main()

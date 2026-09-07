#!/usr/bin/env python3
"""Regressões da auditoria integrada das fundações bare-metal."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
PMM = ROOT / "kernel/src/memory/pmm_allocator.sotlas"
DMA = ROOT / "kernel/src/memory/dma.sotlas"
AHCI = ROOT / "kernel/src/drivers/ahci_block_read.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class FoundationAuditRegressionTests(unittest.TestCase):
    def test_post_cutover_storage_prefers_ahci_then_falls_back_to_nvme(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("pub fn storage_discovery_scan() -> u32", 1)[1]
        ahci_filter = "if kind != STORAGE_CONTROLLER_AHCI { continue; }"
        nvme_filter = "if kind != STORAGE_CONTROLLER_NVME { continue; }"
        self.assertIn("let post_cutover = active_page_tables_is_ready();", body)
        self.assertIn("if !post_cutover {", body)
        self.assertIn(ahci_filter, body)
        self.assertIn(nvme_filter, body)
        self.assertIn("storage_register_ahci_block_device()", body)
        self.assertIn("storage_register_nvme_block_device()", body)
        self.assertIn("return STORAGE_CONTROLLER_AHCI;", body)
        self.assertIn("return STORAGE_CONTROLLER_NVME;", body)
        self.assertLess(body.index(ahci_filter), body.index("storage_register_ahci_block_device()"))
        self.assertLess(body.index("storage_register_ahci_block_device()"), body.index(nvme_filter))
        self.assertLess(body.index(nvme_filter), body.index("storage_register_nvme_block_device()"))
        self.assertNotIn("if post_cutover && kind != STORAGE_CONTROLLER_AHCI { continue; }", body)

    def test_gpt_gate_requires_generic_block_io_after_storage_discovery(self):
        text = POST.read_text(encoding="utf-8")
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        self.assertLess(entry.index("post_cutover_discover_first_storage_controller()"),
                        entry.index("post_cutover_probe_backup_gpt_header()"))
        body = text.split("pub fn post_cutover_probe_backup_gpt_header() -> bool", 1)[1]
        body = body.split("pub fn post_cutover_probe_backup_gpt_entries()", 1)[0]
        self.assertIn("if !storage_generic_block_io_is_ready() { return false; }", body)

    def test_nvme_remains_an_independent_gate_after_filesystem_proof(self):
        text = POST.read_text(encoding="utf-8")
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        self.assertLess(entry.index("foundation_fat_path_probe()"), entry.index("foundation_nvme_probe()"))
        self.assertLess(entry.index("foundation_nvme_probe()"), entry.index("active_framebuffer_write_combining("))

    def test_device_dma_allocation_is_constrained_before_reservation(self):
        pmm = PMM.read_text(encoding="utf-8")
        dma = DMA.read_text(encoding="utf-8")
        self.assertIn("pub fn pmm_alloc_pages_constrained(", pmm)
        constrained = pmm.split("pub fn pmm_alloc_pages_constrained(", 1)[1]
        self.assertIn("last > max_address", constrained)
        self.assertIn("aligned / boundary != last / boundary", constrained)
        body = dma.split("pub fn dma_alloc_for_device", 1)[1]
        self.assertIn("pmm_alloc_pages_constrained(page_count, alignment, max_address, boundary)", body)
        self.assertNotIn("let mut buffer = dma_alloc(size, alignment)", body)

    def test_dma_failed_virtualization_rolls_back_last_pmm_allocation(self):
        text = DMA.read_text(encoding="utf-8")
        alloc = text.split("pub fn dma_alloc(size: u64, alignment: u64)", 1)[1]
        alloc = alloc.split("pub fn dma_submit_to_device", 1)[0]
        self.assertGreaterEqual(alloc.count("pmm_free_pages_lifo(physical, page_count)"), 3)

    def test_ci_keeps_ahci_and_nvme_disks_simultaneously(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("-drive file=build/storage-test.img,format=raw,if=ide,index=0", text)
        self.assertIn("-device nvme,drive=nvme_disk,serial=BAKEN-CI-NVME", text)
        ahci = AHCI.read_text(encoding="utf-8")
        self.assertIn("AHCI_READ_TEST_LBA: u64 = 1023", ahci)
        self.assertIn("AHCI_WRITE_TEST_LBA: u64 = 1024", ahci)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Guardrails do contrato DMA fail-closed antes do cutover UEFI."""

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
        self.assertIn("valid: bool", text)

    def test_dma_allocator_is_fail_closed_before_pmm_allocator(self):
        text = DMA.read_text(encoding="utf-8")
        self.assertIn("pub fn dma_allocator_available() -> bool", text)
        self.assertIn("return false;", text)
        self.assertIn("if !pmm_inventory_is_valid()", text)
        self.assertIn("if !dma_allocator_available()", text)
        self.assertIn("return dma_invalid_buffer();", text)

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

    def test_main_keeps_dma_contract_disabled(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::memory::dma::*;", text)
        self.assertIn("dma_allocator_available();", text)
        self.assertNotIn("dma_alloc(", text)


if __name__ == "__main__":
    unittest.main()

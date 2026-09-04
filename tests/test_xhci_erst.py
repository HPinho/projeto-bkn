#!/usr/bin/env python3
"""Guardrails do contrato fail-closed de ERST xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ERST = ROOT / "kernel/src/drivers/xhci_erst.sotlas"


def code_without_comments(path: Path) -> str:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        lines.append(raw.split("//", 1)[0])
    return "\n".join(lines)


class XhciErstTests(unittest.TestCase):
    def test_erst_entry_contract_is_16_bytes_by_fields(self):
        text = ERST.read_text(encoding="utf-8")
        self.assertIn("XHCI_ERST_ENTRY_SIZE: u64 = 16", text)
        self.assertIn("pub struct XhciErstEntry", text)
        self.assertIn("ring_segment_base_address: u64", text)
        self.assertIn("ring_segment_size: u32", text)
        self.assertIn("reserved: u32", text)

    def test_event_segment_requires_spec_alignment_and_size(self):
        text = ERST.read_text(encoding="utf-8")
        self.assertIn("XHCI_EVENT_SEGMENT_ALIGNMENT: u64 = 64", text)
        self.assertIn("XHCI_EVENT_SEGMENT_MIN_TRBS: u32 = 16", text)
        self.assertIn("XHCI_EVENT_SEGMENT_MAX_TRBS: u32 = 4096", text)
        self.assertIn("segment.physical_address & (XHCI_EVENT_SEGMENT_ALIGNMENT - 1)", text)
        self.assertIn("let required_bytes = (trb_count as u64) * XHCI_EVENT_TRB_SIZE", text)

    def test_erst_requires_real_dma_segment(self):
        text = ERST.read_text(encoding="utf-8")
        self.assertIn("if !dma_buffer_cpu_owned(&segment)", text)
        self.assertIn("segment.size < required_bytes", text)

    def test_erst_contract_does_not_program_runtime_registers(self):
        code = code_without_comments(ERST).lower()
        for token in (
            "erstba", "erstsz", "erdp", "mmio_read", "mmio_write",
            "doorbell", "interrupt_enable", "pci_write", "dma_alloc(",
        ):
            self.assertNotIn(token, code, token)

    def test_reserved_field_must_remain_zero(self):
        text = ERST.read_text(encoding="utf-8")
        self.assertIn("return (*entry).reserved == 0", text)
        self.assertIn("reserved: 0", text)


if __name__ == "__main__":
    unittest.main()

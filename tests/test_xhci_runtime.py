#!/usr/bin/env python3
"""Guardrails das estruturas DMA xHCI antes do start do controller."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "kernel/src/drivers/xhci_runtime.sotlas"


def _code_only(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciRuntimeTests(unittest.TestCase):
    def test_runtime_uses_real_dma_and_single_contiguous_arena(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("import kernel::memory::dma::*;", text)
        self.assertIn("let arena = dma_alloc(total_pages * XHCI_RUNTIME_PAGE_SIZE", text)
        self.assertIn("dma_buffer_cpu_owned(&arena)", text)
        self.assertNotIn("uefi", _code_only(text).lower())

    def test_runtime_contains_dcbaa_command_event_erst_layout(self):
        text = RUNTIME.read_text(encoding="utf-8")
        for token in (
            "XHCI_DCBAA_PAGE_INDEX",
            "XHCI_COMMAND_RING_PAGE_INDEX",
            "XHCI_EVENT_RING_PAGE_INDEX",
            "XHCI_ERST_PAGE_INDEX",
            "xhci_ring_bind(command_buffer",
            "xhci_erst_entry_from_dma(event_buffer",
            "xhci_event_ring_init(&erst_entry)",
        ):
            self.assertIn(token, text)

    def test_command_ring_installs_link_trb(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("let link_index = XHCI_RUNTIME_COMMAND_TRBS - 1", text)
        self.assertIn("xhci_trb_link(command_ring.physical_base, true, command_ring.cycle_state)", text)
        self.assertIn("xhci_runtime_write_trb(command_ring.virtual_base, link_index, link)", text)

    def test_scratchpads_are_not_assumed_zero(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("let scratchpads = xhci_controller_max_scratchpads()", text)
        self.assertIn("xhci_runtime_pointer_array_pages(scratchpads)", text)
        self.assertIn("scratchpad.physical_address", text)
        self.assertIn("xhci_runtime_write_u64(dcbaa.virtual_address, 0, scratchpad_array_physical)", text)

    def test_runtime_does_not_start_controller_or_ring_doorbell(self):
        code = _code_only(RUNTIME.read_text(encoding="utf-8")).lower()
        body = code.split("module kernel::drivers::xhci_runtime;", 1)[1]
        for forbidden in (
            "pci_command_bus_master",
            "run_stop",
            "x86_mmio_write32",
            "enable_slot",
        ):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()

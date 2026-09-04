#!/usr/bin/env python3
"""Guardrails da memória por slot xHCI antes de Address Device."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "kernel/src/drivers/xhci_context.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciContextTests(unittest.TestCase):
    def test_context_supports_32_and_64_byte_layouts(self):
        text = CONTEXT.read_text(encoding="utf-8")
        self.assertIn("XHCI_HCCPARAMS1_CSZ", text)
        self.assertIn("return 64", text)
        self.assertIn("return 32", text)
        self.assertIn("let slot_context_offset = context_size as u64", text)
        self.assertIn("let ep0_context_offset = (context_size as u64) * 2", text)

    def test_context_uses_one_three_page_dma_arena(self):
        text = CONTEXT.read_text(encoding="utf-8")
        self.assertIn("XHCI_CONTEXT_ARENA_PAGES: u64 = 3", text)
        self.assertIn("XHCI_DEVICE_CONTEXT_PAGE: u64 = 0", text)
        self.assertIn("XHCI_INPUT_CONTEXT_PAGE: u64 = 1", text)
        self.assertIn("XHCI_EP0_RING_PAGE: u64 = 2", text)
        self.assertIn("dma_alloc(XHCI_CONTEXT_ARENA_PAGES * XHCI_CONTEXT_PAGE_SIZE", text)

    def test_ep0_packet_size_depends_on_port_speed(self):
        text = CONTEXT.read_text(encoding="utf-8")
        self.assertIn("speed_id == 1 || speed_id == 2", text)
        self.assertIn("return 8", text)
        self.assertIn("speed_id == 3", text)
        self.assertIn("return 64", text)
        self.assertIn("speed_id >= 4", text)
        self.assertIn("return 512", text)

    def test_dcbaa_slot_is_published_only_after_context_and_ring_setup(self):
        text = CONTEXT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_context_prepare_for_enabled_slot()", 1)[1]
        zero = body.index("xhci_context_zero")
        link = body.index("xhci_trb_link")
        slot_context = body.index("slot_context_offset")
        dcbaa = body.index("xhci_context_write_dcbaa_slot")
        shared = body.index("dma_share_with_device")
        self.assertLess(zero, link)
        self.assertLess(link, slot_context)
        self.assertLess(slot_context, dcbaa)
        self.assertLess(dcbaa, shared)

    def test_address_device_is_not_sent_in_context_stage(self):
        text = CONTEXT.read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))
        self.assertNotIn("address_device", code.lower())
        self.assertNotIn("xhci_command_submit", code)
        self.assertNotIn("doorbell", code.lower())

    def test_context_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_context::*;", text)


if __name__ == "__main__":
    unittest.main()

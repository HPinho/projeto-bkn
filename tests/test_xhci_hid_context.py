#!/usr/bin/env python3
"""Guardrails da fundação do Endpoint Context HID Interrupt IN."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HID = ROOT / "kernel/src/drivers/xhci_hid_context.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def code_only(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


class XhciHidContextTests(unittest.TestCase):
    def test_dci_is_derived_from_interrupt_in_endpoint_number(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("USB_ENDPOINT_DIRECTION_IN", text)
        self.assertIn("((endpoint as u16) * 2) + 1", text)
        self.assertIn("XHCI_HID_MAX_CONTEXT_INDEX", text)
        self.assertIn("xhci_hid_context_compute_dci(endpoint_address)", text)

    def test_hid_ring_is_pmm_dma_backed_and_linked(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("dma_alloc(XHCI_HID_RING_SIZE, XHCI_HID_RING_SIZE)", text)
        self.assertIn("xhci_ring_bind", text)
        self.assertIn("xhci_trb_link", text)
        self.assertIn("dma_share_with_device", text)

    def test_input_context_add_flag_and_context_entries_use_dci(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("1 << (dci as u32)", text)
        self.assertIn("XHCI_INPUT_CONTROL_ADD_SLOT | add_flag", text)
        self.assertIn("xhci_hid_context_write32(input, drop_flags_offset, 0)", text)
        self.assertIn("XHCI_SLOT_CONTEXT_ENTRIES_SHIFT", text)
        self.assertIn("((dci as u64) + 1) * (context_size as u64)", text)

    def test_endpoint_context_is_interrupt_in_with_tr_dequeue(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("XHCI_ENDPOINT_TYPE_INTERRUPT_IN", text)
        self.assertIn("XHCI_ENDPOINT_CONTEXT_MAX_PACKET_SHIFT", text)
        self.assertIn("ring.physical_base | XHCI_TR_DEQUEUE_DCS", text)
        self.assertIn("XHCI_ENDPOINT_CONTEXT_AVG_TRB_LENGTH", text)

    def test_periodic_endpoint_sets_max_esit_payload(self):
        text = HID.read_text(encoding="utf-8")
        self.assertIn("XHCI_ENDPOINT_CONTEXT_MAX_ESIT_PAYLOAD_SHIFT", text)
        self.assertIn("((max_packet as u32) << XHCI_ENDPOINT_CONTEXT_MAX_ESIT_PAYLOAD_SHIFT)", text)
        self.assertIn("let ep_dw4", text)

    def test_full_low_speed_interval_uses_xhci_exponent_encoding(self):
        text = HID.read_text(encoding="utf-8")
        body = text.split("fn xhci_hid_context_compute_interval", 1)[1]
        body = body.split("pub fn xhci_hid_context_prepare", 1)[0]
        self.assertIn("let microframes = (usb_interval as u32) * 8", body)
        self.assertIn("let encoded = exponent + 1", body)
        self.assertIn("let encoded = usb_interval - 1", body)

    def test_stage_has_no_command_or_doorbell_side_effects(self):
        text = code_only(HID.read_text(encoding="utf-8")).lower()
        self.assertNotIn("configure_endpoint", text)
        self.assertNotIn("xhci_command_submit", text)
        self.assertNotIn("doorbell", text)
        self.assertNotIn("x86_mmio_write32", text)

    def test_stage_stays_bootstrap_compatible(self):
        text = code_only(HID.read_text(encoding="utf-8"))
        self.assertNotIn("<<=", text)
        self.assertNotIn("1u32", text)
        self.assertNotIn("0x1Fu32", text)
        self.assertIn("power = power << 1", text)
        self.assertIn("1 << (dci as u32)", text)
        self.assertIn("0x1F << XHCI_SLOT_CONTEXT_ENTRIES_SHIFT", text)

    def test_main_registers_hid_context(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_hid_context::*;", text)


if __name__ == "__main__":
    unittest.main()

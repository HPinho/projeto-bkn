#!/usr/bin/env python3
"""Guardrails do Address Device xHCI antes de transfers EP0."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = ROOT / "kernel/src/drivers/xhci_address.sotlas"
POST_CUTOVER = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class XhciAddressTests(unittest.TestCase):
    def test_address_device_uses_real_input_context_and_slot(self):
        text = ADDRESS.read_text(encoding="utf-8")
        self.assertIn("xhci_context_input_physical()", text)
        self.assertIn("xhci_context_slot_id()", text)
        self.assertIn("xhci_trb_address_device(input_physical, slot_id, false", text)
        self.assertIn("xhci_command_submit(command)", text)
        self.assertIn("xhci_command_wait_completion(command_physical)", text)
        self.assertIn("xhci_command_last_slot_id() != slot_id", text)

    def test_address_device_requires_output_context_addressed_state(self):
        text = ADDRESS.read_text(encoding="utf-8")
        self.assertIn("XHCI_SLOT_STATE_ADDRESSED: u8 = 2", text)
        self.assertIn("xhci_context_device_physical()", text)
        self.assertIn("XHCI_SLOT_CONTEXT_DWORD3_OFFSET", text)
        self.assertIn("state != XHCI_SLOT_STATE_ADDRESSED", text)
        self.assertIn("device_address == 0", text)

    def test_address_stage_does_not_start_ep0_transfers(self):
        text = ADDRESS.read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines() if not line.strip().startswith("//"))
        self.assertNotIn("get_descriptor", code.lower())
        self.assertNotIn("setup_stage", code.lower())
        self.assertNotIn("data_stage", code.lower())
        self.assertNotIn("status_stage", code.lower())

    def test_post_cutover_addresses_only_after_context_gate(self):
        text = POST_CUTOVER.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        context = body.index("post_cutover_prepare_first_usb_context()")
        y_marker = body.index("x86_serial_write_stage_marker('Y' as u8)")
        address = body.index("post_cutover_address_first_usb_device()")
        z_marker = body.index("x86_serial_write_stage_marker('Z' as u8)")
        self.assertLess(context, y_marker)
        self.assertLess(y_marker, address)
        self.assertLess(address, z_marker)
        self.assertIn("xhci_address_first_slot()", text)
        self.assertIn("xhci_address_is_ready()", text)
        self.assertIn("xhci_address_device_address() == 0", text)

    def test_address_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_address::*;", text)


if __name__ == "__main__":
    unittest.main()

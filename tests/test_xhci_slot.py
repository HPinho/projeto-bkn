#!/usr/bin/env python3
"""Guardrails do primeiro Enable Slot xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / "kernel/src/drivers/xhci_slot.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


def _code_only(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciSlotTests(unittest.TestCase):
    def test_enable_slot_requires_prepared_port_and_stateful_command_ring(self):
        text = SLOT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_slot_enable_first_port()", 1)[1]
        self.assertIn("xhci_port_stage_is_ready()", body)
        self.assertIn("xhci_command_is_ready()", body)
        self.assertIn("xhci_trb_enable_slot", body)
        self.assertIn("xhci_command_submit(command)", body)
        self.assertIn("xhci_command_wait_completion(command_physical)", body)

    def test_slot_id_comes_from_completion_and_is_range_checked(self):
        text = SLOT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_slot_enable_first_port()", 1)[1]
        self.assertIn("xhci_command_last_slot_id()", body)
        self.assertIn("xhci_controller_max_slots()", body)
        self.assertIn("slot_id == 0", body)
        self.assertIn("slot_id > max_slots", body)

    def test_stage_stops_before_device_context_and_address_device(self):
        code = _code_only(SLOT.read_text(encoding="utf-8")).lower()
        for forbidden in (
            "xhci_trb_address_device",
            "input_context",
            "device_context",
            "dcbaa",
            "dma_alloc",
        ):
            self.assertNotIn(forbidden, code)

    def test_slot_module_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_slot::*;", text)

    def test_post_cutover_enables_slot_only_after_usb_port_ready(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertIn("post_cutover_enable_first_usb_slot()", text)
        self.assertIn("xhci_slot_enable_first_port()", text)
        self.assertIn("xhci_slot_id() == 0", text)
        self.assertLess(
            body.index("x86_serial_write_stage_marker('U' as u8)"),
            body.index("post_cutover_enable_first_usb_slot()"),
        )
        self.assertLess(
            body.index("post_cutover_enable_first_usb_slot()"),
            body.index("x86_serial_write_stage_marker('S' as u8)"),
        )

    def test_ci_requires_enable_slot_runtime_marker(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("STEP=U STEP=S", workflow)


if __name__ == "__main__":
    unittest.main()

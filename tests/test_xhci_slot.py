#!/usr/bin/env python3
"""Guardrails de Enable Slot xHCI, incluindo HID-4c multi-slot."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / "kernel/src/drivers/xhci_slot.sotlas"
TABLE = ROOT / "kernel/src/drivers/xhci_device_table.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


def _code_only(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciSlotTests(unittest.TestCase):
    def test_enable_slot_uses_stateful_command_ring_and_device_table(self):
        text = SLOT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_slot_enable_port", 1)[1]
        self.assertIn("xhci_command_is_ready()", body)
        self.assertIn("xhci_trb_enable_slot", body)
        self.assertIn("xhci_command_execute_capture_slot(command)", body)
        self.assertNotIn("xhci_command_submit(command)", body)
        self.assertNotIn("xhci_command_wait_completion(command_physical)", body)
        self.assertIn("xhci_device_table_reserve(slot_id, port_id, slot_type)", body)

    def test_slot_id_comes_from_serialized_completion_and_is_range_checked(self):
        text = SLOT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_slot_enable_port", 1)[1]
        self.assertIn("let slot_id = xhci_command_execute_capture_slot(command)", body)
        self.assertNotIn("xhci_command_last_slot_id()", body)
        self.assertIn("xhci_controller_max_slots()", body)
        self.assertIn("slot_id == 0", body)
        self.assertIn("slot_id > max_slots", body)

    def test_first_port_api_remains_compatibility_wrapper(self):
        text = SLOT.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_slot_enable_first_port()", 1)[1]
        self.assertIn("xhci_port_stage_is_ready()", body)
        self.assertIn("xhci_port_stage_port_id()", body)
        self.assertIn("xhci_slot_enable_port(port_id, slot_type)", body)

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

    def test_device_table_is_fixed_capacity_and_slot_indexed(self):
        text = TABLE.read_text(encoding="utf-8")
        self.assertIn("XHCI_DEVICE_SLOT_CAPACITY: usize = 256", text)
        self.assertIn("XHCI_DEVICE_SLOTS", text)
        self.assertIn("xhci_device_table_find_slot_for_port", text)
        self.assertIn("xhci_device_table_slot_epoch", text)
        self.assertIn("XHCI_DEVICE_ACTIVE_COUNT", text)

    def test_slot_modules_are_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_device_table::*;", text)
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

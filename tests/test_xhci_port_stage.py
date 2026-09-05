#!/usr/bin/env python3
"""Guardrails do estágio pós-No-op antes de Enable Slot."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "kernel/src/drivers/xhci_port_stage.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


def _code_only(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciPortStageTests(unittest.TestCase):
    def test_stage_requires_real_noop_before_any_port_work(self):
        text = STAGE.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_port_stage_prepare_first()", 1)[1]
        noop = body.index("xhci_start_noop_completed()")
        command = body.index("xhci_command_prepare_after_noop()")
        protocol = body.index("xhci_protocol_scan()")
        ports = body.index("xhci_port_scan()")
        reset = body.index("xhci_port_reset_first_connected()")
        self.assertLess(noop, command)
        self.assertLess(command, protocol)
        self.assertLess(protocol, ports)
        self.assertLess(ports, reset)

    def test_stage_exports_port_protocol_and_slot_type(self):
        text = STAGE.read_text(encoding="utf-8")
        self.assertIn("xhci_port_stage_port_id()", text)
        self.assertIn("xhci_port_stage_protocol_major()", text)
        self.assertIn("xhci_port_stage_slot_type()", text)
        self.assertIn("xhci_protocol_slot_type_for_port(port_id)", text)
        self.assertIn("xhci_port_reset_port_id() != port_id", text)

    def test_stage_does_not_cross_enable_slot_boundary(self):
        code = _code_only(STAGE.read_text(encoding="utf-8")).lower()
        for forbidden in (
            "xhci_trb_enable_slot",
            "xhci_trb_address_device",
            "enable slot",
            "address device",
            "input_context",
            "device_context",
            "dcbaa",
            "dma_alloc",
        ):
            self.assertNotIn(forbidden, code)

    def test_stage_is_in_canonical_graph(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::xhci_port_stage::*;", text)

    def test_post_cutover_activates_port_stage_only_after_noop(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertIn("import kernel::drivers::xhci_port_stage::*;", text)
        self.assertIn("post_cutover_prepare_first_usb_port()", text)
        self.assertIn("xhci_port_stage_prepare_first()", text)
        self.assertLess(
            body.index("x86_serial_write_stage_marker('N' as u8)"),
            body.index("post_cutover_prepare_first_usb_port()"),
        )
        self.assertLess(
            body.index("post_cutover_prepare_first_usb_port()"),
            body.index("x86_serial_write_stage_marker('U' as u8)"),
        )

    def test_qemu_requires_usb_port_runtime_marker(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("STEP=N STEP=U", workflow)


if __name__ == "__main__":
    unittest.main()

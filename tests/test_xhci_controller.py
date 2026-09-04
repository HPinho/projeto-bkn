#!/usr/bin/env python3
"""Guardrails do primeiro bring-up MMIO/reset do xHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "kernel/src/drivers/xhci_controller.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class XhciControllerTests(unittest.TestCase):
    def test_controller_enables_only_memory_space_before_dma_phase(self):
        text = CTRL.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_controller_prepare_first()", 1)[1]
        self.assertIn("PCI_COMMAND_MEMORY_SPACE", body)
        self.assertNotIn("PCI_COMMAND_BUS_MASTER", body)

    def test_mmio_is_mapped_before_first_controller_read(self):
        text = CTRL.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_controller_prepare_first()", 1)[1]
        mapping = body.index("active_page_tables_map_mmio_identity_4k(capability_page)")
        first_read = body.index("x86_mmio_read32(mmio + XHCI_CAPLENGTH_HCIVERSION)")
        self.assertLess(mapping, first_read)

    def test_reset_contract_halts_then_hcrst_then_waits_cnr(self):
        text = CTRL.read_text(encoding="utf-8")
        self.assertIn("XHCI_USBCMD_RUN_STOP", text)
        self.assertIn("XHCI_USBCMD_HCRST", text)
        self.assertIn("XHCI_USBSTS_HCHALTED", text)
        self.assertIn("XHCI_USBSTS_CNR", text)
        self.assertIn("xhci_wait_halted", text)
        self.assertIn("xhci_wait_reset_complete", text)

    def test_post_cutover_requires_keyboard_before_xhci(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_prepare_xhci_controller()", 1)[1].split(
            "pub fn sotlas_x86_post_cutover_entry", 1
        )[0]
        self.assertIn("post_cutover_keyboard_live()", body)
        self.assertIn("pci_scan_all()", body)
        self.assertIn("xhci_controller_prepare_first()", body)
        self.assertIn("POST_CUTOVER_XHCI_READY = true", body)

    def test_x_marker_comes_after_keyboard_marker(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertLess(
            body.index("x86_serial_write_stage_marker('K' as u8)"),
            body.index("x86_serial_write_stage_marker('X' as u8)"),
        )

    def test_ci_attaches_xhci_and_requires_reset_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("qemu-xhci", text)
        self.assertIn('grep -q "BAKEN:STEP=X"', text)


if __name__ == "__main__":
    unittest.main()

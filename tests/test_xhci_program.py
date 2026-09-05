#!/usr/bin/env python3
"""Guardrails da programação DCBAA/CRCR/ERST com xHC parado."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "kernel/src/drivers/xhci_program.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


def _code_only(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciProgramTests(unittest.TestCase):
    def test_programs_dcbaap_crcr_config_and_erst(self):
        text = PROGRAM.read_text(encoding="utf-8")
        for token in (
            "XHCI_OP_DCBAAP",
            "XHCI_OP_CRCR",
            "XHCI_OP_CONFIG",
            "XHCI_INTR_ERSTSZ",
            "XHCI_INTR_ERSTBA",
            "XHCI_INTR_ERDP",
            "xhci_runtime_dcbaa_physical()",
            "xhci_runtime_command_ring_physical()",
            "xhci_runtime_event_ring_physical()",
            "xhci_runtime_erst_physical()",
        ):
            self.assertIn(token, text)

    def test_controller_must_be_halted_before_and_after_programming(self):
        text = PROGRAM.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_program_halted_runtime()", 1)[1]
        self.assertGreaterEqual(body.count("XHCI_USBSTS_HCHALTED"), 2)
        self.assertIn("xhci_controller_is_ready()", body)
        self.assertIn("xhci_runtime_is_ready()", body)

    def test_programming_keeps_xhci_interrupts_disabled(self):
        text = PROGRAM.read_text(encoding="utf-8")
        self.assertIn("iman & ~XHCI_IMAN_IE", text)
        self.assertIn("(x86_mmio_read32(intr0 + XHCI_INTR_IMAN) & XHCI_IMAN_IE) != 0", text)

    def test_programming_does_not_start_dma_or_ring_doorbells(self):
        code = _code_only(PROGRAM.read_text(encoding="utf-8")).lower()
        for forbidden in (
            "pci_command_bus_master",
            "pci_enable_command_bits",
            "xhci_usbcmd_run_stop",
            "doorbell",
            "dma_share_with_device",
        ):
            self.assertNotIn(forbidden, code)

    def test_post_cutover_orders_x_before_d(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertLess(
            body.index("x86_serial_write_stage_marker('X' as u8)"),
            body.index("x86_serial_write_stage_marker('D' as u8)"),
        )
        self.assertIn("xhci_runtime_prepare()", text)
        self.assertIn("xhci_program_halted_runtime()", text)

    def test_ci_requires_dma_tables_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("for marker in TIMER_READY STEP=T STEP=K STEP=X STEP=D STEP=N", text)
        self.assertIn('grep -q "BAKEN:${marker}" build/qemu-serial.log', text)


if __name__ == "__main__":
    unittest.main()

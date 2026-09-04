#!/usr/bin/env python3
"""Guardrails do primeiro start xHCI + No-op Command DMA real."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "kernel/src/drivers/xhci_start.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


def _code_only(text: str) -> str:
    text = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


class XhciStartTests(unittest.TestCase):
    def test_start_requires_all_halted_runtime_prerequisites(self):
        text = START.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_start_and_prove_noop()", 1)[1]
        self.assertIn("xhci_controller_is_ready()", body)
        self.assertIn("xhci_runtime_is_ready()", body)
        self.assertIn("xhci_program_is_ready()", body)
        self.assertIn("XHCI_USBSTS_HCHALTED", body)

    def test_dma_is_shared_before_bus_master(self):
        text = START.read_text(encoding="utf-8")
        body = text.split("pub fn xhci_start_and_prove_noop()", 1)[1]
        share = body.index("dma_share_with_device(&mut shared)")
        bus_master = body.index("xhci_start_set_bus_master(true)")
        self.assertLess(share, bus_master)
        self.assertIn("dma_buffer_shared(&shared)", body)

    def test_noop_is_published_with_bootstrap_compatible_barrier_before_run(self):
        text = START.read_text(encoding="utf-8")
        publish_fn = text.split("fn xhci_start_publish_noop", 1)[1].split(
            "fn xhci_start_ring_command_doorbell", 1
        )[0]
        self.assertIn("xhci_trb_noop_command(true)", publish_fn)
        self.assertIn("unsafe { *slot = noop; }", publish_fn)
        self.assertIn("x86_read_cr3_raw()", publish_fn)
        self.assertLess(publish_fn.index("*slot = noop"), publish_fn.index("x86_read_cr3_raw()"))
        self.assertNotIn("quench {", text)

        body = text.split("pub fn xhci_start_and_prove_noop()", 1)[1]
        self.assertLess(
            body.index("xhci_start_publish_noop(command_physical)"),
            body.index("XHCI_USBCMD_RUN_STOP"),
        )

    def test_doorbell_and_completion_event_are_both_required(self):
        text = START.read_text(encoding="utf-8")
        self.assertIn("xhci_start_ring_command_doorbell()", text)
        self.assertIn("xhci_start_wait_noop_completion(command_physical)", text)
        self.assertIn("XHCI_TRB_TYPE_COMMAND_COMPLETION_EVENT", text)
        self.assertIn("xhci_event_success(event)", text)
        self.assertIn("xhci_command_completion_trb_pointer(event) != command_physical", text)
        self.assertIn("XHCI_INTR_ERDP", text)

    def test_failure_rolls_back_run_bus_master_and_shared_dma(self):
        text = START.read_text(encoding="utf-8")
        rollback = text.split("fn xhci_start_rollback()", 1)[1].split(
            "pub fn xhci_start_and_prove_noop()", 1
        )[0]
        self.assertIn("xhci_start_stop_controller()", rollback)
        self.assertIn("xhci_start_set_bus_master(false)", rollback)
        self.assertIn("dma_unshare_from_device", rollback)

    def test_xhci_interrupts_are_not_enabled_in_first_dma_proof(self):
        code = _code_only(START.read_text(encoding="utf-8")).lower()
        for forbidden in ("msi", "msix", "xhci_iman_ie", "interrupt_enable"):
            self.assertNotIn(forbidden, code)

    def test_post_cutover_connects_noop_only_after_dma_tables(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertIn("xhci_start_and_prove_noop()", text)
        self.assertIn("post_cutover_start_xhci_and_prove_noop()", text)
        self.assertLess(
            body.index("x86_serial_write_stage_marker('D' as u8)"),
            body.index("x86_serial_write_stage_marker('N' as u8)"),
        )
        self.assertIn("xhci_start_noop_completed()", text)
        self.assertIn("POST_CUTOVER_XHCI_NOOP_LIVE = true", text)


if __name__ == "__main__":
    unittest.main()

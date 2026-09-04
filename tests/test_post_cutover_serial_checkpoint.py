#!/usr/bin/env python3
"""Guardrails do checkpoint serial nativo do bring-up."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERIAL = ROOT / "kernel/src/arch/x86_64/serial.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class PostCutoverSerialCheckpointTests(unittest.TestCase):
    def test_serial_is_native_bounded_and_best_effort(self):
        text = SERIAL.read_text(encoding="utf-8")
        self.assertIn("X86_SERIAL_COM1: u16 = 0x3F8", text)
        self.assertIn("X86_SERIAL_MAX_SPINS", text)
        self.assertIn("__outb", text)
        self.assertIn("__inb", text)
        self.assertNotIn("BootServices", text)
        self.assertNotIn("Stall", text)

    def test_marker_is_emitted_only_after_timer_prepare(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        timer = body.index("post_cutover_prepare_timer()")
        serial = body.index("x86_serial_init()")
        marker = body.index("x86_serial_write_timer_ready_marker()")
        self.assertLess(timer, serial)
        self.assertLess(serial, marker)

    def test_qemu_smoke_requires_actual_post_cutover_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("-no-reboot", text)
        self.assertIn("-serial file:build/qemu-serial.log", text)
        self.assertIn('grep -q "BAKEN:TIMER_READY" build/qemu-serial.log', text)
        self.assertIn('test "$status" -eq 124', text)


if __name__ == "__main__":
    unittest.main()

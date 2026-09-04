#!/usr/bin/env python3
"""Guardrails for the staged native x86-64 timer foundation."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TIMER = ROOT / "kernel/src/arch/x86_64/timer.sotlas"
RUNTIME = ROOT / "kernel/src/baken_runtime.sotlas"


class X86TimerTests(unittest.TestCase):
    def test_timer_owns_calibration_and_cpu_only_wait(self):
        text = TIMER.read_text(encoding="utf-8")
        for token in (
            "TSC_CYCLES_PER_US",
            "TSC_CALIBRATED",
            "pub fn x86_timer_set_cycles_per_us",
            "pub fn x86_timer_elapsed_us",
            "pub fn x86_timer_spin_wait_us",
            "return baken_rdtsc();",
        ):
            self.assertIn(token, text)
        self.assertNotIn("EfiBootServices", text)
        self.assertNotIn("Stall(", text)
        self.assertNotIn("system_table", text)

    def test_runtime_uses_uefi_stall_only_for_transition_calibration(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertEqual(text.count("bs.Stall("), 1)
        self.assertIn("bs.Stall(10000)", text)
        self.assertIn("x86_timer_set_cycles_per_us", text)
        self.assertIn("x86_timer_spin_wait_us(remain)", text)
        self.assertIn("x86_timer_elapsed_us(frame_start, frame_end)", text)
        self.assertNotIn("bs.Stall(remain)", text)
        self.assertNotIn("bs.Stall(15)", text)

    def test_runtime_frame_loop_reads_cpu_timer_directly(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("let frame_start: u64 = x86_timer_read_tsc();", text)
        self.assertIn("desktop_compositor_render_frame();", text)
        self.assertIn("baken_efi_frame_wait(frame_start);", text)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Guardrails for the native x86-64 timer foundation."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TIMER = ROOT / "kernel/src/arch/x86_64/timer.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class X86TimerTests(unittest.TestCase):
    def test_timer_owns_calibration_and_cpu_only_wait(self):
        text = TIMER.read_text(encoding="utf-8")
        for token in ("TSC_CYCLES_PER_US", "TSC_CALIBRATED", "pub fn x86_timer_set_cycles_per_us", "pub fn x86_timer_elapsed_us", "pub fn x86_timer_spin_wait_us", "return baken_rdtsc();"):
            self.assertIn(token, text)
        self.assertNotIn("EfiBootServices", text)
        self.assertNotIn("Stall(", text)
        self.assertNotIn("system_table", text)

    def test_native_runtime_calibrates_without_uefi_stall(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("x86_timer_calibrate_from_acpi_pm()", text)
        self.assertIn("x86_timer_spin_wait_us", text)
        self.assertIn("x86_timer_elapsed_us", text)
        self.assertNotIn("Stall(", text)
        self.assertNotIn("x86_timer_set_cycles_per_us(3000)", text)

    def test_native_runtime_frame_loop_reads_cpu_timer_directly(self):
        text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("let frame_start = x86_timer_read_tsc();", text)
        self.assertIn("desktop_compositor_render_frame();", text)
        self.assertIn("baken_native_frame_wait(frame_start);", text)

    def test_legacy_timer_compatibility_aliases_are_retired(self):
        self.assertFalse((ROOT / "kernel/src/baken_runtime.sotlas").exists())
        code = "\n".join(line.split("//", 1)[0] for text in (TIMER.read_text(encoding="utf-8"), RUNTIME.read_text(encoding="utf-8")) for line in text.splitlines())
        self.assertNotIn("baken_efi_", code)
        self.assertNotIn("BootServices", code)
        self.assertNotIn("Stall(", code)


if __name__ == "__main__":
    unittest.main()

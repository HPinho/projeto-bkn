#!/usr/bin/env python3
"""Guardrails do timer LAPIC pós-cutover."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TIMER = ROOT / "kernel/src/interrupts/lapic_timer.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class LapicTimerTests(unittest.TestCase):
    def test_calibration_uses_native_pm_timer(self):
        text = TIMER.read_text(encoding="utf-8")
        self.assertIn("fadt_pm_timer_init()", text)
        self.assertIn("acpi_pm_timer_read_counter()", text)
        self.assertIn("acpi_pm_timer_elapsed_ticks", text)
        self.assertIn("LAPIC_TIMER_REG_CURRENT_COUNT", text)
        self.assertIn("LAPIC_TIMER_MAX_SPINS", text)

    def test_periodic_timer_remains_masked_after_calibration(self):
        text = TIMER.read_text(encoding="utf-8")
        body = text.split("pub fn lapic_timer_calibrate_masked_from_pm", 1)[1].split("pub fn lapic_timer_is_ready", 1)[0]
        self.assertIn("LAPIC_TIMER_MASKED | LAPIC_TIMER_PERIODIC", body)
        self.assertIn("IRQ_VECTOR_TIMER", body)

    def test_unmask_is_explicit_separate_operation(self):
        text = TIMER.read_text(encoding="utf-8")
        self.assertIn("pub fn lapic_timer_unmask_periodic() -> bool", text)
        unmask = text.split("pub fn lapic_timer_unmask_periodic", 1)[1].split("pub fn lapic_timer_mask", 1)[0]
        self.assertNotIn("LAPIC_TIMER_MASKED", unmask)

    def test_post_cutover_calibrates_but_does_not_enable_interrupts(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        self.assertIn("post_cutover_prepare_timer()", body)
        code = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
        self.assertNotIn("lapic_timer_unmask_periodic()", code)
        self.assertNotIn("__sti(", code)
        self.assertNotIn("x86_sti", code)


if __name__ == "__main__":
    unittest.main()

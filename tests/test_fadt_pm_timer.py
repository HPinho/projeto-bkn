#!/usr/bin/env python3
"""Guardrails do inventário FADT/ACPI PM Timer."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FADT = ROOT / "kernel/src/acpi/fadt.sotlas"
LAPIC_TIMER = ROOT / "kernel/src/interrupts/lapic_timer.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class FadtPmTimerTests(unittest.TestCase):
    def test_extended_pm_timer_is_preferred_over_legacy_block(self):
        text = FADT.read_text(encoding="utf-8")
        extended = text.index("if length >= FADT_X_PM_TMR_END")
        legacy = text.index("let mut pm_timer_len: u8 = 0")
        self.assertLess(extended, legacy)
        self.assertIn("FADT_X_PM_TMR_OFFSET", text)
        self.assertIn("FADT_PM_TMR_BLK_OFFSET", text)
        self.assertIn("pm_timer_len != 4", text)

    def test_hardware_reduced_acpi_disables_fixed_pm_timer(self):
        text = FADT.read_text(encoding="utf-8")
        self.assertIn("FADT_FLAG_HW_REDUCED_ACPI", text)
        self.assertIn("if (flags & FADT_FLAG_HW_REDUCED_ACPI) != 0", text)
        self.assertIn("return false;", text)

    def test_timer_width_and_frequency_match_acpi_contract(self):
        text = FADT.read_text(encoding="utf-8")
        self.assertIn("FADT_FLAG_TMR_VAL_EXT", text)
        self.assertIn("{ 32 } else { 24 }", text)
        self.assertIn("ACPI_PM_TIMER_FREQUENCY_HZ: u64 = 3579545", text)

    def test_inventory_does_not_access_io_or_mmio(self):
        text = FADT.read_text(encoding="utf-8")
        self.assertNotIn("__in", text)
        self.assertNotIn("__out", text)
        self.assertNotIn("mmio_read", text)
        self.assertNotIn("mmio_write", text)
        self.assertNotIn("volatile", text)

    def test_lapic_timer_consumes_fadt_only_after_post_cutover_acpi(self):
        timer = LAPIC_TIMER.read_text(encoding="utf-8")
        self.assertIn("fadt_pm_timer_is_ready()", timer)
        self.assertIn("fadt_pm_timer_init()", timer)
        self.assertIn("acpi_pm_timer_port_ready()", timer)
        post = POST.read_text(encoding="utf-8")
        entry = post.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        acpi = entry.index("post_cutover_activate_acpi(context)")
        timer_stage = entry.index("post_cutover_prepare_timer()", acpi)
        self.assertLess(acpi, timer_stage)


if __name__ == "__main__":
    unittest.main()

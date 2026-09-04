#!/usr/bin/env python3
"""Guardrails da leitura ACPI PM Timer e calibração TSC nativa."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PM = ROOT / "kernel/src/acpi/pm_timer.sotlas"
TIMER = ROOT / "kernel/src/arch/x86_64/timer.sotlas"


class PmTimerCalibrationTests(unittest.TestCase):
    def test_pm_timer_uses_only_x86_system_io(self):
        text = PM.read_text(encoding="utf-8")
        self.assertIn("fadt_pm_timer_address_space() != ACPI_GAS_SYSTEM_IO", text)
        self.assertIn("address > 0xFFFF", text)
        self.assertIn("__inl(port)", text)
        self.assertNotIn("__out", text)
        self.assertNotIn("mmio_read", text)
        self.assertNotIn("mmio_write", text)
        self.assertNotIn("volatile", text)

    def test_24_bit_counter_masks_wraparound(self):
        text = PM.read_text(encoding="utf-8")
        self.assertIn("ACPI_PM_TIMER_MASK_24: u32 = 0x00FFFFFF", text)
        self.assertIn("return (current - start) & ACPI_PM_TIMER_MASK_24", text)
        self.assertIn("bits == 24 || bits == 32", text)

    def test_tsc_calibration_uses_native_pm_reference_only(self):
        text = TIMER.read_text(encoding="utf-8")
        self.assertIn("x86_timer_calibrate_from_acpi_pm", text)
        self.assertIn("acpi_pm_timer_read_counter", text)
        self.assertIn("acpi_pm_timer_elapsed_ticks", text)
        self.assertIn("TSC_PM_CALIBRATION_MAX_SPINS", text)
        self.assertIn("x86_timer_set_cycles_per_us(cycles_per_us)", text)
        self.assertNotIn("Stall", text.replace("UEFI Stall continua apenas como", ""))
        self.assertNotIn("BootServices", text)
        self.assertNotIn("baken_efi", text)

    def test_calibration_rounds_instead_of_truncating(self):
        text = TIMER.read_text(encoding="utf-8")
        self.assertIn("let numerator = tsc_delta * frequency", text)
        self.assertIn("(numerator + (denominator / 2)) / denominator", text)

    def test_calibration_has_bounded_failure_path(self):
        text = TIMER.read_text(encoding="utf-8")
        self.assertIn("while spins < TSC_PM_CALIBRATION_MAX_SPINS", text)
        self.assertIn("if (elapsed_ticks as u64) < target_ticks { return false; }", text)
        self.assertIn("if tsc_finish <= tsc_start { return false; }", text)


if __name__ == "__main__":
    unittest.main()

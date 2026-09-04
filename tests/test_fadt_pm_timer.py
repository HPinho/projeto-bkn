#!/usr/bin/env python3
"""Guardrails do inventário FADT/ACPI PM Timer."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FADT = ROOT / "kernel/src/acpi/fadt.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


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

    def test_main_initializes_fadt_only_inside_valid_acpi_block(self):
        text = MAIN.read_text(encoding="utf-8")
        acpi_start = text.index("if acpi_init(boot_info.acpi_rsdp) {")
        pci_start = text.index("pci_scan_all();")
        block = text[acpi_start:pci_start]
        self.assertIn("fadt_pm_timer_init();", block)
        self.assertLess(block.index("hpet_init();"), block.index("fadt_pm_timer_init();"))


if __name__ == "__main__":
    unittest.main()

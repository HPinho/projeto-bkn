#!/usr/bin/env python3
"""Guardrails do inventário HPET passivo do Baken OS."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HPET = ROOT / "kernel/src/acpi/hpet.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class HpetInventoryTests(unittest.TestCase):
    def test_hpet_comes_only_from_validated_acpi_table(self):
        text = HPET.read_text(encoding="utf-8")
        self.assertIn("let table = acpi_hpet();", text)
        self.assertIn("HPET_TABLE_MIN_LENGTH", text)
        self.assertIn("ACPI_ADDRESS_SPACE_SYSTEM_MEMORY", text)
        self.assertIn("base_address == 0", text)

    def test_hpet_parses_capabilities_without_touching_mmio(self):
        text = HPET.read_text(encoding="utf-8")
        self.assertIn("comparator_count", text)
        self.assertIn("counter_size_64", text)
        self.assertIn("minimum_tick", text)
        self.assertNotIn("volatile", text)
        self.assertNotIn("mmio_write", text)
        self.assertNotIn("mmio_read", text)
        self.assertNotIn("__out", text)
        self.assertNotIn("__wrmsr", text)
        self.assertNotIn("__sti", text)

    def test_main_initializes_hpet_only_after_acpi_success(self):
        text = MAIN.read_text(encoding="utf-8")
        acpi_start = text.index("if acpi_init(boot_info.acpi_rsdp) {")
        pci_start = text.index("pci_scan_all();")
        block = text[acpi_start:pci_start]
        self.assertIn("hpet_init();", block)
        self.assertLess(block.index("madt_init();"), block.index("hpet_init();"))


if __name__ == "__main__":
    unittest.main()

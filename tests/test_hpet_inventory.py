#!/usr/bin/env python3
"""Guardrails do inventário HPET passivo do Baken OS."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HPET = ROOT / "kernel/src/acpi/hpet.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


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

    def test_hpet_inventory_is_optional_not_a_post_cutover_boot_gate(self):
        post = POST.read_text(encoding="utf-8")
        self.assertIn("acpi_init_post_cutover(rsdp)", post)
        self.assertNotIn("hpet_init();", post)
        self.assertIn("pub fn hpet_init()", HPET.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

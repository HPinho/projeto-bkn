#!/usr/bin/env python3
"""Guardrails para inventário ACPI MCFG e cálculo ECAM."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MCFG = ROOT / "kernel/src/acpi/mcfg.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
PCI = ROOT / "kernel/src/drivers/pci_bus.sotlas"


class AcpiMcfgTests(unittest.TestCase):
    def test_mcfg_parses_16_byte_allocation_entries(self):
        text = MCFG.read_text(encoding="utf-8")
        self.assertIn("MCFG_ENTRY_SIZE: usize = 16", text)
        self.assertIn("MCFG_ENTRIES_OFFSET: usize = 44", text)
        self.assertIn("segment_group", text)
        self.assertIn("start_bus", text)
        self.assertIn("end_bus", text)
        self.assertIn("if (payload % MCFG_ENTRY_SIZE) != 0", text)

    def test_ecam_address_formula_uses_segment_relative_bus(self):
        text = MCFG.read_text(encoding="utf-8")
        self.assertIn("let relative_bus = (bus - entry.start_bus) as u64", text)
        self.assertIn("(relative_bus << 20)", text)
        self.assertIn("((device as u64) << 15)", text)
        self.assertIn("((function as u64) << 12)", text)
        self.assertIn("(offset as u64)", text)

    def test_mcfg_does_not_access_ecam_or_program_pci(self):
        text = MCFG.read_text(encoding="utf-8")
        for forbidden in ("__in", "__out", "pci_write", "pci_enable", "volatile"): self.assertNotIn(forbidden, text)

    def test_mcfg_inventory_is_optional_while_native_pci_uses_legacy_config_io(self):
        mcfg = MCFG.read_text(encoding="utf-8")
        post = POST.read_text(encoding="utf-8")
        self.assertIn("pub fn mcfg_init() -> bool", mcfg)
        self.assertIn("pci_scan_all()", post)
        self.assertNotIn("mcfg_init();", post)

    def test_legacy_pci_mechanism_remains_until_vmm_ecam_cutover(self):
        text = PCI.read_text(encoding="utf-8")
        self.assertIn("PCI_CONFIG_ADDRESS_PORT", text)
        self.assertIn("PCI_CONFIG_DATA_PORT", text)
        self.assertNotIn("mcfg_ecam_address", text)


if __name__ == "__main__":
    unittest.main()

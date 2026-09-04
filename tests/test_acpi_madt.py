#!/usr/bin/env python3
"""Guardrails para inventário MADT e mapeamento IRQ -> GSI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MADT = ROOT / "kernel/src/acpi/madt.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
I8042 = ROOT / "kernel/src/drivers/i8042.sotlas"


class AcpiMadtTests(unittest.TestCase):
    def test_parser_handles_ioapic_iso_and_lapic_override(self):
        text = MADT.read_text(encoding="utf-8")
        for token in (
            "MADT_ENTRY_IO_APIC: u8 = 1",
            "MADT_ENTRY_INTERRUPT_OVERRIDE: u8 = 2",
            "MADT_ENTRY_LOCAL_APIC_ADDRESS_OVERRIDE: u8 = 5",
            "MADT_LAPIC_ADDRESS",
            "MADT_IOAPICS",
            "MADT_OVERRIDES",
        ):
            self.assertIn(token, text)

    def test_irq_mapping_uses_iso_and_has_identity_fallback(self):
        text = MADT.read_text(encoding="utf-8")
        self.assertIn("pub fn madt_irq_to_gsi(irq: u8) -> u32", text)
        self.assertIn("entry.bus == 0 && entry.source_irq == irq", text)
        self.assertIn("return entry.gsi;", text)
        self.assertIn("return irq as u32;", text)
        self.assertIn("pub fn madt_irq_flags", text)

    def test_madt_is_initialized_only_after_valid_acpi_root(self):
        text = MAIN.read_text(encoding="utf-8")
        acpi_pos = text.index("if acpi_init(boot_info.acpi_rsdp)")
        madt_pos = text.index("madt_init();")
        self.assertLess(acpi_pos, madt_pos)

    def test_parser_does_not_enable_interrupts_or_write_mmio(self):
        text = MADT.read_text(encoding="utf-8")
        for forbidden in ("__sti", "__out", "__wrmsr", "pci_write", "ioapic_write", "lapic_write"):
            self.assertNotIn(forbidden, text)

    def test_i8042_irqs_remain_staged_until_ioapic_cutover(self):
        text = I8042.read_text(encoding="utf-8")
        self.assertIn("pub fn i8042_enable_native_irqs()", text)
        main = MAIN.read_text(encoding="utf-8")
        self.assertNotIn("i8042_enable_native_irqs(", main)


if __name__ == "__main__":
    unittest.main()

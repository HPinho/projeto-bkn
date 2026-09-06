#!/usr/bin/env python3
"""Guardrails da raiz ACPI validada do Baken OS."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACPI = ROOT / "kernel/src/acpi/tables.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class AcpiTableTests(unittest.TestCase):
    def test_rsdp_signature_and_both_checksums_are_required(self):
        text = ACPI.read_text(encoding="utf-8")
        self.assertIn("acpi_rsdp_signature_valid", text)
        self.assertIn("acpi_checksum_zero(rsdp, ACPI_RSDP_V1_LENGTH)", text)
        self.assertIn("acpi_checksum_zero(rsdp, rsdp_length)", text)
        self.assertIn("ACPI_RSDP_V2_MIN_LENGTH", text)

    def test_xsdt_is_preferred_and_rsdt_is_fallback(self):
        text = ACPI.read_text(encoding="utf-8")
        xsdt = text.index("let xsdt_address = acpi_read_u64(rsdp, 24)")
        rsdt = text.index("let rsdt_address = acpi_read_u32(rsdp, 16)")
        self.assertLess(xsdt, rsdt)
        self.assertIn("ACPI_ROOT_ENTRY_SIZE = 8", text)
        self.assertIn("ACPI_ROOT_ENTRY_SIZE = 4", text)

    def test_every_returned_sdt_is_checksum_validated(self):
        text = ACPI.read_text(encoding="utf-8")
        self.assertIn("acpi_sdt_valid(table, signature)", text)
        self.assertIn("ACPI_MAX_SDT_LENGTH", text)
        for signature in ("ACPI_SIG_MADT", "ACPI_SIG_MCFG", "ACPI_SIG_HPET", "ACPI_SIG_FADT"): self.assertIn(signature, text)

    def test_post_cutover_initializes_acpi_before_interrupt_controllers_and_pci(self):
        text = POST.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::tables::*;", text)
        acpi_body = text.split("pub fn post_cutover_activate_acpi", 1)[1].split("pub fn post_cutover_acpi_ready", 1)[0]
        self.assertIn("acpi_init_post_cutover(rsdp)", acpi_body)
        self.assertIn("acpi_uses_post_cutover_direct_map()", acpi_body)
        self.assertIn("madt_init()", acpi_body)
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        acpi = entry.index("post_cutover_activate_acpi(context)")
        controllers = entry.index("post_cutover_activate_interrupt_controllers()", acpi)
        xhci = entry.index("post_cutover_prepare_xhci_controller()", controllers)
        self.assertLess(acpi, controllers)
        self.assertLess(controllers, xhci)

    def test_acpi_layer_is_read_only(self):
        text = ACPI.read_text(encoding="utf-8")
        self.assertNotIn("__out", text)
        self.assertNotIn("pci_write", text)
        self.assertNotIn("__wrmsr", text)
        self.assertNotIn("__sti", text)


if __name__ == "__main__":
    unittest.main()

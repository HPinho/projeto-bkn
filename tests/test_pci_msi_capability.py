#!/usr/bin/env python3
"""DF-6a: modelo MSI deve ser bounded, fail-closed e estritamente read-only."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPS = (ROOT / "kernel/src/drivers/pci_capabilities.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsiCapabilityTests(unittest.TestCase):
    def _probe_body(self):
        return CAPS.split("pub fn pci_msi_capability_probe", 1)[1]

    def test_df6a_lives_in_already_linked_capability_module(self):
        self.assertIn("module kernel::drivers::pci_capabilities;", CAPS)
        self.assertIn("import kernel::drivers::pci_capabilities::*;", MAIN)
        self.assertIn("pub struct PciMsiCapability", CAPS)
        self.assertIn("pub fn pci_msi_capability_probe", CAPS)

    def test_msi_control_bits_match_pci_layout(self):
        for token in (
            "PCI_MSI_CONTROL_ENABLE: u16 = 0x0001",
            "PCI_MSI_CONTROL_MMC_MASK: u16 = 0x000E",
            "PCI_MSI_CONTROL_MME_MASK: u16 = 0x0070",
            "PCI_MSI_CONTROL_64BIT: u16 = 0x0080",
            "PCI_MSI_CONTROL_PVM: u16 = 0x0100",
            "PCI_MSI_MAX_VECTOR_ENCODING: u8 = 5",
        ):
            self.assertIn(token, CAPS)

    def test_vector_encoding_is_bounded_to_one_through_32_messages(self):
        body = CAPS.split("fn pci_msi_vector_count", 1)[1].split("\n@system", 1)[0]
        for encoding, count in ((0, 1), (1, 2), (2, 4), (3, 8), (4, 16), (5, 32)):
            self.assertIn(f"encoding == {encoding} {{ return {count}; }}", body)
        self.assertIn("return 0;", body)

    def test_probe_uses_df5c_walker_and_revalidates_identity(self):
        body = self._probe_body()
        self.assertIn("pci_capability_find(segment, bus, slot, func, PCI_CAP_ID_MSI)", body)
        self.assertIn("capability.id != PCI_CAP_ID_MSI as u16", body)
        self.assertIn("pci_config_read16(segment, bus, slot, func, capability.offset)", body)
        self.assertIn("revalidated_next != capability.next_offset", body)
        self.assertIn("header == 0xFFFF", body)

    def test_reserved_or_impossible_multi_message_state_fails_closed(self):
        body = self._probe_body()
        self.assertIn("mmc > PCI_MSI_MAX_VECTOR_ENCODING", body)
        self.assertIn("mme > PCI_MSI_MAX_VECTOR_ENCODING", body)
        self.assertIn("mme > mmc", body)
        self.assertIn("return pci_msi_capability_invalid();", body)

    def test_32_and_64_bit_layouts_include_optional_masking(self):
        for token in (
            "PCI_MSI_ADDRESS_LOW_REL: u16 = 0x0004",
            "PCI_MSI_ADDRESS_HIGH_64_REL: u16 = 0x0008",
            "PCI_MSI_DATA_32_REL: u16 = 0x0008",
            "PCI_MSI_DATA_64_REL: u16 = 0x000C",
            "PCI_MSI_MASK_32_REL: u16 = 0x000C",
            "PCI_MSI_PENDING_32_REL: u16 = 0x0010",
            "PCI_MSI_MASK_64_REL: u16 = 0x0010",
            "PCI_MSI_PENDING_64_REL: u16 = 0x0014",
        ):
            self.assertIn(token, CAPS)
        layout = CAPS.split("fn pci_msi_last_relative_offset", 1)[1].split("\n@system", 1)[0]
        self.assertIn("return 0x0017", layout)
        self.assertIn("return 0x000D", layout)
        self.assertIn("return 0x0013", layout)
        self.assertIn("return 0x0009", layout)

    def test_layout_cannot_run_past_conventional_config_space(self):
        body = self._probe_body()
        self.assertIn("PCI_CONFIG_LEGACY_MAX_OFFSET - last_relative", body)
        self.assertIn("capability.offset > PCI_CONFIG_LEGACY_MAX_OFFSET - last_relative", body)
        self.assertIn("last_offset: capability.offset + last_relative", body)

    def test_df6a_does_not_program_or_route_interrupts(self):
        body = self._probe_body()
        for forbidden in (
            "pci_config_write",
            "pci_config_set16_bits",
            "irq_registry_register",
            "irq_registry_unregister",
            "lapic_",
            "ioapic_",
            "idt_",
            "eoi",
            "pci_enable_bus_master",
            "pci_enable_memory",
        ):
            self.assertNotIn(forbidden, body)

    def test_df6a_does_not_add_boot_time_invocation(self):
        self.assertNotIn("pci_msi_capability_probe(", MAIN)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""DF-6b: reserva MSI deve reutilizar o IRQ Registry sem programar hardware."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsiReservationTests(unittest.TestCase):
    def _body(self, name: str) -> str:
        return BRIDGE.split(f"pub fn {name}", 1)[1].split("\n@system", 1)[0]

    def test_bridge_reuses_capability_and_generic_irq_foundations(self):
        self.assertIn("import kernel::drivers::pci_capabilities::*;", BRIDGE)
        self.assertIn("import kernel::interrupts::registry::*;", BRIDGE)
        self.assertIn("pub struct PciMsiReservation", BRIDGE)
        for field in (
            "pub irq: IrqHandle",
            "pub vector: u16",
            "pub bdf: u32",
            "pub capability_offset: u16",
            "pub max_vectors: u16",
            "pub valid: bool",
        ):
            self.assertIn(field, BRIDGE)

    def test_reservation_is_single_vector_and_irq_registry_is_authoritative(self):
        body = self._body("pci_msi_reserve_single")
        self.assertIn("pci_bridge_owned_device", body)
        self.assertIn("pci_msi_capability_probe", body)
        self.assertIn("capability.enabled", body)
        self.assertIn("irq_registry_register(device, driver, descriptor)", body)
        self.assertIn("irq_registry_vector(irq)", body)
        self.assertIn("IRQ_DYNAMIC_VECTOR_FIRST", body)
        self.assertIn("IRQ_DYNAMIC_VECTOR_LAST", body)
        self.assertNotIn("resource_claim", body)

    def test_reservation_never_programs_msi_or_interrupt_hardware(self):
        body = self._body("pci_msi_reserve_single")
        for forbidden in (
            "pci_config_write",
            "pci_config_set16_bits",
            "x86_mmio_write",
            "lapic_",
            "ioapic_",
            "idt_set",
            "MSI_CONTROL_ENABLE",
        ):
            self.assertNotIn(forbidden, body)

    def test_reservation_revalidates_after_irq_claim_and_rolls_back(self):
        body = self._body("pci_msi_reserve_single")
        self.assertGreaterEqual(body.count("pci_bridge_owned_device"), 2)
        self.assertGreaterEqual(body.count("pci_msi_capability_probe"), 2)
        self.assertIn("verify.capability_offset != capability.capability_offset", body)
        self.assertIn("verify.control != capability.control", body)
        self.assertIn("verify.address_64 != capability.address_64", body)
        self.assertIn("verify.per_vector_masking != capability.per_vector_masking", body)
        self.assertIn("verify.max_vectors != capability.max_vectors", body)
        self.assertGreaterEqual(body.count("irq_registry_unregister"), 3)

    def test_release_path_allows_unbinding_but_claim_path_does_not(self):
        claim_owner = BRIDGE.split("fn pci_bridge_owned_device(", 1)[1].split("\n@system", 1)[0]
        release_owner = BRIDGE.split("fn pci_bridge_owned_device_for_release", 1)[1].split("\n@system", 1)[0]
        self.assertNotIn("DEVICE_STATE_UNBINDING", claim_owner)
        self.assertIn("DEVICE_STATE_BINDING", release_owner)
        self.assertIn("DEVICE_STATE_ACTIVE", release_owner)
        self.assertIn("DEVICE_STATE_UNBINDING", release_owner)

    def test_unarmed_release_refuses_to_free_live_enabled_source(self):
        body = self._body("pci_msi_release_unarmed_reservation")
        self.assertIn("pci_bridge_owned_device_for_release", body)
        self.assertIn("irq_registry_vector(reservation.irq) != reservation.vector", body)
        self.assertIn("capability.capability_offset != reservation.capability_offset", body)
        self.assertIn("capability.enabled", body)
        self.assertIn("irq_registry_unregister(reservation.irq, device, driver)", body)
        self.assertLess(body.index("capability.enabled"), body.index("irq_registry_unregister"))

    def test_df6b_adds_no_boot_path_invocation_or_parallel_msi_registry(self):
        self.assertNotIn("pci_msi_reserve_single(", MAIN)
        self.assertNotIn("static mut PCI_MSI_", BRIDGE)
        self.assertEqual(BRIDGE.count("pub fn pci_msi_reserve_single"), 1)


if __name__ == "__main__":
    unittest.main()

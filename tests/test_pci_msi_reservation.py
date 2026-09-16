#!/usr/bin/env python3
"""DF-6b: reserva MSI deve reutilizar Resource/IRQ foundations sem programar hardware."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsiReservationTests(unittest.TestCase):
    def _body(self, name: str) -> str:
        return BRIDGE.split(f"pub fn {name}", 1)[1].split("\n@system", 1)[0]

    def test_bridge_reuses_capability_resource_and_generic_irq_foundations(self):
        self.assertIn("import kernel::drivers::pci_capabilities::*;", BRIDGE)
        self.assertIn("import kernel::device::resource_manager::*;", BRIDGE)
        self.assertIn("import kernel::interrupts::registry::*;", BRIDGE)
        self.assertIn("pub struct PciMsiReservation", BRIDGE)
        for field in (
            "pub source: ResourceHandle",
            "pub irq: IrqHandle",
            "pub vector: u16",
            "pub bdf: u32",
            "pub capability_offset: u16",
            "pub max_vectors: u16",
            "pub valid: bool",
        ):
            self.assertIn(field, BRIDGE)

    def test_reservation_claims_source_before_irq_and_irq_registry_owns_vector(self):
        body = self._body("pci_msi_reserve_single")
        self.assertIn("pci_bridge_owned_device", body)
        self.assertIn("pci_msi_capability_probe", body)
        self.assertIn("capability.enabled", body)
        self.assertIn("kind: RESOURCE_KIND_PCI_MSI", body)
        self.assertIn("resource_claim(device, driver", body)
        self.assertIn("irq_registry_register(device, driver, descriptor)", body)
        self.assertLess(body.index("kind: RESOURCE_KIND_PCI_MSI"), body.index("irq_registry_register"))
        self.assertIn("irq_registry_vector(irq)", body)
        self.assertIn("IRQ_DYNAMIC_VECTOR_FIRST", body)
        self.assertIn("IRQ_DYNAMIC_VECTOR_LAST", body)
        self.assertNotIn("kind: RESOURCE_KIND_IRQ", body)

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

    def test_reservation_revalidates_source_device_and_capability(self):
        body = self._body("pci_msi_reserve_single")
        self.assertGreaterEqual(body.count("pci_bridge_owned_device"), 2)
        self.assertGreaterEqual(body.count("pci_msi_capability_probe"), 2)
        self.assertIn("resource_snapshot(source)", body)
        self.assertIn("verify_source.request.kind != RESOURCE_KIND_PCI_MSI", body)
        self.assertIn("verify_source.request.start != bdf as u64", body)
        self.assertIn("verify.capability_offset != capability.capability_offset", body)
        self.assertIn("verify.control != capability.control", body)
        self.assertIn("verify.address_64 != capability.address_64", body)
        self.assertIn("verify.per_vector_masking != capability.per_vector_masking", body)
        self.assertIn("verify.max_vectors != capability.max_vectors", body)
        self.assertGreaterEqual(body.count("pci_msi_rollback_unarmed_claims"), 4)

    def test_rollback_is_irq_then_source_and_retains_source_if_irq_release_fails(self):
        body = BRIDGE.split("fn pci_msi_rollback_unarmed_claims", 1)[1].split("\n@system", 1)[0]
        irq = "irq_registry_unregister(irq, device, driver)"
        source = "resource_release(source, device, driver)"
        self.assertIn(irq, body)
        self.assertIn(source, body)
        self.assertLess(body.index(irq), body.index(source))
        self.assertIn("if irq.valid && !irq_registry_unregister", body)

    def test_release_path_allows_unbinding_but_claim_path_does_not(self):
        claim_owner = BRIDGE.split("fn pci_bridge_owned_device(", 1)[1].split("\n@system", 1)[0]
        release_owner = BRIDGE.split("fn pci_bridge_owned_device_for_release", 1)[1].split("\n@system", 1)[0]
        self.assertNotIn("DEVICE_STATE_UNBINDING", claim_owner)
        self.assertIn("DEVICE_STATE_BINDING", release_owner)
        self.assertIn("DEVICE_STATE_ACTIVE", release_owner)
        self.assertIn("DEVICE_STATE_UNBINDING", release_owner)

    def test_unarmed_release_verifies_source_then_quiescence_then_releases_reverse_order(self):
        body = self._body("pci_msi_release_unarmed_reservation")
        self.assertIn("resource_snapshot(reservation.source)", body)
        self.assertIn("source.request.kind != RESOURCE_KIND_PCI_MSI", body)
        self.assertIn("pci_bridge_owned_device_for_release", body)
        self.assertIn("irq_registry_vector(reservation.irq) != reservation.vector", body)
        self.assertIn("capability.capability_offset != reservation.capability_offset", body)
        self.assertIn("capability.enabled", body)
        irq = "irq_registry_unregister(reservation.irq, device, driver)"
        source = "resource_release(reservation.source, device, driver)"
        self.assertIn(irq, body)
        self.assertIn(source, body)
        self.assertLess(body.index("capability.enabled"), body.index(irq))
        self.assertLess(body.index(irq), body.index(source))

    def test_df6b_adds_no_boot_path_invocation_or_parallel_msi_registry(self):
        self.assertNotIn("pci_msi_reserve_single(", MAIN)
        self.assertNotIn("static mut PCI_MSI_", BRIDGE)
        self.assertEqual(BRIDGE.count("pub fn pci_msi_reserve_single"), 1)


if __name__ == "__main__":
    unittest.main()

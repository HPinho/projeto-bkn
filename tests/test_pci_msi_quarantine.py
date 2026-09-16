#!/usr/bin/env python3
"""DF-6b: incerteza de quiescencia deve reter ownership em quarentena."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")


class PciMsiQuarantineTests(unittest.TestCase):
    def _fn(self, marker: str) -> str:
        return BRIDGE.split(marker, 1)[1].split("\n@system", 1)[0]

    def test_quiescence_requires_live_same_capability_and_disabled_source(self):
        body = self._fn("fn pci_msi_quiescence_proven")
        for token in (
            "pci == (null as *const PciDevice)",
            "pci_bdf_pack(0, bus, slot_id, func) != bdf",
            "pci_msi_capability_probe",
            "capability.valid",
            "capability.capability_offset == capability_offset",
            "capability.max_vectors == max_vectors",
            "!capability.enabled",
        ):
            self.assertIn(token, body)

    def test_cleanup_proves_quiescence_before_any_release(self):
        body = self._fn("fn pci_msi_cleanup_unarmed_claims")
        proof = body.index("pci_msi_quiescence_proven")
        irq = body.index("irq_registry_unregister")
        source = body.index("resource_release")
        self.assertLess(proof, irq)
        self.assertLess(proof, source)
        self.assertLess(irq, source)

    def test_cleanup_quarantines_on_failed_irq_or_source_release(self):
        body = self._fn("fn pci_msi_cleanup_unarmed_claims")
        self.assertIn("if !irq_registry_unregister", body)
        self.assertIn("if !resource_release", body)
        self.assertGreaterEqual(body.count("pci_msi_quarantined_reservation"), 5)
        self.assertIn("remaining_irq = irq_invalid_handle()", body)
        self.assertIn("remaining_vector = 0", body)

    def test_final_verify_failure_cannot_blindly_release_enabled_source(self):
        body = self._fn("pub fn pci_msi_reserve_single")
        final = body.split("if !verify.valid || verify.enabled ||", 1)[1]
        self.assertIn("return pci_msi_cleanup_unarmed_claims(", final)
        cleanup = self._fn("fn pci_msi_cleanup_unarmed_claims")
        self.assertIn("if !pci_msi_quiescence_proven", cleanup)
        self.assertNotIn("pci_msi_rollback_unarmed_claims", BRIDGE)

    def test_retry_api_preserves_quarantine_until_proof_succeeds(self):
        body = self._fn("pub fn pci_msi_retry_quarantined_cleanup")
        self.assertIn("pci_msi_reservation_is_quarantined", body)
        self.assertIn("pci_bridge_owned_device_for_release", body)
        self.assertIn("return reservation", body)
        self.assertIn("pci_msi_cleanup_unarmed_claims", body)

    def test_future_armability_has_explicit_ready_predicate(self):
        body = self._fn("pub fn pci_msi_reservation_is_ready")
        self.assertIn("reservation.state == PCI_MSI_RESERVATION_READY", body)
        self.assertIn("reservation.source.valid && reservation.irq.valid", body)


if __name__ == "__main__":
    unittest.main()

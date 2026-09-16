#!/usr/bin/env python3
"""DF-6b correction: unarmed MSI release must prove the source is quiescent."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")


class PciMsiReleaseFailClosedTests(unittest.TestCase):
    def test_release_requires_live_pci_identity_and_valid_msi_probe(self):
        body = BRIDGE.split("pub fn pci_msi_release_unarmed_reservation", 1)[1]
        self.assertIn("if pci == (null as *const PciDevice) { return false; }", body)
        self.assertIn("if !capability.valid ||", body)
        self.assertIn("capability.capability_offset != reservation.capability_offset", body)
        self.assertIn("capability.max_vectors != reservation.max_vectors", body)
        self.assertIn("capability.enabled", body)
        self.assertLess(body.index("if !capability.valid ||"), body.index("irq_registry_unregister"))

    def test_release_has_no_invalid_probe_bypass(self):
        body = BRIDGE.split("pub fn pci_msi_release_unarmed_reservation", 1)[1]
        self.assertNotIn("if capability.valid {", body)
        self.assertNotIn("if pci != (null as *const PciDevice) {", body)


if __name__ == "__main__":
    unittest.main()

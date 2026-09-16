#!/usr/bin/env python3
"""DF-6b: release nao pode liberar MSI sem prova positiva de quiescencia."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")


class PciMsiReleaseFailClosedTests(unittest.TestCase):
    def test_release_delegates_to_quiescence_gated_cleanup(self):
        body = BRIDGE.split("pub fn pci_msi_release_unarmed_reservation", 1)[1].split("\n@system", 1)[0]
        self.assertIn("pci_msi_reservation_is_ready", body)
        self.assertIn("pci_bridge_owned_device_for_release", body)
        self.assertIn("pci_msi_cleanup_unarmed_claims", body)
        self.assertNotIn("irq_registry_unregister", body)
        self.assertNotIn("resource_release(", body)

    def test_no_invalid_probe_bypass_exists_in_cleanup(self):
        cleanup = BRIDGE.split("fn pci_msi_cleanup_unarmed_claims", 1)[1].split("\n@system", 1)[0]
        self.assertIn("if !pci_msi_quiescence_proven", cleanup)
        self.assertLess(cleanup.index("if !pci_msi_quiescence_proven"),
                        cleanup.index("irq_registry_unregister"))


if __name__ == "__main__":
    unittest.main()

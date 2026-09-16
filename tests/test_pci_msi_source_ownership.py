#!/usr/bin/env python3
"""DF-6b: Resource Manager deve serializar ownership da fonte PCI MSI por BDF."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = (ROOT / "kernel/src/device/types.sotlas").read_text(encoding="utf-8")
MANAGER = (ROOT / "kernel/src/device/resource_manager.sotlas").read_text(encoding="utf-8")
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")


class PciMsiSourceOwnershipTests(unittest.TestCase):
    def test_pci_msi_has_dedicated_logical_resource_kind(self):
        self.assertIn("RESOURCE_KIND_PCI_MSI: u8 = 6", TYPES)
        self.assertIn("request.kind > RESOURCE_KIND_PCI_MSI", MANAGER)
        msi_valid = MANAGER.split("if request.kind == RESOURCE_KIND_PCI_MSI", 1)[1].split("}", 1)[0]
        self.assertIn("request.length == 1", msi_valid)
        self.assertIn("request.auxiliary == 0", msi_valid)

    def test_same_bdf_msi_claims_conflict_in_generic_resource_manager(self):
        conflict = MANAGER.split("fn resource_requests_conflict", 1)[1].split("\n@system", 1)[0]
        self.assertIn("left.kind == RESOURCE_KIND_IRQ || left.kind == RESOURCE_KIND_PCI_MSI", conflict)
        self.assertIn("return left.start == right.start", conflict)

    def test_bridge_keys_source_claim_by_bdf_and_keeps_vector_in_irq_registry(self):
        body = BRIDGE.split("pub fn pci_msi_reserve_single", 1)[1].split("\n@system", 1)[0]
        self.assertIn("kind: RESOURCE_KIND_PCI_MSI", body)
        self.assertIn("start: bdf as u64", body)
        self.assertIn("length: 1", body)
        self.assertIn("auxiliary: 0", body)
        self.assertIn("irq_registry_register(device, driver, descriptor)", body)
        self.assertNotIn("kind: RESOURCE_KIND_IRQ", body)


if __name__ == "__main__":
    unittest.main()

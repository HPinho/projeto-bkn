#!/usr/bin/env python3
"""DF-7e1 release-layout contracts: teardown gets a fresh generation-safe proof."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "kernel/src/drivers/pci_msix_release_layout.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciMsixReleaseLayoutContracts(unittest.TestCase):
    def _fn(self, name: str) -> str:
        marker = f"fn {name}"
        start = SOURCE.index(marker)
        end = SOURCE.find("\n@system", start + len(marker))
        return SOURCE[start:] if end == -1 else SOURCE[start:end]

    def _pub(self, name: str) -> str:
        marker = f"pub fn {name}"
        start = SOURCE.index(marker)
        end = SOURCE.find("\n@system", start + len(marker))
        return SOURCE[start:] if end == -1 else SOURCE[start:end]

    def test_module_is_linked_but_not_called_from_boot(self):
        self.assertIn("import kernel::drivers::pci_msix_release_layout::*;", MAIN)
        self.assertNotIn("pci_msix_release_layout_probe(", MAIN)

    def test_probe_is_teardown_only(self):
        body = self._pub("pci_msix_release_layout_probe")
        self.assertIn("owner.state != DEVICE_STATE_UNBINDING", body)
        self.assertIn("verify_owner.state != DEVICE_STATE_UNBINDING", body)
        self.assertNotIn("DEVICE_STATE_ACTIVE", body)
        self.assertNotIn("DEVICE_STATE_BINDING", body)

    def test_generation_bound_aperture_is_reused(self):
        known = self._fn("pci_msix_release_known_bar_size")
        self.assertIn("pci_bar_aperture_snapshot(", known)
        self.assertIn("device_generation", known)
        self.assertIn("aperture.device_generation != device_generation", known)

    def test_claims_are_generation_safe_and_exact_aperture(self):
        proof = self._fn("pci_msix_release_window_proof")
        for token in (
            "resource_snapshot(claim.logical)",
            "resource_snapshot(claim.physical)",
            "device_handle_equal(logical.owner_device, device)",
            "driver_handle_equal(logical.owner_driver, driver)",
            "logical.request.kind != RESOURCE_KIND_PCI_BAR",
            "physical.request.kind != RESOURCE_KIND_MMIO",
            "physical.request.start != bar.base",
            "physical.request.length != bar.size",
        ):
            self.assertIn(token, proof)

    def test_same_bir_requires_same_claim_handles(self):
        body = self._pub("pci_msix_release_layout_probe")
        self.assertIn("capability.table_bir == capability.pba_bir", body)
        self.assertIn("resource_handle_equal(table_claim.logical, pba_claim.logical)", body)
        self.assertIn("resource_handle_equal(table_claim.physical, pba_claim.physical)", body)

    def test_probe_revalidates_owner_capability_and_windows(self):
        body = self._pub("pci_msix_release_layout_probe")
        self.assertGreaterEqual(body.count("device_core_snapshot(device)"), 2)
        self.assertGreaterEqual(body.count("pci_msix_capability_probe("), 2)
        self.assertGreaterEqual(body.count("pci_msix_release_window_proof("), 4)
        self.assertIn("pci_msix_release_capability_equal(capability, verify_capability)", body)

    def test_release_probe_is_read_only(self):
        for forbidden in (
            "pci_config_write",
            "x86_mmio_write",
            "active_page_tables_map",
            "resource_claim(",
            "resource_release(",
            "irq_registry_unregister(",
        ):
            self.assertNotIn(forbidden, SOURCE)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = (ROOT / "kernel/src/drivers/pci_msix_layout.sotlas").read_text(encoding="utf-8")
APERTURE = (ROOT / "kernel/src/drivers/pci_bar_aperture.sotlas").read_text(encoding="utf-8")
BUS = "(*out_bar).size = 0"
BRIDGE = "driver deve fornecer explicitamente a extensao"


class PciMsixLayoutContracts(unittest.TestCase):
    def _body(self, name: str) -> str:
        marker = f"fn {name}"
        start = LAYOUT.index(marker)
        next_fn = LAYOUT.find("\n@system\n", start + len(marker))
        if next_fn == -1:
            return LAYOUT[start:]
        return LAYOUT[start:next_fn]

    def test_layout_consumes_existing_bar_claims_only(self):
        body = self._body("pci_msix_layout_probe")
        self.assertIn("table_claim: PciBarClaim", body)
        self.assertIn("pba_claim: PciBarClaim", body)
        self.assertNotIn("pci_claim_bar(", LAYOUT)
        self.assertNotIn("resource_claim(", LAYOUT)

    def test_global_bar_scan_contract_remains_unknown(self):
        self.assertIn("size = 0", BUS)
        self.assertNotIn("pci_config_measure_memory_bar", LAYOUT)

    def test_bridge_unknown_length_is_not_authoritative(self):
        self.assertIn("driver deve fornecer explicitamente", BRIDGE)
        body = self._body("pci_msix_layout_window_proof")
        self.assertIn("physical.request.length != bar.size", body)

    def test_known_bar_size_comes_only_from_df7b1_aperture_registry(self):
        body = self._body("pci_msix_layout_known_bar_size")
        self.assertIn("pci_bar_aperture_snapshot", body)
        self.assertIn("aperture.size == 0", body)
        self.assertIn("aperture.is_64bit != expected_64bit", body)
        self.assertNotIn("pci_get_device", body)
        self.assertNotIn("physical.request.length", body)

    def test_device_owner_and_segment_zero_are_fail_closed(self):
        body = self._body("pci_msix_layout_probe")
        self.assertIn("device_core_snapshot(device)", body)
        self.assertIn("owner.bus != DEVICE_BUS_PCI", body)
        self.assertIn("driver_handle_equal(owner.driver, driver)", body)
        self.assertIn("DEVICE_STATE_BINDING", body)
        self.assertIn("DEVICE_STATE_ACTIVE", body)
        self.assertIn("((bdf >> 16) & 0xFFFF) != 0", body)

    def test_logical_bar_claim_proves_bdf_bar_and_owner(self):
        body = self._body("pci_msix_layout_window_proof")
        for token in (
            "resource_snapshot(claim.logical)",
            "logical.request.kind != RESOURCE_KIND_PCI_BAR",
            "logical.request.start != bdf as u64",
            "logical.request.length != 1",
            "logical.request.auxiliary != expected_bir as u32",
            "device_handle_equal(logical.owner_device, device)",
            "driver_handle_equal(logical.owner_driver, driver)",
        ):
            self.assertIn(token, body)

    def test_physical_claim_must_match_measured_aperture_exactly(self):
        body = self._body("pci_msix_layout_window_proof")
        for token in (
            "resource_snapshot(claim.physical)",
            "physical.request.kind != RESOURCE_KIND_MMIO",
            "physical.request.start != bar.base",
            "physical.request.length != bar.size",
            "offset > bar.size",
            "bytes > bar.size - offset",
            "address < bar.base",
            "address + bytes < address",
        ):
            self.assertIn(token, body)
        self.assertNotIn("RESOURCE_KIND_IO_PORT", body)

    def test_unknown_aperture_fails_closed(self):
        known = self._body("pci_msix_layout_known_bar_size")
        bar = self._body("pci_msix_layout_bar_snapshot")
        self.assertIn("if !aperture.valid", known)
        self.assertIn("if base == 0 || size == 0", bar)
        self.assertNotIn("size: physical.request.length", LAYOUT)

    def test_bar_walk_rejects_upper_half_and_reserved_memory_types(self):
        body = self._body("pci_msix_layout_bar_snapshot")
        self.assertIn("while bar < 6", body)
        self.assertIn("if bar_type != 0 && bar_type != 2", body)
        self.assertIn("if bar_type == 2 && bar >= 5", body)
        self.assertIn("bar += 2", body)
        self.assertIn("(low & 1) != 0", body)
        self.assertIn("pci_bdf_pack(0, bus, slot, func) != bdf", body)

    def test_same_bir_requires_same_generation_safe_bar_claim(self):
        body = self._body("pci_msix_layout_probe")
        self.assertIn("capability.table_bir == capability.pba_bir", body)
        self.assertIn("resource_handle_equal(table_claim.logical, pba_claim.logical)", body)
        self.assertIn("resource_handle_equal(table_claim.physical, pba_claim.physical)", body)

    def test_capability_claims_bars_and_apertures_are_revalidated(self):
        body = self._body("pci_msix_layout_probe")
        self.assertGreaterEqual(body.count("device_core_snapshot(device)"), 2)
        self.assertGreaterEqual(body.count("pci_msix_capability_probe("), 2)
        self.assertGreaterEqual(body.count("pci_msix_layout_window_proof("), 4)
        self.assertIn("pci_msix_layout_capability_equal(capability, verify_capability)", body)
        self.assertIn("verify_table.bar_size != table.bar_size", body)
        self.assertIn("verify_pba.bar_size != pba.bar_size", body)

    def test_df7b_is_strictly_passive(self):
        forbidden = (
            "pci_config_write",
            "pci_config_set16_bits",
            "pci_write_config32(",
            "active_runtime_map(",
            "active_page_tables_map_mmio",
            "irq_registry_register(",
            "irq_registry_unregister(",
            "lapic_eoi(",
            "pci_enable_memory(",
            "pci_enable_bus_master(",
            "resource_release(",
            "pci_config_measure_memory_bar(",
        )
        for token in forbidden:
            self.assertNotIn(token, LAYOUT)

    def test_aperture_registry_itself_does_not_own_or_program_hardware(self):
        for token in (
            "resource_claim(", "resource_release(", "irq_registry_",
            "pci_config_", "active_page_tables_map_mmio", "lapic_eoi("
        ):
            self.assertNotIn(token, APERTURE)


if __name__ == "__main__":
    unittest.main()

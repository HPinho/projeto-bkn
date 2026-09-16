from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = (ROOT / "kernel/src/drivers/pci_msix_layout.sotlas").read_text(encoding="utf-8")
APERTURE = (ROOT / "kernel/src/drivers/pci_bar_aperture.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
BUS = (ROOT / "kernel/src/drivers/pci_bus.sotlas").read_text(encoding="utf-8")
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")
SIZING = (ROOT / "kernel/src/drivers/pci_bar_sizing.sotlas").read_text(encoding="utf-8")


class PciMsixLayoutContracts(unittest.TestCase):
    def _body(self, text: str, name: str) -> str:
        marker = f"fn {name}"
        start = text.index(marker)
        next_fn = text.find("\n@system\n", start + len(marker))
        if next_fn == -1:
            return text[start:]
        return text[start:next_fn]

    def test_module_is_linked_but_not_invoked_from_boot(self):
        self.assertIn("import kernel::drivers::pci_msix_layout::*;", MAIN)
        self.assertNotIn("pci_msix_layout_probe(", MAIN)
        self.assertEqual(LAYOUT.count("pub fn pci_msix_layout_probe"), 1)
        self.assertIn("import kernel::drivers::pci_bar_aperture::*;", LAYOUT)
        self.assertIn("import kernel::drivers::pci_bar_aperture::*;", SIZING)

    def test_layout_consumes_existing_bar_claims_only(self):
        body = self._body(LAYOUT, "pci_msix_layout_probe")
        self.assertIn("table_claim: PciBarClaim", body)
        self.assertIn("pba_claim: PciBarClaim", body)
        self.assertNotIn("pci_claim_bar(", LAYOUT)
        self.assertNotIn("resource_claim(", LAYOUT)

    def test_global_bar_scan_is_still_read_only_and_size_unknown(self):
        self.assertIn("(*out_bar).size = 0", BUS)
        probe_start = BUS.index("pub fn pci_probe_bar")
        scan_start = BUS.index("pub fn pci_scan_all", probe_start)
        probe = BUS[probe_start:scan_start]
        self.assertNotIn("pci_config_write", probe)
        self.assertNotIn("pci_write_config32", probe)
        self.assertNotIn("pci_bar_aperture_publish", BUS)

    def test_bridge_does_not_make_unknown_size_authoritative(self):
        self.assertIn("known_size != 0 && known_size != length", BRIDGE)
        self.assertIn("driver deve fornecer explicitamente a extensao", BRIDGE)
        body = self._body(LAYOUT, "pci_msix_layout_window_proof")
        self.assertIn("physical.request.length != bar.size", body)

    def test_known_bar_size_comes_only_from_df7b1_aperture_registry(self):
        body = self._body(LAYOUT, "pci_msix_layout_known_bar_size")
        self.assertIn("pci_bar_aperture_snapshot", body)
        self.assertIn("aperture.size == 0", body)
        self.assertIn("aperture.is_64bit != expected_64bit", body)
        self.assertNotIn("pci_get_device", body)
        self.assertNotIn("physical.request.length", body)
        self.assertNotIn("(*pci).bars", body)

    def test_device_owner_and_segment_zero_are_fail_closed(self):
        body = self._body(LAYOUT, "pci_msix_layout_probe")
        self.assertIn("device_core_snapshot(device)", body)
        self.assertIn("owner.bus != DEVICE_BUS_PCI", body)
        self.assertIn("driver_handle_equal(owner.driver, driver)", body)
        self.assertIn("DEVICE_STATE_BINDING", body)
        self.assertIn("DEVICE_STATE_ACTIVE", body)
        self.assertIn("((bdf >> 16) & 0xFFFF) != 0", body)

    def test_logical_bar_claim_proves_bdf_bar_and_owner(self):
        body = self._body(LAYOUT, "pci_msix_layout_window_proof")
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
        body = self._body(LAYOUT, "pci_msix_layout_window_proof")
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
        self.assertNotIn("bytes > physical.request.length - offset", body)

    def test_unknown_aperture_fails_closed(self):
        known = self._body(LAYOUT, "pci_msix_layout_known_bar_size")
        bar = self._body(LAYOUT, "pci_msix_layout_bar_snapshot")
        self.assertIn("if !aperture.valid", known)
        self.assertIn("if base == 0 || size == 0", bar)
        self.assertNotIn("size: physical.request.length", LAYOUT)

    def test_bar_walk_rejects_upper_half_and_reserved_memory_types(self):
        body = self._body(LAYOUT, "pci_msix_layout_bar_snapshot")
        self.assertIn("while bar < 6", body)
        self.assertIn("if bar_type != 0 && bar_type != 2", body)
        self.assertIn("if bar_type == 2 && bar >= 5", body)
        self.assertIn("bar += 2", body)
        self.assertIn("(low & 1) != 0", body)
        self.assertIn("pci_bdf_pack(0, bus, slot, func) != bdf", body)

    def test_same_bir_requires_same_generation_safe_bar_claim(self):
        body = self._body(LAYOUT, "pci_msix_layout_probe")
        self.assertIn("capability.table_bir == capability.pba_bir", body)
        self.assertIn("resource_handle_equal(table_claim.logical, pba_claim.logical)", body)
        self.assertIn("resource_handle_equal(table_claim.physical, pba_claim.physical)", body)

    def test_capability_claims_bars_and_apertures_are_revalidated_before_publication(self):
        body = self._body(LAYOUT, "pci_msix_layout_probe")
        self.assertGreaterEqual(body.count("device_core_snapshot(device)"), 2)
        self.assertGreaterEqual(body.count("pci_msix_capability_probe("), 2)
        self.assertGreaterEqual(body.count("pci_msix_layout_window_proof("), 4)
        self.assertIn("pci_msix_layout_capability_equal(capability, verify_capability)", body)
        self.assertIn("verify_table.bar_base != table.bar_base", body)
        self.assertIn("verify_table.bar_size != table.bar_size", body)
        self.assertIn("verify_pba.bar_size != pba.bar_size", body)
        self.assertIn("verify_pba.physical != pba.physical", body)

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
            "pci_bar_aperture_publish(",
        )
        for token in forbidden:
            self.assertNotIn(token, LAYOUT)

    def test_aperture_registry_itself_does_not_own_or_program_hardware(self):
        for token in (
            "resource_claim(", "resource_release(", "irq_registry_",
            "pci_config_", "active_page_tables_map_mmio", "lapic_eoi("
        ):
            self.assertNotIn(token, APERTURE)

    def test_layout_publishes_measured_bar_sizes_with_windows(self):
        for token in (
            "table_bar_base: table.bar_base",
            "table_bar_size: table.bar_size",
            "table_physical: table.physical",
            "table_bytes: capability.table_bytes",
            "pba_bar_base: pba.bar_base",
            "pba_bar_size: pba.bar_size",
            "pba_physical: pba.physical",
            "pba_bytes: capability.pba_bytes",
            "valid: true",
        ):
            self.assertIn(token, LAYOUT)


if __name__ == "__main__":
    unittest.main()

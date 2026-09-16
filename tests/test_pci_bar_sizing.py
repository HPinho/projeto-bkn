from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / "kernel/src/drivers/pci_config.sotlas").read_text(encoding="utf-8")
SIZING = (ROOT / "kernel/src/drivers/pci_bar_sizing.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
BUS = (ROOT / "kernel/src/drivers/pci_bus.sotlas").read_text(encoding="utf-8")


class PciBarSizingContracts(unittest.TestCase):
    def _body(self, text: str, name: str) -> str:
        marker = f"fn {name}"
        start = text.index(marker)
        next_fn = text.find("\n@system\n", start + len(marker))
        if next_fn == -1:
            return text[start:]
        return text[start:next_fn]

    def test_module_is_linked_but_not_invoked_from_boot(self):
        self.assertIn("import kernel::drivers::pci_bar_sizing::*;", MAIN)
        self.assertNotIn("pci_measure_owned_bar(", MAIN)
        self.assertEqual(SIZING.count("pub fn pci_measure_owned_bar"), 1)

    def test_global_bar_scan_is_still_read_only_and_unsized(self):
        self.assertIn("(*out_bar).size = 0", BUS)
        probe = BUS[BUS.index("pub fn pci_probe_bar"):BUS.index("pub fn pci_scan_all")]
        self.assertNotIn("pci_config_measure_memory_bar", probe)
        self.assertNotIn("pci_config_write32(", probe)
        self.assertNotIn("pci_write_config32(", probe)

    def test_measurement_uses_single_existing_config_lock(self):
        body = self._body(CONFIG, "pci_config_measure_memory_bar")
        self.assertIn("pci_config_lock_irq(&mut flags)", body)
        self.assertIn("pci_config_unlock_irq(flags)", body)
        self.assertNotIn("spinlock_init", body)
        self.assertIn("pci_config_legacy_read32_locked", body)
        self.assertIn("pci_config_legacy_write32_locked", body)
        self.assertNotIn("pci_config_write32(", body)

    def test_decode_and_bus_master_must_already_be_off(self):
        body = self._body(CONFIG, "pci_config_measure_memory_bar")
        self.assertIn("let command = (command_status & 0xFFFF) as u16", body)
        self.assertIn("if (command & 0x0007) != 0", body)
        self.assertNotIn("pci_config_write16", body)
        self.assertNotIn("pci_config_set16_bits", body)

    def test_measurement_rejects_io_reserved_and_upper_half_bars(self):
        body = self._body(CONFIG, "pci_config_measure_memory_bar")
        self.assertIn("while cursor < 6", body)
        self.assertIn("(low & 1) != 0", body)
        self.assertIn("if kind != 0 && kind != 2", body)
        self.assertIn("if kind == 2 && cursor >= 5", body)
        self.assertIn("cursor += 2", body)

    def test_destructive_window_restores_before_valid_result(self):
        body = self._body(CONFIG, "pci_config_measure_memory_bar")
        first_probe = body.index("bar_offset, 0xFFFFFFFF")
        restore = body.index("bar_offset + 4, target_high", first_probe)
        verify = body.index("let verify_low", restore)
        publish = body.rindex("valid: true")
        self.assertLess(first_probe, restore)
        self.assertLess(restore, verify)
        self.assertLess(verify, publish)
        self.assertIn("verify_low == target_low", body)
        self.assertIn("verify_high == target_high", body)
        self.assertIn("verify_command == command", body)
        self.assertIn("if !wrote_low || !wrote_high || !restored", body)

    def test_64bit_bar_is_measured_and_restored_as_pair(self):
        body = self._body(CONFIG, "pci_config_measure_memory_bar")
        self.assertIn("target_high = pci_config_legacy_read32_locked", body)
        self.assertIn("bar_offset + 4, 0xFFFFFFFF", body)
        self.assertIn("bar_offset + 4, target_high", body)
        self.assertIn("mask |= (measured_high as u64) << 32", body)

    def test_size_is_sanity_checked(self):
        body = self._body(CONFIG, "pci_config_measure_memory_bar")
        self.assertIn("size >= 16", body)
        self.assertIn("pci_config_bar_size_power_of_two(size)", body)
        self.assertIn("base != 0", body)
        self.assertIn("(base & (size - 1)) == 0", body)
        self.assertIn("~mask32", body)

    def test_wrapper_requires_binding_and_only_bar_resources(self):
        body = self._body(SIZING, "pci_measure_owned_bar")
        self.assertIn("owner.state != DEVICE_STATE_BINDING", body)
        self.assertIn("owner.resource_count != 2", body)
        self.assertNotIn("DEVICE_STATE_ACTIVE", body)
        self.assertIn("verify_owner.resource_count != 2", body)

    def test_wrapper_proves_generation_safe_claims_but_not_aperture_from_length(self):
        owned = self._body(SIZING, "pci_bar_size_claim_owned")
        self.assertIn("resource_snapshot(claim.logical)", owned)
        self.assertIn("logical.request.kind != RESOURCE_KIND_PCI_BAR", owned)
        self.assertIn("logical.request.start != bdf as u64", owned)
        self.assertIn("logical.request.auxiliary != bar_index as u32", owned)
        self.assertIn("resource_snapshot(claim.physical)", owned)
        self.assertIn("physical.request.kind != RESOURCE_KIND_MMIO", owned)
        self.assertIn("physical.request.start != expected_base", owned)
        self.assertIn("physical.request.length == 0", owned)
        self.assertNotIn("physical.request.length == measurement.size", SIZING)
        self.assertNotIn("physical.request.length != measurement.size", SIZING)
        self.assertNotIn("size = physical.request.length", SIZING)

    def test_wrapper_requires_unknown_inventory_size_and_quiet_interrupt_sources(self):
        inventory = self._body(SIZING, "pci_bar_size_inventory")
        quiet = self._body(SIZING, "pci_bar_size_sources_quiet")
        self.assertIn("(*pci).bars[bar_index as usize].size == 0", inventory)
        self.assertIn("pci_msi_capability_probe", quiet)
        self.assertIn("msi.valid && msi.enabled", quiet)
        self.assertIn("pci_msix_capability_probe", quiet)
        self.assertIn("msix.valid && msix.enabled", quiet)

    def test_wrapper_revalidates_after_destructive_measurement(self):
        body = self._body(SIZING, "pci_measure_owned_bar")
        self.assertGreaterEqual(body.count("pci_bar_size_inventory("), 2)
        self.assertGreaterEqual(body.count("pci_bar_size_claim_owned("), 2)
        self.assertGreaterEqual(body.count("pci_bar_size_sources_quiet("), 2)
        self.assertGreaterEqual(body.count("device_core_snapshot(device)"), 2)
        self.assertIn("measurement.restored", body)
        self.assertIn("measurement.base != base", body)

    def test_df7b1_does_not_program_msix_or_touch_irq_dma_mmio(self):
        forbidden = (
            "irq_registry_register(",
            "irq_registry_unregister(",
            "lapic_eoi(",
            "active_runtime_map(",
            "active_page_tables_map_mmio",
            "pci_msix_layout_probe(",
            "pci_msix_table",
            "pci_msix_pba",
            "RESOURCE_KIND_DMA",
            "pci_write_command_bits(",
        )
        for token in forbidden:
            self.assertNotIn(token, SIZING)


if __name__ == "__main__":
    unittest.main()

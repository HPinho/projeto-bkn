#!/usr/bin/env python3
"""DF-5a/5b: PCI config core SMP-safe com ECAM staged e fallback CF8/CFC."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "kernel/src/drivers/pci_config.sotlas"
PCI = ROOT / "kernel/src/drivers/pci_bus.sotlas"


class PciConfigCoreTests(unittest.TestCase):
    def test_pci_bus_routes_normal_config_access_through_core(self):
        config = CONFIG.read_text(encoding="utf-8")
        pci = PCI.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::pci_config;", config)
        self.assertIn("import kernel::drivers::pci_config::*;", pci)
        self.assertIn("pci_config_read32(0, bus, slot, func, offset as u16)", pci)
        self.assertIn("pci_config_write32(0, bus, slot, func, offset as u16, value)", pci)
        self.assertNotIn("baken_pci_out32", pci)
        self.assertNotIn("baken_pci_in32", pci)

    def test_cf8_cfc_pair_remains_irq_safe_and_spinlocked(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("static mut PCI_CONFIG_LOCK: SpinLock", text)
        self.assertIn("x86_irq_save_disable()", text)
        self.assertIn("spinlock_lock(&mut PCI_CONFIG_LOCK)", text)
        self.assertIn("spinlock_unlock(&mut PCI_CONFIG_LOCK)", text)
        self.assertIn("x86_irq_restore(flags)", text)
        self.assertIn("baken_pci_out32(PCI_CONFIG_ADDRESS_PORT, address)", text)
        self.assertIn("baken_pci_in32(PCI_CONFIG_DATA_PORT)", text)

    def test_ecam_is_staged_after_legacy_bootstrap_scan(self):
        config = CONFIG.read_text(encoding="utf-8")
        pci = PCI.read_text(encoding="utf-8")
        self.assertIn("PCI_CONFIG_BACKEND_LEGACY_CF8CFC", config)
        self.assertIn("PCI_CONFIG_BACKEND_ECAM", config)
        self.assertIn("PCI_CONFIG_BACKEND = PCI_CONFIG_BACKEND_LEGACY_CF8CFC", config)
        self.assertIn("pub fn pci_config_promote_ecam() -> bool", config)
        self.assertIn("pci_config_read16_legacy", pci)
        self.assertIn("pci_config_read8_legacy", pci)
        promote_pos = pci.index("pci_config_promote_ecam()")
        scan_pos = pci.index("pub fn pci_scan_all()")
        self.assertGreater(promote_pos, scan_pos)

    def test_ecam_uses_mcfg_and_mmio_mapping_with_legacy_fallback(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("import kernel::acpi::mcfg::*;", text)
        self.assertIn("import kernel::memory::active_page_tables::*;", text)
        self.assertIn("import kernel::memory::mmio_mapping::*;", text)
        self.assertIn("mcfg_init()", text)
        self.assertIn("mcfg_ecam_address", text)
        self.assertIn("mmio_describe_identity(page, 4096, MMIO_CACHE_POLICY_UC)", text)
        self.assertIn("mmio_map_identity(&mapping)", text)
        self.assertNotIn("active_page_tables_map_mmio_identity_4k(page)", text)
        self.assertIn("x86_mmio_read32(ecam)", text)
        self.assertIn("x86_mmio_write32(ecam, value)", text)
        self.assertIn("return pci_config_legacy_read32_locked", text)
        self.assertIn("return pci_config_legacy_write32_locked", text)

    def test_ecam_page_cache_bounds_identity_mappings(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("PCI_CONFIG_ECAM_PAGE_CACHE_CAPACITY: usize = 128", text)
        self.assertIn("PCI_CONFIG_ECAM_PAGES", text)
        self.assertIn("pci_config_ecam_page_cached_locked", text)
        self.assertIn("PCI_CONFIG_ECAM_PAGE_COUNT >= PCI_CONFIG_ECAM_PAGE_CACHE_CAPACITY as u32", text)
        self.assertIn("PCI_CONFIG_ECAM_PAGE_COUNT += 1", text)

    def test_scan_initializes_core_and_does_not_require_ecam(self):
        text = PCI.read_text(encoding="utf-8")
        scan = text.split("pub fn pci_scan_all()", 1)[1].split("pub fn pci_get_device_count", 1)[0]
        init_pos = scan.index("pci_config_init()")
        first_vendor = scan.index("pci_config_read16_legacy")
        self.assertLess(init_pos, first_vendor)
        self.assertNotIn("!pci_config_uses_legacy_cf8cfc()", scan)
        self.assertIn("if pci_config_ecam_available() { pci_config_promote_ecam(); }", scan)

    def test_command_register_updates_use_single_locked_rmw_helper(self):
        config = CONFIG.read_text(encoding="utf-8")
        pci = PCI.read_text(encoding="utf-8")
        self.assertIn("pub fn pci_config_write16", config)
        self.assertIn("pub fn pci_config_set16_bits", config)
        self.assertIn("let clear_mask: u32 = ~mask;", config)
        self.assertIn("pci_config_read32_locked", config)
        self.assertIn("pci_config_write32_locked", config)
        self.assertIn("pci_config_write16(0, bus, slot, func, 0x04, command)", pci)
        self.assertIn("pci_config_set16_bits(0, bus, slot, func, 0x04, requested)", pci)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""DF-5a: PCI config core deve preservar CF8/CFC com serialização SMP/IRQ-safe."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "kernel/src/drivers/pci_config.sotlas"
PCI = ROOT / "kernel/src/drivers/pci_bus.sotlas"


class PciConfigCoreTests(unittest.TestCase):
    def test_pci_bus_routes_all_config_access_through_core(self):
        config = CONFIG.read_text(encoding="utf-8")
        pci = PCI.read_text(encoding="utf-8")
        self.assertIn("module kernel::drivers::pci_config;", config)
        self.assertIn("import kernel::drivers::pci_config::*;", pci)
        self.assertIn("pci_config_read32(0, bus, slot, func, offset as u16)", pci)
        self.assertIn("pci_config_write32(0, bus, slot, func, offset as u16, value)", pci)
        self.assertNotIn("baken_pci_out32", pci)
        self.assertNotIn("baken_pci_in32", pci)

    def test_cf8_cfc_pair_is_irq_safe_and_spinlocked(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("static mut PCI_CONFIG_LOCK: SpinLock", text)
        self.assertIn("x86_irq_save_disable()", text)
        self.assertIn("spinlock_lock(&mut PCI_CONFIG_LOCK)", text)
        self.assertIn("spinlock_unlock(&mut PCI_CONFIG_LOCK)", text)
        self.assertIn("x86_irq_restore(flags)", text)
        self.assertIn("baken_pci_out32(PCI_CONFIG_ADDRESS_PORT, address)", text)
        self.assertIn("baken_pci_in32(PCI_CONFIG_DATA_PORT)", text)

    def test_legacy_backend_is_explicit_and_ecam_is_not_active_yet(self):
        text = CONFIG.read_text(encoding="utf-8")
        self.assertIn("PCI_CONFIG_BACKEND_LEGACY_CF8CFC", text)
        self.assertIn("PCI_CONFIG_BACKEND_ECAM", text)
        self.assertIn("PCI_CONFIG_BACKEND = PCI_CONFIG_BACKEND_LEGACY_CF8CFC", text)
        self.assertIn("segment != 0", text)
        self.assertIn("offset > PCI_CONFIG_LEGACY_MAX_OFFSET", text)
        self.assertNotIn("mcfg_ecam_address", text)
        self.assertNotIn("x86_mmio_read32", text)
        self.assertNotIn("x86_mmio_write32", text)

    def test_scan_initializes_config_core_before_first_bdf_read(self):
        text = PCI.read_text(encoding="utf-8")
        scan = text.split("pub fn pci_scan_all()", 1)[1].split("pub fn pci_get_device_count", 1)[0]
        init_pos = scan.index("pci_config_init()")
        read_pos = scan.index("pci_read_config16")
        self.assertLess(init_pos, read_pos)
        self.assertIn("pci_config_uses_legacy_cf8cfc()", scan)

    def test_command_register_updates_use_single_locked_rmw_helper(self):
        config = CONFIG.read_text(encoding="utf-8")
        pci = PCI.read_text(encoding="utf-8")
        self.assertIn("pub fn pci_config_write16", config)
        self.assertIn("pub fn pci_config_set16_bits", config)
        self.assertIn("let clear_mask: u32 = ~mask;", config)
        self.assertIn("pci_config_write16(0, bus, slot, func, 0x04, command)", pci)
        self.assertIn("pci_config_set16_bits(0, bus, slot, func, 0x04, requested)", pci)


if __name__ == "__main__":
    unittest.main()

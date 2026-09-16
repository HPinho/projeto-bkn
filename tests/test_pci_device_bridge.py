#!/usr/bin/env python3
"""DF-5d: bridge PCI/Device/Resource deve preservar ownership generation-safe."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "kernel/src/drivers/pci_device_bridge.sotlas").read_text(encoding="utf-8")
MAIN = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")


class PciDeviceBridgeTests(unittest.TestCase):
    def test_bridge_is_linked_into_real_kernel_graph(self):
        self.assertIn("module kernel::drivers::pci_device_bridge;", BRIDGE)
        self.assertIn("import kernel::drivers::pci_device_bridge::*;", MAIN)

    def test_bridge_uses_device_and_resource_foundations(self):
        for dependency in (
            "import kernel::drivers::pci_bus::*;",
            "import kernel::drivers::pci_config::*;",
            "import kernel::device::types::*;",
            "import kernel::device::registry::*;",
            "import kernel::device::resource_manager::*;",
        ):
            self.assertIn(dependency, BRIDGE)
        self.assertIn("device_core_init()", BRIDGE)
        self.assertIn("resource_manager_init()", BRIDGE)

    def test_bdf_identity_preserves_segment_and_standard_bdf_bits(self):
        self.assertIn("pub fn pci_bdf_pack(segment: u16, bus: u8, slot: u8, func: u8)", BRIDGE)
        self.assertIn("((segment as u32) << 16)", BRIDGE)
        self.assertIn("((bus as u32) << 8)", BRIDGE)
        self.assertIn("(((slot & 0x1F) as u32) << 3)", BRIDGE)
        self.assertIn("((func & 0x07) as u32)", BRIDGE)
        self.assertIn("if slot >= 32 || func >= 8", BRIDGE)

    def test_pci_devices_are_published_as_generation_safe_device_core_records(self):
        body = BRIDGE.split("pub fn pci_claim_device", 1)[1].split("\n@system", 1)[0]
        self.assertIn("device_core_attach(", body)
        self.assertIn("DEVICE_BUS_PCI", body)
        self.assertIn("pci_device_class", body)
        self.assertIn("vendor_id", body)
        self.assertIn("device_id", body)
        self.assertIn("bdf", body)
        self.assertIn("device_core_snapshot(existing)", body)

    def test_detach_never_bypasses_device_core_lifecycle(self):
        body = BRIDGE.split("pub fn pci_release_device", 1)[1].split("\n@system", 1)[0]
        self.assertIn("device_core_detach(handle)", body)
        self.assertLess(body.index("device_core_detach(handle)"), body.index("pci_bridge_clear_slot_locked(slot)"))
        self.assertNotIn("resource_release_all", body)

    def test_bar_claim_is_logical_plus_physical_and_rolls_back(self):
        body = BRIDGE.split("pub fn pci_claim_bar", 1)[1].split("\n@system", 1)[0]
        self.assertIn("RESOURCE_KIND_PCI_BAR", body)
        self.assertIn("RESOURCE_KIND_IO_PORT", body)
        self.assertIn("RESOURCE_KIND_MMIO", body)
        self.assertLess(body.index("kind: RESOURCE_KIND_PCI_BAR"), body.index("kind: physical_kind"))
        self.assertIn("resource_release(logical, device, driver)", body)
        self.assertNotIn("pci_config_write", body)
        self.assertNotIn("pci_enable_device", body)

    def test_bar_release_is_reverse_order_and_fail_closed(self):
        body = BRIDGE.split("pub fn pci_release_bar", 1)[1].split("\n@system", 1)[0]
        physical = "resource_release(claim.physical, device, driver)"
        logical = "resource_release(claim.logical, device, driver)"
        self.assertIn(physical, body)
        self.assertIn(logical, body)
        self.assertLess(body.index(physical), body.index(logical))
        self.assertIn("return false", body)

    def test_command_bits_require_exact_bound_driver_ownership(self):
        ownership = BRIDGE.split("fn pci_bridge_owned_device", 1)[1].split("\n@system", 1)[0]
        self.assertIn("driver_handle_equal(snapshot.driver, driver)", ownership)
        self.assertIn("DEVICE_STATE_BINDING", ownership)
        self.assertIn("DEVICE_STATE_ACTIVE", ownership)
        self.assertIn("snapshot.bus_instance != bdf", ownership)

        memory = BRIDGE.split("pub fn pci_enable_memory", 1)[1].split("\n@system", 1)[0]
        bus_master = BRIDGE.split("pub fn pci_enable_bus_master", 1)[1].split("\n@system", 1)[0]
        self.assertIn("PCI_COMMAND_MEMORY_SPACE", memory)
        self.assertNotIn("PCI_COMMAND_BUS_MASTER", memory)
        self.assertNotIn("PCI_COMMAND_IO_SPACE", memory)
        self.assertIn("PCI_COMMAND_BUS_MASTER", bus_master)
        self.assertNotIn("PCI_COMMAND_MEMORY_SPACE", bus_master)
        self.assertNotIn("PCI_COMMAND_IO_SPACE", bus_master)

    def test_resource_claims_happen_without_bridge_lock_held(self):
        ownership = BRIDGE.split("fn pci_bridge_owned_device", 1)[1].split("\n@system", 1)[0]
        self.assertIn("pci_bridge_unlock_irq(flags)", ownership)
        claim = BRIDGE.split("pub fn pci_claim_bar", 1)[1].split("\n@system", 1)[0]
        self.assertNotIn("pci_bridge_lock_irq", claim)
        self.assertIn("pci_bridge_owned_device", claim)
        self.assertIn("resource_claim", claim)

    def test_no_destructive_bar_sizing_or_broad_enable_helper(self):
        self.assertNotIn("0xFFFFFFFF,", BRIDGE.split("pub fn pci_claim_bar", 1)[1])
        self.assertNotIn("pci_enable_device(", BRIDGE)
        self.assertNotIn("pci_write_config32", BRIDGE)


if __name__ == "__main__":
    unittest.main()

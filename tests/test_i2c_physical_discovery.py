from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"
REGISTRY = ROOT / "kernel/src/drivers/i2c_controller_registry.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class I2cPhysicalDiscoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.registry = REGISTRY.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")

    def test_physical_discovery_is_in_native_graph(self):
        self.assertIn("import kernel::drivers::i2c_physical_discovery::*;", self.main)

    def test_hardware_types_and_constants(self):
        for token in (
            "pub const I2C_HARDWARE_TYPE_UNKNOWN: u8 = 0",
            "pub const I2C_HARDWARE_TYPE_DESIGNWARE: u8 = 1",
            "pub const I2C_HARDWARE_TYPE_INTEL_LPSS: u8 = 2",
            "pub const I2C_MAX_PHYSICAL_CONTROLLERS: usize = 8",
            "pub const PCI_CLASS_SERIAL_BUS: u8 = 0x0C",
            "pub const PCI_SUBCLASS_SMBUS: u8 = 0x05",
            "pub const PCI_SUBCLASS_SERIAL_OTHER: u8 = 0x80",
            "pub struct I2cPhysicalController",
        ):
            self.assertIn(token, self.text)

    def test_hardware_filter_is_fail_closed_and_clock_table_drives_support(self):
        self.assertIn("pub fn i2c_physical_identify_hardware", self.text)
        self.assertIn("let is_valid_pci_serial_class = class_code == PCI_CLASS_SERIAL_BUS", self.text)
        self.assertIn("if !is_valid_pci_serial_class", self.text)
        self.assertIn("i2c_physical_clock_for_device(vendor_id, device_id) != 0", self.text)
        self.assertIn("return I2C_HARDWARE_TYPE_UNKNOWN;", self.text)
        self.assertNotIn("device_id >= 0x7E50 && device_id <= 0x7E55", self.text)
        self.assertNotIn("device_id >= 0x9DA0 && device_id <= 0x9DA5", self.text)

    def test_intel_lpss_clock_families_are_explicit(self):
        self.assertIn("return 120000000;", self.text)
        self.assertIn("return 216000000;", self.text)
        self.assertIn("return 133000000;", self.text)
        self.assertIn("return 100000000;", self.text)
        self.assertIn("device_id >= 0x02E8 && device_id <= 0x02EB", self.text)
        self.assertIn("device_id >= 0x4B78 && device_id <= 0x4B7B", self.text)
        self.assertIn("device_id >= 0x7E50 && device_id <= 0x7E51", self.text)

    def test_acpi_binding_is_resolved_before_any_pci_or_mmio_side_effect(self):
        probe = self.text.split("pub fn i2c_physical_probe_pci()", 1)[1]
        acpi_pos = probe.index("let acpi_ns = i2c_physical_find_acpi_namespace")
        pci_enable_pos = probe.index("pci_enable_command_bits(bus, slot, func, PCI_COMMAND_MEMORY_SPACE)")
        mmio_pos = probe.index("active_page_tables_map_mmio_identity_4k(page_aligned)")
        self.assertLess(acpi_pos, pci_enable_pos)
        self.assertLess(acpi_pos, mmio_pos)
        self.assertIn("if acpi_ns == AML_NAMESPACE_INVALID_INDEX", probe)
        self.assertIn("i2c_discovery_bridge_find_by_namespace(acpi_ns)", probe)

    def test_acpi_adr_matching_rejects_root_bus_ambiguity(self):
        self.assertIn("pub fn i2c_physical_find_acpi_namespace(bus: u8, slot: u8, func: u8) -> usize", self.text)
        self.assertIn("!aml_discovery_is_ready() || bus != 0", self.text)
        self.assertIn("let target_adr = ((slot as u64) << 16) | (func as u64);", self.text)
        self.assertIn("i2c_discovery_bridge_find_by_namespace(ns_index)", self.text)
        self.assertIn("if found != AML_NAMESPACE_INVALID_INDEX && found != ns_index", self.text)

    def test_probe_is_idempotent_before_hardware_side_effects(self):
        probe = self.text.split("pub fn i2c_physical_probe_pci()", 1)[1]
        snapshot_pos = probe.index("let logical_record = i2c_controller_registry_snapshot(")
        pci_enable_pos = probe.index("pci_enable_command_bits(bus, slot, func, PCI_COMMAND_MEMORY_SPACE)")
        self.assertLess(snapshot_pos, pci_enable_pos)
        self.assertIn("logical_record.state != I2C_CONTROLLER_STATE_ATTACHED", probe)
        self.assertIn("logical_record.backend_ready", probe)

    def test_pci_probing_checks_bar_base_and_mmio_mapping(self):
        self.assertIn("let bar_step = pci_probe_bar(bus, slot, func, 0, &mut bar0);", self.text)
        self.assertIn("bar_step >= 1 && bar0.base_address != 0 && !bar0.is_io", self.text)
        self.assertIn("if !active_page_tables_map_mmio_identity_4k(page_aligned)", self.text)
        self.assertIn("pci_enable_command_bits(bus, slot, func, PCI_COMMAND_MEMORY_SPACE)", self.text)
        self.assertNotIn("PCI_COMMAND_BUS_MASTER", self.text)

    def test_backend_capabilities_are_clamped_before_publish_and_activation(self):
        self.assertIn("pub fn i2c_controller_registry_update_capabilities", self.registry)
        probe = self.text.split("pub fn i2c_physical_probe_pci()", 1)[1]
        update_pos = probe.index("i2c_controller_registry_update_capabilities(")
        publish_pos = probe.index("i2c_controller_registry_publish_backend(")
        activate_pos = probe.index("i2c_controller_registry_activate(")
        self.assertLess(update_pos, publish_pos)
        self.assertLess(publish_pos, activate_pos)
        self.assertIn(
            "let physical_caps = i2c_discovery_default_capabilities(DW_SUPPORTED_FAST_SPEED_HZ, false);",
            probe,
        )

    def test_publish_and_activate_fail_closed_with_rollback(self):
        self.assertIn("if !i2c_controller_registry_publish_backend(", self.text)
        self.assertIn("if !i2c_controller_registry_activate(", self.text)
        self.assertIn("i2c_controller_registry_mark_failed(", self.text)
        self.assertIn("i2c_physical_rollback_last(slot_idx);", self.text)
        self.assertIn("i2c_dw_enable(phys_base, false);", self.text)

    def test_hardware_initialization_requires_init_ok(self):
        self.assertIn(
            "let init_ok = i2c_dw_init_with_clock(phys_base, DW_SUPPORTED_FAST_SPEED_HZ, input_clock);",
            self.text,
        )
        self.assertIn("if !init_ok {", self.text)
        self.assertIn("i2c_lpss_reset_release(phys_base, phys_base)", self.text)

    def test_smp_per_controller_locking_does_not_mask_irqs(self):
        self.assertIn("pub fn i2c_physical_lock_controller(backend_instance: u32) -> bool", self.text)
        self.assertIn("pub fn i2c_physical_unlock_controller(backend_instance: u32) -> void", self.text)
        self.assertIn("I2C_PHYSICAL_CONTROLLER_LOCKS", self.text)
        lock_body = self.text.split("pub fn i2c_physical_lock_controller", 1)[1].split("pub fn i2c_physical_unlock_controller", 1)[0]
        self.assertNotIn("x86_irq_save_disable", lock_body)

    def test_boot_route_invokes_i2c_discovery(self):
        self.assertIn("i2c_discovery_scan_acpi_controllers();", self.runtime)
        self.assertIn("i2c_physical_probe_pci();", self.runtime)


if __name__ == "__main__":
    unittest.main()

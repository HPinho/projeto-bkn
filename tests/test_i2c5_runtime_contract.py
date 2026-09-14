from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
DISCOVERY = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"
DESIGNWARE = ROOT / "kernel/src/drivers/i2c_designware.sotlas"
REGISTRY = ROOT / "kernel/src/drivers/i2c_controller_registry.sotlas"
DEVICE = ROOT / "kernel/src/drivers/i2c_device.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"


class I2c5RuntimeContractTests(unittest.TestCase):
    """Architectural and runtime contracts for I2C-5 physical-controller foundation."""

    def test_i2c5a_discovery_is_bounded_and_zero_heap(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertNotIn("kernel_heap", text)
        self.assertNotIn("alloc(", text)
        self.assertIn("pub const I2C_MAX_PHYSICAL_CONTROLLERS: usize = 8;", text)
        self.assertIn("pci_probe_bar(", text)
        self.assertIn("pci_enable_command_bits(bus, slot, func, PCI_COMMAND_MEMORY_SPACE);", text)
        self.assertIn("if !active_page_tables_map_mmio_identity_4k(page_aligned)", text)

    def test_i2c5a_pci_class_and_hardware_filter_fail_closed(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("pub const PCI_CLASS_SERIAL_BUS: u8 = 0x0C;", text)
        self.assertIn("pub const PCI_SUBCLASS_SMBUS: u8 = 0x05;", text)
        self.assertIn("pub const PCI_SUBCLASS_SERIAL_OTHER: u8 = 0x80;", text)
        self.assertIn("return I2C_HARDWARE_TYPE_UNKNOWN;", text)
        self.assertIn("i2c_physical_clock_for_device(vendor_id, device_id) != 0", text)
        self.assertIn("bar_step >= 1 && bar0.base_address != 0 && !bar0.is_io", text)

    def test_i2c5a_acpi_pci_binding_precedes_hardware_side_effects(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        probe = text.split("pub fn i2c_physical_probe_pci()", 1)[1]
        self.assertIn("pub fn i2c_physical_find_acpi_namespace", text)
        self.assertIn("!aml_discovery_is_ready() || bus != 0", text)
        self.assertLess(
            probe.index("let acpi_ns = i2c_physical_find_acpi_namespace"),
            probe.index("pci_enable_command_bits(bus, slot, func, PCI_COMMAND_MEMORY_SPACE)"),
        )
        self.assertIn("i2c_discovery_bridge_find_by_namespace(acpi_ns)", probe)

    def test_i2c5a_physical_capabilities_are_bound_before_backend_publish(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        registry = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("pub fn i2c_controller_registry_update_capabilities", registry)
        probe = text.split("pub fn i2c_physical_probe_pci()", 1)[1]
        self.assertLess(
            probe.index("i2c_controller_registry_update_capabilities("),
            probe.index("i2c_controller_registry_publish_backend("),
        )
        self.assertLess(
            probe.index("i2c_controller_registry_publish_backend("),
            probe.index("i2c_controller_registry_activate("),
        )
        self.assertIn("i2c_controller_registry_mark_failed(", probe)

    def test_i2c5b_designware_register_map_contract(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        for token in (
            "pub const DW_IC_CON: u64 = 0x00;",
            "pub const DW_IC_TAR: u64 = 0x04;",
            "pub const DW_IC_DATA_CMD: u64 = 0x10;",
            "pub const DW_IC_SS_SCL_HCNT: u64 = 0x14;",
            "pub const DW_IC_SS_SCL_LCNT: u64 = 0x18;",
            "pub const DW_IC_FS_SCL_HCNT: u64 = 0x1C;",
            "pub const DW_IC_FS_SCL_LCNT: u64 = 0x20;",
            "pub const DW_IC_STATUS: u64 = 0x70;",
            "pub const DW_IC_TXFLR: u64 = 0x74;",
            "pub const DW_IC_RXFLR: u64 = 0x78;",
            "pub const DW_IC_TX_ABRT_SOURCE: u64 = 0x80;",
            "pub const DW_IC_ENABLE: u64 = 0x6C;",
        ):
            self.assertIn(token, text)

    def test_i2c5b_lpss_wrapper_uses_canonical_64bit_remap(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        self.assertIn("pub const INTEL_LPSS_DEV_OFFSET: u64 = 0x000;", text)
        self.assertIn("pub const INTEL_LPSS_PRIV_OFFSET: u64 = 0x200;", text)
        self.assertIn("pub const LPSS_PRIV_REMAP_ADDR: u64 = 0x40;", text)
        self.assertIn("pub const LPSS_PRIV_REMAP_ADDR_HIGH: u64 = 0x44;", text)
        self.assertIn("pub const LPSS_PRIV_RESETS_FUNC: u32 = 0x03;", text)
        self.assertIn("pub const LPSS_PRIV_RESETS_IDMA: u32 = 1 << 2;", text)
        self.assertIn("pub const LPSS_PRIV_RESETS_BOTH: u32 = 0x07;", text)
        self.assertIn("let high_addr = ((physical_address >> 32) & 0xFFFFFFFF) as u32;", text)
        self.assertNotIn("pub const LPSS_PRIV_REMAP_ADDR: u64 = 0x00;", text)

    def test_i2c5b_clock_table_and_transaction_speed_contract(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        disc = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("return 120000000;", disc)
        self.assertIn("return 216000000;", disc)
        self.assertIn("return 133000000;", disc)
        self.assertIn("return 100000000;", disc)
        self.assertIn("pub const DW_SUPPORTED_STANDARD_SPEED_HZ: u32 = 100000;", text)
        self.assertIn("pub const DW_SUPPORTED_FAST_SPEED_HZ: u32 = 400000;", text)
        self.assertIn("let bus_speed_hz = unsafe { (*transaction).bus_speed_hz };", text)
        self.assertIn("current_speed_bits != desired_speed_bits", text)
        self.assertIn("return I2C_STATUS_UNSUPPORTED;", text)

    def test_i2c5c_synchronous_fifo_and_real_buffer_mutation_contract(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        self.assertIn("DW_IC_STATUS_TFNF", text)
        self.assertIn("DW_IC_STATUS_RFNE", text)
        self.assertIn("DW_IC_STATUS_TFE", text)
        self.assertIn("*buf.add(byte_idx) = received_byte;", text)
        dev_text = DEVICE.read_text(encoding="utf-8")
        self.assertIn("i2c_dw_transfer(", dev_text)

    def test_i2c5c_zero_synthetic_fallback_and_smp_serialization(self):
        dev_text = DEVICE.read_text(encoding="utf-8")
        self.assertIn("return I2C_STATUS_CONTROLLER_ERROR;", dev_text)
        self.assertIn("i2c_physical_lock_controller(", dev_text)
        self.assertIn("i2c_physical_unlock_controller(", dev_text)

    def test_i2c5d_shared_deadline_covers_reconfiguration_and_io(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        self.assertIn("DW_ABRT_7B_ADDR_NOACK", text)
        self.assertIn("DW_ABRT_TXDATA_NOACK", text)
        self.assertIn("DW_ABRT_ARB_LOST", text)
        self.assertIn("I2C_STATUS_ADDRESS_NACK", text)
        self.assertIn("I2C_STATUS_DATA_NACK", text)
        self.assertIn("I2C_STATUS_ARBITRATION_LOST", text)
        self.assertIn("I2C_STATUS_TIMEOUT", text)
        self.assertIn("x86_timer_is_calibrated()", text)
        self.assertIn("x86_timer_read_tsc()", text)
        self.assertIn("deadline_tsc", text)
        self.assertIn("fn i2c_dw_enable_until", text)
        self.assertIn("i2c_dw_enable_until(base, false, deadline_tsc, timeout_cycles)", text)
        self.assertIn("i2c_dw_enable_until(base, true, deadline_tsc, timeout_cycles)", text)

    def test_canonical_boot_route_invokes_i2c_discovery(self):
        rt_text = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("i2c_discovery_scan_acpi_controllers();", rt_text)
        self.assertIn("i2c_physical_probe_pci();", rt_text)

    def test_main_modular_kernel_graph_contract(self):
        main_text = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::i2c_physical_discovery::*;", main_text)
        self.assertIn("import kernel::drivers::i2c_designware::*;", main_text)

    def test_qemu_smoke_gate_invariants_preserved(self):
        smoke_text = SMOKE.read_text(encoding="utf-8")
        self.assertIn("REQUIRED = (", smoke_text)
        self.assertIn("USER_FAULT_ISOLATED_READY", smoke_text)
        self.assertIn("BARE_METAL_READY", smoke_text)
        self.assertIn("SCHEDULER_ROUND_TRIP", smoke_text)
        disc_text = DISCOVERY.read_text(encoding="utf-8")
        self.assertNotIn("panic(", disc_text)
        self.assertNotIn("loop {", disc_text)


if __name__ == "__main__":
    unittest.main()

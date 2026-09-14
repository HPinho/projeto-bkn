from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "tools/scripts/verify_kernel_smoke.py"
DISCOVERY = ROOT / "kernel/src/drivers/i2c_physical_discovery.sotlas"
DESIGNWARE = ROOT / "kernel/src/drivers/i2c_designware.sotlas"
DEVICE = ROOT / "kernel/src/drivers/i2c_device.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2c5RuntimeContractTests(unittest.TestCase):
    """Architectural and runtime contracts for I2C-5 (Physical Controller Backend)."""

    def test_i2c5a_discovery_is_bounded_and_zero_heap(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertNotIn("kernel_heap", text)
        self.assertNotIn("alloc(", text)
        self.assertIn("pub const I2C_MAX_PHYSICAL_CONTROLLERS: usize = 8;", text)
        self.assertIn("pci_probe_bar(", text)
        self.assertIn("pci_enable_device(", text)
        self.assertIn("active_page_tables_map_mmio_identity_4k(", text)

    def test_i2c5a_pci_class_and_hardware_filter_fail_closed(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        # PCI Class 0x0C (Serial Bus), Subclasses 0x80 or 0x05 (SMBus/I2C)
        self.assertIn("pub const PCI_CLASS_SERIAL_BUS: u8 = 0x0C;", text)
        self.assertIn("pub const PCI_SUBCLASS_SMBUS: u8 = 0x05;", text)
        self.assertIn("pub const PCI_SUBCLASS_SERIAL_OTHER: u8 = 0x80;", text)
        # Invariante crítica: identificação fail-closed padrão UNKNOWN
        self.assertIn("return I2C_HARDWARE_TYPE_UNKNOWN;", text)
        # BAR probe deve aceitar retorno >= 1 (32-bit ou 64-bit)
        self.assertIn("bar_step >= 1 && bar0.base_address != 0 && !bar0.is_io", text)

    def test_i2c5a_acpi_pci_binding_and_registry_activation(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        # Associação com _ADR do ACPI
        self.assertIn("pub fn i2c_physical_find_acpi_namespace", text)
        # Ativação do backend no registry
        self.assertIn("i2c_controller_registry_publish_backend(", text)
        self.assertIn("i2c_controller_registry_activate(", text)

    def test_i2c5b_designware_register_map_contract(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        # Canonical Synopsys DesignWare I2C register layout
        self.assertIn("pub const DW_IC_CON: u64 = 0x00;", text)
        self.assertIn("pub const DW_IC_TAR: u64 = 0x04;", text)
        self.assertIn("pub const DW_IC_DATA_CMD: u64 = 0x10;", text)
        self.assertIn("pub const DW_IC_SS_SCL_HCNT: u64 = 0x14;", text)
        self.assertIn("pub const DW_IC_SS_SCL_LCNT: u64 = 0x18;", text)
        self.assertIn("pub const DW_IC_FS_SCL_HCNT: u64 = 0x1C;", text)
        self.assertIn("pub const DW_IC_FS_SCL_LCNT: u64 = 0x20;", text)
        self.assertIn("pub const DW_IC_STATUS: u64 = 0x70;", text)
        self.assertIn("pub const DW_IC_TXFLR: u64 = 0x74;", text)
        self.assertIn("pub const DW_IC_RXFLR: u64 = 0x78;", text)
        self.assertIn("pub const DW_IC_TX_ABRT_SOURCE: u64 = 0x80;", text)
        self.assertIn("pub const DW_IC_ENABLE: u64 = 0x6C;", text)

    def test_i2c5b_lpss_wrapper_and_dynamic_clock_calculations(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        self.assertIn("pub const INTEL_LPSS_DEV_OFFSET: u64 = 0x000;", text)
        self.assertIn("pub const INTEL_LPSS_PRIV_OFFSET: u64 = 0x200;", text)
        self.assertIn("pub fn i2c_lpss_reset_release", text)
        self.assertIn("pub fn i2c_dw_calc_scl_hcnt", text)
        self.assertIn("pub fn i2c_dw_calc_scl_lcnt", text)

    def test_i2c5c_synchronous_fifo_and_real_buffer_mutation_contract(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        # Polling status flags for FIFO fullness / emptiness
        self.assertIn("DW_IC_STATUS_TFNF", text)
        self.assertIn("DW_IC_STATUS_RFNE", text)
        self.assertIn("DW_IC_STATUS_TFE", text)
        # Real physical write-back into message memory buffer
        self.assertIn("*buf.add(byte_idx) = received_byte;", text)
        # Device dispatch integration
        dev_text = DEVICE.read_text(encoding="utf-8")
        self.assertIn("i2c_dw_transfer(", dev_text)

    def test_i2c5c_zero_synthetic_fallback_and_smp_serialization(self):
        dev_text = DEVICE.read_text(encoding="utf-8")
        # Invariante P0: fail closed imediato em produção sem fallback sintético
        self.assertIn("return I2C_STATUS_CONTROLLER_ERROR;", dev_text)
        # Invariante SMP: serialização exclusiva da transação por controlador
        self.assertIn("i2c_physical_lock_controller(", dev_text)
        self.assertIn("i2c_physical_unlock_controller(", dev_text)

    def test_i2c5d_temporal_deadline_timeout_and_fault_decoding(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        # Accurate translation from hardware abort sources to core status codes
        self.assertIn("DW_ABRT_7B_ADDR_NOACK", text)
        self.assertIn("DW_ABRT_TXDATA_NOACK", text)
        self.assertIn("DW_ABRT_ARB_LOST", text)
        self.assertIn("I2C_STATUS_ADDRESS_NACK", text)
        self.assertIn("I2C_STATUS_DATA_NACK", text)
        self.assertIn("I2C_STATUS_ARBITRATION_LOST", text)
        self.assertIn("I2C_STATUS_TIMEOUT", text)
        # Deadline temporal real baseado no timer
        self.assertIn("x86_timer_is_calibrated()", text)
        self.assertIn("x86_timer_read_tsc()", text)

    def test_main_modular_kernel_graph_contract(self):
        text = MAIN.read_text(encoding="utf-8")
        self.assertIn("import kernel::drivers::i2c_physical_discovery::*;", text)
        self.assertIn("import kernel::drivers::i2c_designware::*;", text)

    def test_qemu_smoke_gate_invariants_preserved(self):
        smoke_text = SMOKE.read_text(encoding="utf-8")
        # Ensure fail-closed gate is completely untouched and intact
        self.assertIn("REQUIRED = (", smoke_text)
        self.assertIn("USER_FAULT_ISOLATED_READY", smoke_text)
        self.assertIn("BARE_METAL_READY", smoke_text)
        self.assertIn("SCHEDULER_ROUND_TRIP", smoke_text)
        # Discovery must be fail-safe and never block boot unconditionally
        disc_text = DISCOVERY.read_text(encoding="utf-8")
        self.assertNotIn("panic(", disc_text)
        self.assertNotIn("loop {", disc_text)


if __name__ == "__main__":
    unittest.main()

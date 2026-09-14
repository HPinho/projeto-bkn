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

    def test_i2c5a_pci_class_filtering_contract(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        # PCI Class 0x0C (Serial Bus), Subclasses 0x80 or 0x05 (SMBus/I2C)
        self.assertIn("pub const PCI_CLASS_SERIAL_BUS: u8 = 0x0C;", text)
        self.assertIn("pub const PCI_SUBCLASS_SMBUS: u8 = 0x05;", text)
        self.assertIn("pub const PCI_SUBCLASS_SERIAL_OTHER: u8 = 0x80;", text)
        # Intel LPSS Vendor ID
        self.assertIn("vendor_id == 0x8086", text)

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

    def test_i2c5d_semantic_fault_decoding_contract(self):
        text = DESIGNWARE.read_text(encoding="utf-8")
        # Accurate translation from hardware abort sources to core status codes
        self.assertIn("DW_ABRT_7B_ADDR_NOACK", text)
        self.assertIn("DW_ABRT_TXDATA_NOACK", text)
        self.assertIn("DW_ABRT_ARB_LOST", text)
        self.assertIn("I2C_STATUS_ADDRESS_NACK", text)
        self.assertIn("I2C_STATUS_DATA_NACK", text)
        self.assertIn("I2C_STATUS_ARBITRATION_LOST", text)
        self.assertIn("I2C_STATUS_TIMEOUT", text)

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

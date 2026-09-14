from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "kernel/src/drivers/i2c_designware.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class I2cDesignWareContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = MODULE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_designware_is_in_native_graph(self):
        self.assertIn("import kernel::drivers::i2c_designware::*;", self.main)

    def test_standard_designware_register_offsets(self):
        for token in (
            "pub const DW_IC_CON: u64 = 0x00",
            "pub const DW_IC_TAR: u64 = 0x04",
            "pub const DW_IC_DATA_CMD: u64 = 0x10",
            "pub const DW_IC_SS_SCL_HCNT: u64 = 0x14",
            "pub const DW_IC_SS_SCL_LCNT: u64 = 0x18",
            "pub const DW_IC_FS_SCL_HCNT: u64 = 0x1C",
            "pub const DW_IC_FS_SCL_LCNT: u64 = 0x20",
            "pub const DW_IC_INTR_STAT: u64 = 0x2C",
            "pub const DW_IC_INTR_MASK: u64 = 0x30",
            "pub const DW_IC_RAW_INTR_STAT: u64 = 0x34",
            "pub const DW_IC_CLR_INTR: u64 = 0x40",
            "pub const DW_IC_CLR_TX_ABRT: u64 = 0x54",
            "pub const DW_IC_ENABLE: u64 = 0x6C",
            "pub const DW_IC_STATUS: u64 = 0x70",
            "pub const DW_IC_TX_ABRT_SOURCE: u64 = 0x80",
            "pub const DW_IC_ENABLE_STATUS: u64 = 0x9C",
        ):
            self.assertIn(token, self.text)

    def test_designware_control_and_status_bits(self):
        for token in (
            "pub const DW_IC_CON_MASTER_MODE: u32 = 1 << 0",
            "pub const DW_IC_CON_SPEED_STD: u32 = 1 << 1",
            "pub const DW_IC_CON_SPEED_FAST: u32 = 2 << 1",
            "pub const DW_IC_CON_RESTART_EN: u32 = 1 << 5",
            "pub const DW_IC_CON_SLAVE_DISABLE: u32 = 1 << 6",
            "pub const DW_IC_STATUS_TFNF: u32 = 1 << 1",
            "pub const DW_IC_STATUS_TFE: u32 = 1 << 2",
            "pub const DW_IC_STATUS_RFNE: u32 = 1 << 3",
            "pub const DW_IC_RAW_INTR_TX_ABRT: u32 = 1 << 6",
        ):
            self.assertIn(token, self.text)

    def test_designware_abort_reasons_decoded(self):
        for token in (
            "pub const DW_ABRT_7B_ADDR_NOACK: u32 = 1 << 0",
            "pub const DW_ABRT_10ADDR1_NOACK: u32 = 1 << 1",
            "pub const DW_ABRT_10ADDR2_NOACK: u32 = 1 << 2",
            "pub const DW_ABRT_TXDATA_NOACK: u32 = 1 << 3",
            "pub const DW_ABRT_ARB_LOST: u32 = 1 << 12",
        ):
            self.assertIn(token, self.text)
        self.assertIn("pub fn i2c_dw_check_abort", self.text)
        self.assertIn("I2C_STATUS_ADDRESS_NACK", self.text)
        self.assertIn("I2C_STATUS_DATA_NACK", self.text)
        self.assertIn("I2C_STATUS_ARBITRATION_LOST", self.text)

    def test_designware_initialization_and_timing_calculation(self):
        self.assertIn("pub fn i2c_dw_init", self.text)
        self.assertIn("pub fn i2c_dw_enable", self.text)
        self.assertIn("DW_IC_SS_SCL_HCNT", self.text)
        self.assertIn("DW_IC_FS_SCL_HCNT", self.text)

    def test_designware_transfer_writes_directly_to_buffer(self):
        self.assertIn("pub fn i2c_dw_transfer", self.text)
        self.assertIn("DW_IC_CMD_READ", self.text)
        self.assertIn("DW_IC_CMD_STOP", self.text)
        self.assertIn("DW_IC_CMD_RESTART", self.text)
        self.assertIn("*buf.add(byte_idx) = received_byte;", self.text)


if __name__ == "__main__":
    unittest.main()

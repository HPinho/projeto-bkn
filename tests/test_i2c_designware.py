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

    def test_lpss_private_wrapper_offsets_and_64bit_remap(self):
        for token in (
            "pub const INTEL_LPSS_DEV_OFFSET: u64 = 0x000",
            "pub const INTEL_LPSS_DEV_SIZE: u64 = 0x200",
            "pub const INTEL_LPSS_PRIV_OFFSET: u64 = 0x200",
            "pub const INTEL_LPSS_PRIV_SIZE: u64 = 0x100",
            "pub const INTEL_LPSS_IDMA64_OFFSET: u64 = 0x800",
            "pub const LPSS_PRIV_REMAP_ADDR: u64 = 0x40",
            "pub const LPSS_PRIV_REMAP_ADDR_HIGH: u64 = 0x44",
            "pub const LPSS_PRIV_RESETS: u64 = 0x04",
            "pub const LPSS_PRIV_RESETS_FUNC: u32 = 0x03",
            "pub const LPSS_PRIV_RESETS_IDMA: u32 = 1 << 2",
            "pub const LPSS_PRIV_RESETS_BOTH: u32 = 0x07",
            "pub fn i2c_lpss_reset_release(base: u64, physical_address: u64) -> void",
            "let high_addr = ((physical_address >> 32) & 0xFFFFFFFF) as u32;",
            "x86_mmio_write32(priv_base + LPSS_PRIV_REMAP_ADDR_HIGH, high_addr);",
        ):
            self.assertIn(token, self.text)
        self.assertNotIn("pub const LPSS_PRIV_REMAP_ADDR: u64 = 0x00", self.text)

    def test_designware_control_and_status_bits(self):
        for token in (
            "pub const DW_IC_CON_MASTER_MODE: u32 = 1 << 0",
            "pub const DW_IC_CON_SPEED_STD: u32 = 1 << 1",
            "pub const DW_IC_CON_SPEED_FAST: u32 = 2 << 1",
            "pub const DW_IC_CON_SPEED_MASK: u32 = 3 << 1",
            "pub const DW_IC_CON_10BITADDR_MASTER: u32 = 1 << 4",
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

    def test_hardware_aware_timing_calculations(self):
        self.assertIn("pub fn i2c_dw_calc_scl_hcnt", self.text)
        self.assertIn("pub fn i2c_dw_calc_scl_lcnt", self.text)
        self.assertIn("pub fn i2c_dw_init_with_clock", self.text)

        def calc_hcnt(clk, target, fast):
            period = clk // target
            return (period * 36) // 100 if fast else (period * 45) // 100

        def calc_lcnt(clk, target, fast):
            period = clk // target
            return (period * 64) // 100 if fast else (period * 55) // 100

        self.assertEqual(calc_hcnt(100_000_000, 100_000, False), 450)
        self.assertEqual(calc_lcnt(100_000_000, 100_000, False), 550)
        self.assertEqual(calc_hcnt(100_000_000, 400_000, True), 90)
        self.assertEqual(calc_lcnt(100_000_000, 400_000, True), 160)
        self.assertEqual(calc_hcnt(133_000_000, 400_000, True), 119)
        self.assertEqual(calc_lcnt(133_000_000, 400_000, True), 212)
        self.assertEqual(calc_hcnt(216_000_000, 400_000, True), 194)
        self.assertEqual(calc_lcnt(216_000_000, 400_000, True), 345)

    def test_transfer_honors_only_certified_bus_speeds(self):
        self.assertIn("pub const DW_SUPPORTED_STANDARD_SPEED_HZ: u32 = 100000", self.text)
        self.assertIn("pub const DW_SUPPORTED_FAST_SPEED_HZ: u32 = 400000", self.text)
        self.assertIn("pub fn i2c_dw_speed_supported", self.text)
        self.assertIn("let bus_speed_hz = unsafe { (*transaction).bus_speed_hz };", self.text)
        self.assertIn("if !i2c_dw_speed_supported(bus_speed_hz)", self.text)
        self.assertIn("return I2C_STATUS_UNSUPPORTED;", self.text)
        self.assertIn("current_speed_bits != desired_speed_bits", self.text)

    def test_deadline_includes_enable_disable_reconfiguration_and_enable_recovery(self):
        self.assertIn("fn i2c_dw_enable_until", self.text)
        self.assertIn("deadline_tsc", self.text)
        self.assertIn("let enable_status = i2c_dw_read32(base, DW_IC_ENABLE_STATUS);", self.text)
        self.assertIn("let is_enabled = (enable_status & 1) != 0;", self.text)
        self.assertIn("current_speed_bits != desired_speed_bits ||", self.text)
        self.assertIn("!is_enabled", self.text)
        self.assertIn("is_enabled && !i2c_dw_enable_until(base, false, deadline_tsc, timeout_cycles)", self.text)
        self.assertIn("i2c_dw_enable_until(base, true, deadline_tsc, timeout_cycles)", self.text)
        self.assertNotIn("i2c_dw_enable(base, false);", self.text)

    def test_designware_transfer_writes_directly_to_buffer(self):
        self.assertIn("pub fn i2c_dw_transfer", self.text)
        self.assertIn("DW_IC_CMD_READ", self.text)
        self.assertIn("DW_IC_CMD_STOP", self.text)
        self.assertIn("DW_IC_CMD_RESTART", self.text)
        self.assertIn("*buf.add(byte_idx) = received_byte;", self.text)


if __name__ == "__main__":
    unittest.main()

"""Contratos I2C-1a para o core genérico de transações I2C."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/drivers/i2c_core.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
    raise AssertionError(f"unterminated function: {signature}")


class I2cCoreContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_in_native_sotlas_graph(self):
        self.assertIn("module kernel::drivers::i2c_core;", self.source)
        self.assertIn("import kernel::drivers::i2c_core::*;", self.main)

    def test_contract_exposes_bounded_messages_and_normalized_statuses(self):
        for token in (
            "I2C_DIRECTION_WRITE",
            "I2C_DIRECTION_READ",
            "I2C_STATUS_ADDRESS_NACK",
            "I2C_STATUS_DATA_NACK",
            "I2C_STATUS_ARBITRATION_LOST",
            "I2C_STATUS_BUS_BUSY",
            "I2C_STATUS_TIMEOUT",
            "I2C_STATUS_CONTROLLER_ERROR",
            "I2C_STATUS_UNSUPPORTED",
            "I2C_MAX_MESSAGES",
            "I2C_MAX_MESSAGE_BYTES",
            "I2C_MAX_TRANSACTION_BYTES",
            "I2C_TIMEOUT_MAX_US",
            "pub struct I2cMessage",
            "pub struct I2cTransaction",
            "pub struct I2cTransferPlan",
            "pub struct I2cControllerCapabilities",
            "pub struct I2cTransferResult",
        ):
            self.assertIn(token, self.source)

    def test_planner_is_bounded_and_fail_closed(self):
        body = function_body(self.source, "pub fn i2c_plan_transaction")
        for token in (
            "i2c_address_valid(address, ten_bit)",
            "speed == 0",
            "timeout == 0",
            "timeout > I2C_TIMEOUT_MAX_US",
            "count == 0",
            "count > I2C_MAX_MESSAGES",
            "direction != I2C_DIRECTION_WRITE",
            "direction != I2C_DIRECTION_READ",
            "data == (null as *mut u8)",
            "length == 0",
            "length > I2C_MAX_MESSAGE_BYTES",
            "length > I2C_MAX_TRANSACTION_BYTES - total",
        ):
            self.assertIn(token, body)

    def test_combined_and_ten_bit_reads_require_repeated_start(self):
        body = function_body(self.source, "pub fn i2c_plan_transaction")
        self.assertIn("restart_count: usize = count - 1", body)
        self.assertIn("ten_bit_read_restart", body)
        self.assertIn("restart_count += 1", body)
        supported = function_body(self.source, "pub fn i2c_plan_supported_by")
        self.assertIn("supports_repeated_start", supported)
        self.assertIn("repeated_start_count", supported)

    def test_controller_capabilities_bound_the_plan(self):
        valid = function_body(self.source, "pub fn i2c_controller_capabilities_valid")
        for token in (
            "supports_7bit",
            "supports_10bit",
            "max_messages",
            "max_message_bytes",
            "max_transaction_bytes",
            "max_speed_hz",
        ):
            self.assertIn(token, valid)
        supported = function_body(self.source, "pub fn i2c_plan_supported_by")
        for token in (
            "supports_10bit",
            "supports_7bit",
            "max_messages",
            "max_message_bytes",
            "max_transaction_bytes",
            "max_speed_hz",
        ):
            self.assertIn(token, supported)

    def test_results_are_explicit_and_consistency_checked(self):
        success = function_body(self.source, "pub fn i2c_result_success")
        self.assertIn("I2C_STATUS_OK", success)
        self.assertIn("I2C_INVALID_MESSAGE_INDEX", success)
        error = function_body(self.source, "pub fn i2c_result_error")
        self.assertIn("status == I2C_STATUS_OK", error)
        self.assertIn("status == I2C_STATUS_INVALID", error)
        self.assertIn("completed_messages >", error)
        self.assertIn("transferred_bytes >", error)
        consistent = function_body(self.source, "pub fn i2c_result_consistent")
        self.assertIn("i2c_status_valid", consistent)
        self.assertIn("failed_message_index", consistent)

    def test_i2c_1a_is_stateless_and_has_no_hardware_side_effects(self):
        lower = self.source.lower()
        self.assertNotIn("static mut", lower)
        for forbidden in (
            "mmio_read", "mmio_write", "pci_read", "pci_write",
            "dma_alloc", "dma_release", "pmm_", "irq_register", "irq_route",
            "__in8", "__in16", "__in32", "__out8", "__out16", "__out32",
            "gpio_program", "xhci_", "aml_evaluate", "execute_method",
        ):
            self.assertNotIn(forbidden, lower)


if __name__ == "__main__":
    unittest.main()

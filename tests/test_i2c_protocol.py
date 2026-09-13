"""Contratos I2C-1c para state machine genérica e recovery lógico."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/drivers/i2c_protocol.sotlas"
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


class I2cProtocolContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_in_native_graph_after_executor(self):
        self.assertIn("module kernel::drivers::i2c_protocol;", self.source)
        self.assertIn("import kernel::drivers::i2c_core::*;", self.source)
        self.assertIn("import kernel::drivers::i2c_executor::*;", self.source)
        executor = self.main.index("import kernel::drivers::i2c_executor::*;")
        protocol = self.main.index("import kernel::drivers::i2c_protocol::*;")
        self.assertLess(executor, protocol)

    def test_state_machine_exposes_only_abstract_protocol_actions(self):
        for token in (
            "I2C_PROTOCOL_ACTION_START",
            "I2C_PROTOCOL_ACTION_ADDRESS",
            "I2C_PROTOCOL_ACTION_WRITE_BYTE",
            "I2C_PROTOCOL_ACTION_READ_BYTE",
            "I2C_PROTOCOL_ACTION_REPEATED_START",
            "I2C_PROTOCOL_ACTION_STOP",
            "I2C_PROTOCOL_ACTION_RECOVER",
            "pub struct I2cProtocolAction",
            "pub struct I2cProtocolEvent",
            "pub struct I2cProtocolMachine",
        ):
            self.assertIn(token, self.source)

    def test_begin_requires_certified_backend_request_and_preserves_borrow(self):
        body = function_body(self.source, "pub fn i2c_protocol_begin")
        self.assertIn("i2c_backend_request_ready(request)", body)
        self.assertIn("transaction: (*request).transaction", body)
        self.assertIn("plan: (*request).plan", body)
        self.assertIn("state: I2C_PROTOCOL_STATE_NEED_START", body)
        self.assertIn("terminal_status: I2C_STATUS_OK", body)

    def test_issue_serializes_start_address_data_restart_stop(self):
        body = function_body(self.source, "pub fn i2c_protocol_issue")
        for token in (
            "I2C_PROTOCOL_STATE_NEED_START",
            "I2C_PROTOCOL_ACTION_START",
            "I2C_PROTOCOL_STATE_NEED_ADDRESS",
            "I2C_PROTOCOL_ACTION_ADDRESS",
            "I2C_PROTOCOL_STATE_NEED_DATA",
            "I2C_PROTOCOL_ACTION_WRITE_BYTE",
            "I2C_PROTOCOL_ACTION_READ_BYTE",
            "I2C_PROTOCOL_STATE_NEED_RESTART",
            "I2C_PROTOCOL_ACTION_REPEATED_START",
            "I2C_PROTOCOL_STATE_NEED_STOP",
            "I2C_PROTOCOL_ACTION_STOP",
            "I2C_PROTOCOL_STATE_NEED_RECOVERY",
            "I2C_PROTOCOL_ACTION_RECOVER",
            "(*machine).awaiting_event = true",
        ):
            self.assertIn(token, body)

    def test_read_last_byte_is_nack_and_10bit_restart_stays_in_address_phase(self):
        body = function_body(self.source, "pub fn i2c_protocol_issue")
        self.assertIn("ack_after_read: direction == I2C_DIRECTION_READ", body)
        self.assertIn("((*machine).byte_index + 1) < length", body)
        self.assertIn("address_phase_restart: (*machine).plan.ten_bit_read_address_restart", body)
        self.assertIn("direction == I2C_DIRECTION_READ", body)

    def test_event_status_is_action_scoped(self):
        body = function_body(self.source, "fn i2c_protocol_status_allowed_for_action")
        self.assertIn("status == I2C_STATUS_ADDRESS_NACK", body)
        self.assertIn("action == I2C_PROTOCOL_ACTION_ADDRESS", body)
        self.assertIn("status == I2C_STATUS_DATA_NACK", body)
        self.assertIn("action == I2C_PROTOCOL_ACTION_WRITE_BYTE", body)
        self.assertIn("status == I2C_STATUS_UNSUPPORTED", body)

    def test_progress_moves_to_restart_between_messages_and_stop_after_last(self):
        body = function_body(self.source, "pub fn i2c_protocol_accept_event")
        for token in (
            "(*machine).transferred_bytes += 1",
            "(*machine).completed_messages += 1",
            "(*machine).message_index += 1",
            "I2C_PROTOCOL_STATE_NEED_RESTART",
            "I2C_PROTOCOL_STATE_NEED_STOP",
        ):
            self.assertIn(token, body)

    def test_failure_is_fail_closed_without_retry_and_recovery_is_single_attempt(self):
        record = function_body(self.source, "fn i2c_protocol_record_failure")
        issue = function_body(self.source, "pub fn i2c_protocol_issue")
        self.assertIn("terminal_status == I2C_STATUS_OK", record)
        self.assertIn("I2C_PROTOCOL_STATE_NEED_RECOVERY", record)
        self.assertIn("I2C_PROTOCOL_STATE_FAILED", record)
        self.assertIn("recovery_attempted", issue)
        self.assertIn("if (*machine).recovery_attempted", issue)
        self.assertNotIn("message_index = 0", record)
        self.assertNotIn("byte_index = 0", record)

    def test_stop_requires_bus_release_and_controller_quiescence(self):
        body = function_body(self.source, "pub fn i2c_protocol_accept_event")
        self.assertIn("I2C_PROTOCOL_ACTION_STOP", body)
        self.assertIn("bus_ownership_released && (*event).controller_quiesced", body)
        self.assertIn("terminal_status = I2C_STATUS_CONTROLLER_ERROR", body)
        self.assertIn("state = I2C_PROTOCOL_STATE_NEED_RECOVERY", body)

    def test_completion_adapts_to_i2c_1b_without_reading_a_clock(self):
        body = function_body(self.source, "pub fn i2c_protocol_completion")
        self.assertIn("elapsed_us: u64", self.source)
        self.assertIn("I2cBackendCompletion", self.source)
        self.assertIn("elapsed_us: elapsed_us", body)
        self.assertIn("completed_messages: (*machine).completed_messages", body)
        self.assertIn("transferred_bytes: (*machine).transferred_bytes", body)
        self.assertIn("bus_ownership_released: (*machine).bus_ownership_released", body)

    def test_i2c_1c_has_no_physical_backend_or_hidden_retry(self):
        lower = self.source.lower()
        self.assertNotIn("static mut", lower)
        for forbidden in (
            "mmio_read", "mmio_write", "pci_read", "pci_write",
            "dma_alloc", "dma_release", "pmm_", "irq_register", "irq_route",
            "x86_mmio", "__in8", "__in16", "__in32", "__out8", "__out16", "__out32",
            "gpio_program", "xhci_", "aml_evaluate", "execute_method",
            "irq_timer_count", "timer_count", "sleep_ms", "sleep_us", "busy_wait",
            "retry_count", "automatic_retry",
        ):
            self.assertNotIn(forbidden, lower)


if __name__ == "__main__":
    unittest.main()

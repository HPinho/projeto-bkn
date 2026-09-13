"""Contratos I2C-1b para executor e fronteira data-oriented de backend."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "kernel/src/drivers/i2c_executor.sotlas"
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


class I2cExecutorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.main = MAIN.read_text(encoding="utf-8")

    def test_module_is_in_native_sotlas_graph(self):
        self.assertIn("module kernel::drivers::i2c_executor;", self.source)
        self.assertIn("import kernel::drivers::i2c_core::*;", self.source)
        self.assertIn("import kernel::drivers::i2c_executor::*;", self.main)

    def test_backend_boundary_is_data_oriented_and_borrowed(self):
        for token in (
            "pub struct I2cBackendRequest",
            "pub transaction: *const I2cTransaction",
            "pub plan: I2cTransferPlan",
            "pub timeout_budget_us: u64",
            "pub struct I2cBackendCompletion",
            "pub elapsed_us: u64",
            "pub bus_ownership_released: bool",
            "pub controller_quiesced: bool",
            "pub struct I2cExecutionOutcome",
            "pub deadline_exceeded: bool",
            "pub recovery_required: bool",
        ):
            self.assertIn(token, self.source)

    def test_prepare_reuses_certified_planner_and_capability_gate(self):
        body = function_body(self.source, "pub fn i2c_executor_prepare")
        for token in (
            "i2c_controller_capabilities_valid(caps)",
            "i2c_plan_transaction(transaction)",
            "!plan.valid",
            "!i2c_plan_supported_by(&plan, caps)",
            "I2C_STATUS_UNSUPPORTED",
            "timeout_budget_us: plan.timeout_us",
            "I2C_STATUS_OK",
        ):
            self.assertIn(token, body)

    def test_backend_request_ready_requires_exact_timeout_budget(self):
        body = function_body(self.source, "pub fn i2c_backend_request_ready")
        self.assertIn("status == I2C_STATUS_OK", body)
        self.assertIn("transaction != (null as *const I2cTransaction)", body)
        self.assertIn("plan.valid", body)
        self.assertIn("timeout_budget_us == (*request).plan.timeout_us", body)

    def test_completion_is_bounded_by_the_request_plan(self):
        body = function_body(self.source, "pub fn i2c_backend_completion_valid")
        for token in (
            "i2c_backend_request_ready(request)",
            "i2c_status_valid((*completion).status)",
            "status == I2C_STATUS_INVALID",
            "completed_messages > (*request).plan.message_count",
            "transferred_bytes > (*request).plan.total_bytes",
            "failed_message_index >= (*request).plan.message_count",
            "status == I2C_STATUS_OK",
            "failed_message_index == I2C_INVALID_MESSAGE_INDEX",
        ):
            self.assertIn(token, body)

    def test_finish_propagates_deadline_and_recovery_without_hiding_error(self):
        body = function_body(self.source, "pub fn i2c_executor_finish")
        for token in (
            "elapsed_us > (*request).timeout_budget_us",
            "status = I2C_STATUS_TIMEOUT",
            "!(*completion).bus_ownership_released",
            "!(*completion).controller_quiesced",
            "status == I2C_STATUS_OK && recovery_required",
            "status = I2C_STATUS_CONTROLLER_ERROR",
            "i2c_result_success",
            "i2c_result_error",
            "i2c_result_consistent",
        ):
            self.assertIn(token, body)

    def test_unsupported_preflight_can_return_without_backend_execution(self):
        body = function_body(self.source, "pub fn i2c_executor_immediate_result")
        self.assertIn("status != I2C_STATUS_UNSUPPORTED", body)
        self.assertIn("I2C_STATUS_UNSUPPORTED", body)
        self.assertIn("i2c_result_error", body)

    def test_i2c_1b_has_no_global_state_or_physical_backend_side_effects(self):
        lower = self.source.lower()
        self.assertNotIn("static mut", lower)
        for forbidden in (
            "mmio_read", "mmio_write", "pci_read", "pci_write",
            "dma_alloc", "dma_release", "pmm_", "irq_register", "irq_route",
            "x86_mmio", "__in8", "__in16", "__in32", "__out8", "__out16", "__out32",
            "gpio_program", "xhci_", "aml_evaluate", "execute_method",
            "irq_timer_count", "timer_count", "sleep_ms", "sleep_us",
        ):
            self.assertNotIn(forbidden, lower)


if __name__ == "__main__":
    unittest.main()

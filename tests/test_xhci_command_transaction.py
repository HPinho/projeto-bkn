#!/usr/bin/env python3
"""Guardrails SMP para a transação global do Command Ring xHCI."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "kernel/src/drivers/xhci_command.sotlas"
KERNEL_SRC = ROOT / "kernel/src"


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"missing function {name}")
    brace = source.find("{", match.end())
    if brace < 0:
        raise AssertionError(f"missing function body {name}")

    depth = 0
    index = brace
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
                continue
            index += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:index]
        index += 1
    raise AssertionError(f"unterminated function {name}")


def ordered_positions(body: str, *tokens: str) -> list[int]:
    positions: list[int] = []
    cursor = 0
    for token in tokens:
        position = body.find(token, cursor)
        if position < 0:
            raise AssertionError(f"missing ordered token: {token}")
        positions.append(position)
        cursor = position + len(token)
    return positions


class XhciCommandTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = COMMAND.read_text(encoding="utf-8")
        cls.capture = function_body(
            cls.source, "xhci_command_execute_capture_slot"
        )
        cls.execute = function_body(cls.source, "xhci_command_execute")

    def test_global_command_ring_has_dedicated_transaction_lock(self):
        self.assertIn("import kernel::sync::spinlock::*;", self.source)
        self.assertRegex(
            self.source,
            r"static\s+mut\s+XHCI_COMMAND_TRANSACTION_LOCK\s*:\s*SpinLock\s*=\s*"
            r"SpinLock\s*\{\s*state:\s*SPINLOCK_UNLOCKED\s*\}",
        )

    def test_raw_submit_and_wait_are_private_primitives(self):
        self.assertRegex(self.source, r"(?m)^fn\s+xhci_command_submit\s*\(")
        self.assertRegex(
            self.source, r"(?m)^fn\s+xhci_command_wait_completion\s*\("
        )
        self.assertNotRegex(
            self.source, r"(?m)^pub\s+fn\s+xhci_command_submit\s*\("
        )
        self.assertNotRegex(
            self.source,
            r"(?m)^pub\s+fn\s+xhci_command_wait_completion\s*\(",
        )

    def test_transaction_is_irq_and_preemption_safe(self):
        ordered_positions(
            self.capture,
            "x86_irq_save_disable()",
            "spinlock_lock(&mut XHCI_COMMAND_TRANSACTION_LOCK)",
            "xhci_command_submit(command)",
            "xhci_command_wait_completion(command_physical)",
            "completed_slot_id = XHCI_COMMAND_LAST_SLOT_ID",
            "spinlock_unlock(&mut XHCI_COMMAND_TRANSACTION_LOCK)",
            "x86_irq_restore(flags)",
            "return completed_slot_id;",
        )
        failed_lock = self.capture.find("if !locked")
        restore_after_failure = self.capture.find("x86_irq_restore(flags)", failed_lock)
        first_submit = self.capture.find("xhci_command_submit(command)")
        self.assertGreaterEqual(failed_lock, 0)
        self.assertGreater(restore_after_failure, failed_lock)
        self.assertLess(restore_after_failure, first_submit)

    def test_no_early_return_after_successful_lock_acquisition(self):
        failure_return = self.capture.find("return 0;", self.capture.find("if !locked"))
        submit = self.capture.find("xhci_command_submit(command)")
        unlock = self.capture.rfind(
            "spinlock_unlock(&mut XHCI_COMMAND_TRANSACTION_LOCK)"
        )
        self.assertGreaterEqual(failure_return, 0)
        self.assertGreater(submit, failure_return)
        self.assertGreater(unlock, submit)
        critical = self.capture[submit:unlock]
        self.assertNotRegex(critical, r"\breturn\b")

    def test_irq_restore_happens_only_after_unlock_on_success(self):
        unlock = self.capture.rfind(
            "spinlock_unlock(&mut XHCI_COMMAND_TRANSACTION_LOCK)"
        )
        restore = self.capture.rfind("x86_irq_restore(flags)")
        final_return = self.capture.rfind("return completed_slot_id;")
        self.assertGreater(restore, unlock)
        self.assertGreater(final_return, restore)

    def test_expected_slot_wrapper_matches_captured_completion(self):
        self.assertIn("if expected_slot_id == 0 { return false; }", self.execute)
        self.assertIn(
            "xhci_command_execute_capture_slot(command) == expected_slot_id",
            self.execute,
        )

    def test_drivers_cannot_bypass_transaction_api(self):
        forbidden = (
            "xhci_command_submit(",
            "xhci_command_wait_completion(",
            "xhci_command_last_slot_id()",
        )
        offenders: list[str] = []
        for path in KERNEL_SRC.rglob("*.sotlas"):
            if path == COMMAND:
                continue
            source = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in source:
                    offenders.append(f"{path.relative_to(ROOT)}: {token}")
        self.assertEqual([], offenders, "raw Command Ring API bypasses found")

    def test_enable_slot_uses_capture_api_and_fixed_slot_commands_use_execute(self):
        slot = (KERNEL_SRC / "drivers/xhci_slot.sotlas").read_text(encoding="utf-8")
        self.assertIn("xhci_command_execute_capture_slot(command)", slot)
        for relative in (
            "drivers/xhci_address.sotlas",
            "drivers/xhci_evaluate_context.sotlas",
            "drivers/xhci_configure_endpoint.sotlas",
            "drivers/xhci_hid_lifecycle.sotlas",
        ):
            source = (KERNEL_SRC / relative).read_text(encoding="utf-8")
            self.assertIn("xhci_command_execute(command, slot_id)", source, relative)


if __name__ == "__main__":
    unittest.main()

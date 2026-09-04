#!/usr/bin/env python3
"""Guardrails for x86-64 exception stubs and Sotlas dispatcher."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
EXCEPTIONS = ROOT / "kernel/src/arch/x86_64/exceptions.sotlas"
MAIN = ROOT / "kernel/src/main.sotlas"


class X86ExceptionTests(unittest.TestCase):
    def test_backend_emits_all_32_exception_stubs(self):
        text = BACKEND.read_text(encoding="utf-8")
        vectors = {
            int(match.group(1))
            for match in re.finditer(r"BAKEN_ISR_(?:NOERR|ERR)\((\d+)\)", text)
        }
        self.assertEqual(vectors, set(range(32)))
        self.assertIn("__baken_exception_common", text)
        self.assertIn("call baken_exception_dispatch", text)

    def test_error_code_vectors_are_not_given_synthetic_error_codes(self):
        text = BACKEND.read_text(encoding="utf-8")
        expected = {8, 10, 11, 12, 13, 14, 17, 21, 29, 30}
        actual = {
            int(match.group(1))
            for match in re.finditer(r"BAKEN_ISR_ERR\((\d+)\)", text)
        }
        self.assertEqual(actual, expected)
        for vector in set(range(32)) - expected:
            self.assertIn(f"BAKEN_ISR_NOERR({vector})", text)

    def test_exception_frame_matches_normalized_stack_prefix(self):
        text = EXCEPTIONS.read_text(encoding="utf-8")
        fields = ["vector: u64", "error_code: u64", "rip: u64", "cs: u64", "rflags: u64"]
        for field in fields:
            self.assertIn(field, text)
        self.assertIn("@repr(C)\n@packed\npub struct ExceptionRawFrame", text)

    def test_page_fault_records_cr2_and_decodes_error_bits(self):
        text = EXCEPTIONS.read_text(encoding="utf-8")
        self.assertIn("EXCEPTION_PAGE_FAULT: u64 = 14", text)
        self.assertIn("LAST_EXCEPTION.cr2 = x86_read_cr2()", text)
        self.assertIn("@export\npub fn baken_exception_dispatch", text)
        for token in (
            "PAGE_FAULT_PRESENT: u64 = 1",
            "PAGE_FAULT_WRITE: u64 = 2",
            "PAGE_FAULT_USER: u64 = 4",
            "PAGE_FAULT_RESERVED_BIT: u64 = 8",
            "PAGE_FAULT_INSTRUCTION_FETCH: u64 = 16",
            "PAGE_FAULT_PROTECTION_KEY: u64 = 32",
            "PAGE_FAULT_SHADOW_STACK: u64 = 64",
            "page_fault_was_protection_violation",
            "page_fault_was_instruction_fetch",
        ):
            self.assertIn(token, text)

    def test_dispatcher_is_terminal_until_full_restore_abi_exists(self):
        text = EXCEPTIONS.read_text(encoding="utf-8")
        code_only = re.sub(r"//[^\n]*", "", text)
        self.assertIn("__cli();", code_only)
        self.assertIn("loop { __hlt(); }", code_only)
        self.assertNotRegex(code_only.lower(), r"\b(?:x86_)?iretq?\s*\(")

    def test_boot_still_does_not_activate_private_descriptor_tables(self):
        main = MAIN.read_text(encoding="utf-8")
        self.assertIn("exception_state_reset()", main)
        self.assertNotIn("x86_lgdt_raw(", main)
        self.assertNotIn("x86_lidt_raw(", main)
        self.assertNotIn("x86_ltr_raw(", main)


if __name__ == "__main__":
    unittest.main()

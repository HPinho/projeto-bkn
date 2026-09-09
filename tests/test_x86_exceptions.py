#!/usr/bin/env python3
"""Guardrails for x86-64 exception stubs and Sotlas dispatcher."""
from pathlib import Path
import re, unittest
ROOT=Path(__file__).resolve().parents[1]; BACKEND=ROOT/"tools/sotlas_compile/x86_intrinsics.py"; EXCEPTIONS=ROOT/"kernel/src/arch/x86_64/exceptions.sotlas"; CPU=ROOT/"kernel/src/arch/x86_64/cpu.sotlas"; POST=ROOT/"kernel/src/arch/x86_64/post_cutover.sotlas"
class X86ExceptionTests(unittest.TestCase):
    def test_backend_emits_all_32_exception_stubs(self):
        text=BACKEND.read_text(encoding="utf-8"); vectors={int(m.group(1)) for m in re.finditer(r"SOTLAS_X86_ISR_(?:NOERR|ERR)\((\d+)\)",text)}; self.assertEqual(vectors,set(range(32)))
        self.assertIn("__sotlas_x86_exception_common",text); self.assertIn("call sotlas_x86_exception_dispatch",text)
        self.assertRegex(text,r"__attribute__\(\(\s*naked\s*,\s*used\s*\)\)\s+static\s+void\s+__sotlas_x86_exception_common")
        self.assertRegex(text,r"__attribute__\(\(\s*naked\s*,\s*unused\s*\)\)\s+static\s+void\s+__sotlas_x86_isr_##n")
        self.assertNotIn("baken_exception_dispatch",text)
    def test_error_code_vectors_are_not_given_synthetic_error_codes(self):
        text=BACKEND.read_text(encoding="utf-8"); expected={8,10,11,12,13,14,17,21,29,30}; actual={int(m.group(1)) for m in re.finditer(r"SOTLAS_X86_ISR_ERR\((\d+)\)",text)}; self.assertEqual(actual,expected)
        for vector in set(range(32))-expected: self.assertIn(f"SOTLAS_X86_ISR_NOERR({vector})",text)
    def test_generic_stub_address_builtin_is_exposed_without_idt_policy(self):
        backend=BACKEND.read_text(encoding="utf-8"); cpu=CPU.read_text(encoding="utf-8"); self.assertIn("static inline uint64_t __exception_stub_address(uint16_t vector)",backend); self.assertIn('"__exception_stub_address": Function(',backend); self.assertIn("pub fn x86_exception_stub_address(vector: u16) -> u64",cpu); self.assertNotIn("IDT_GATE_INTERRUPT",backend); self.assertNotIn("IDT_VECTOR_DOUBLE_FAULT",backend)
    def test_exception_frame_matches_normalized_stack_prefix(self):
        text=EXCEPTIONS.read_text(encoding="utf-8"); [self.assertIn(field,text) for field in ("r15: u64","rax: u64","vector: u64","error_code: u64","rip: u64","cs: u64","rflags: u64","rsp: u64","ss: u64")]; self.assertIn("@repr(C)\n@packed\npub struct ExceptionSavedFrame",text)
    def test_page_fault_records_cr2_and_decodes_error_bits(self):
        text=EXCEPTIONS.read_text(encoding="utf-8"); self.assertIn("EXCEPTION_PAGE_FAULT: u64 = 14",text); self.assertIn("LAST_EXCEPTION.cr2 = x86_read_cr2()",text); self.assertIn("@export\npub fn sotlas_x86_exception_dispatch",text)
        for token in ("PAGE_FAULT_PRESENT: u64 = 1","PAGE_FAULT_WRITE: u64 = 2","PAGE_FAULT_USER: u64 = 4","PAGE_FAULT_RESERVED_BIT: u64 = 8","PAGE_FAULT_INSTRUCTION_FETCH: u64 = 16","PAGE_FAULT_PROTECTION_KEY: u64 = 32","PAGE_FAULT_SHADOW_STACK: u64 = 64","page_fault_was_protection_violation","page_fault_was_instruction_fetch"): self.assertIn(token,text)
    def test_user_faults_return_to_scheduler_while_kernel_faults_remain_terminal(self):
        exceptions=EXCEPTIONS.read_text(encoding="utf-8"); backend=BACKEND.read_text(encoding="utf-8")
        self.assertIn("user = (frame.cs & 3) == 3", exceptions)
        self.assertIn("scheduler_terminate_current()", exceptions)
        self.assertIn("irq_schedule_terminated_current(frame_address)", exceptions)
        self.assertIn("return exception_terminal", exceptions)
        self.assertIn("exception_write_user_exit_marker()", exceptions)
        self.assertIn("66,65,75,69,78,58,85,83,69,82,95,70,65,85,76,84,95,69,88,73,84,10", exceptions)
        self.assertIn('"addq $8, %rsp\\n\\t" "iretq\\n\\t"', backend)
        self.assertIn('"2: cli\\n\\t" "1: hlt\\n\\t"', backend)
    def test_post_cutover_prepares_and_loads_private_exception_idt(self):
        body=POST.read_text(encoding="utf-8").split("pub fn post_cutover_activate_cpu",1)[1].split("pub fn post_cutover_cpu_tables_active",1)[0]
        for token in ("idt_prepare_exceptions()","idt_exceptions_ready()","x86_lidt_table_raw(idt_address, idt_limit())","x86_mmu_activate_root(snapshot.root_physical)"): self.assertIn(token,body)
        self.assertLess(body.index("x86_mmu_activate_root(snapshot.root_physical)"),body.index("x86_lidt_table_raw(idt_address, idt_limit())"))
if __name__ == "__main__": unittest.main()

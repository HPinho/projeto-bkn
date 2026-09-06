#!/usr/bin/env python3
"""Guardrails for the active x86_64 descriptor-table foundation."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "kernel/src/arch/x86_64"
POST = ARCH / "post_cutover.sotlas"


class X8664FoundationTests(unittest.TestCase):
    def test_gdt_has_long_mode_selectors_and_real_storage(self):
        text = (ARCH / "gdt.sotlas").read_text(encoding="utf-8")
        for token in ("GDT_KERNEL_CODE_SELECTOR: u16 = 0x08", "GDT_KERNEL_DATA_SELECTOR: u16 = 0x10", "GDT_USER_CODE_SELECTOR: u16 = 0x1B", "GDT_USER_DATA_SELECTOR: u16 = 0x23", "GDT_TSS_SELECTOR: u16 = 0x28", "static mut GDT_ENTRIES: [u64; GDT_ENTRY_COUNT]", "gdt_set_tss_descriptor"):
            self.assertIn(token, text)
        self.assertIn("@repr(C)\n@packed\npub struct DescriptorTablePointer", text)

    def test_tss_is_packed_and_uses_104_byte_long_mode_layout(self):
        text = (ARCH / "tss.sotlas").read_text(encoding="utf-8")
        self.assertIn("@repr(C)\n@packed\npub struct Tss64", text)
        self.assertIn("TSS.io_map_base = 104", text)
        self.assertIn("pub fn tss_limit() -> u32", text)
        self.assertIn("return 103;", text)
        self.assertIn("pub fn tss_size() -> u32", text)
        self.assertIn("return 104;", text)

    def test_tss_has_real_rsp0_and_critical_ist_stack_storage(self):
        text = (ARCH / "tss.sotlas").read_text(encoding="utf-8")
        for token in ("static mut KERNEL_RSP0_STACK", "static mut DOUBLE_FAULT_STACK", "static mut NMI_STACK", "static mut MACHINE_CHECK_STACK", "TSS_STACK_ALIGNMENT_MASK: u64 = 0xFFFFFFFFFFFFFFF0", "pub fn tss_prepare_default_stacks()"):
            self.assertIn(token, text)

    def test_idt_owns_256_concrete_packed_16_byte_gates(self):
        text = (ARCH / "idt.sotlas").read_text(encoding="utf-8")
        for token in ("IDT_VECTOR_COUNT: usize = 256", "@repr(C)\n@packed\npub struct IdtGate", "@repr(C)\n@packed\npub struct IdtDescriptorTablePointer", "static mut IDT: [IdtGate; IDT_VECTOR_COUNT]", "handler >> 32", "IDT[idx].ist = ist & 7", "((IDT_VECTOR_COUNT * 16) - 1) as u16"):
            self.assertIn(token, text)

    def test_exception_gate_policy_reserves_critical_ists(self):
        text = (ARCH / "idt.sotlas").read_text(encoding="utf-8")
        for token in ("IDT_VECTOR_DOUBLE_FAULT: u16 = 8", "IDT_VECTOR_NMI: u16 = 2", "IDT_VECTOR_MACHINE_CHECK: u16 = 18", "if vector == IDT_VECTOR_DOUBLE_FAULT { return 1; }", "if vector == IDT_VECTOR_NMI { return 2; }", "if vector == IDT_VECTOR_MACHINE_CHECK { return 3; }", "pub fn idt_set_exception_gate(vector: u16, handler: u64)"):
            self.assertIn(token, text)

    def test_idt_populates_0_through_31_from_native_stub_addresses(self):
        text = (ARCH / "idt.sotlas").read_text(encoding="utf-8")
        cpu = (ARCH / "cpu.sotlas").read_text(encoding="utf-8")
        self.assertIn("IDT_EXCEPTION_COUNT: u16 = 32", text)
        self.assertIn("pub fn idt_prepare_exceptions() -> bool", text)
        self.assertIn("x86_exception_stub_address(vector)", text)
        self.assertIn("idt_set_exception_gate(vector, handler)", text)
        self.assertIn("pub fn x86_exception_stub_address(vector: u16) -> u64", cpu)
        self.assertIn("return __exception_stub_address(vector);", cpu)

    def test_post_cutover_loads_private_cpu_tables_after_activating_cr3(self):
        post = POST.read_text(encoding="utf-8")
        body = post.split("pub fn post_cutover_activate_cpu", 1)[1].split("pub fn post_cutover_cpu_tables_active", 1)[0]
        for token in ("x86_mmu_activate_root(context.root_physical)", "tss_prepare_default_stacks()", "gdt_prepare()", "gdt_set_tss_descriptor(tss_base(), tss_limit())", "idt_prepare_exceptions()", "x86_gdt_activate_segments_raw(", "x86_ltr_raw(GDT_TSS_SELECTOR)", "x86_lidt_table_raw("):
            self.assertIn(token, body)
        self.assertLess(body.index("x86_mmu_activate_root(context.root_physical)"), body.index("x86_gdt_activate_segments_raw("))


if __name__ == "__main__": unittest.main()

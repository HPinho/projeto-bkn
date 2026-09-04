#!/usr/bin/env python3
"""Guardrails for the staged x86_64 descriptor-table foundation."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "kernel/src/arch/x86_64"


class X8664FoundationTests(unittest.TestCase):
    def test_gdt_has_long_mode_selectors_and_real_storage(self):
        text = (ARCH / "gdt.sotlas").read_text(encoding="utf-8")
        for token in (
            "GDT_KERNEL_CODE_SELECTOR: u16 = 0x08",
            "GDT_KERNEL_DATA_SELECTOR: u16 = 0x10",
            "GDT_USER_CODE_SELECTOR: u16 = 0x1B",
            "GDT_USER_DATA_SELECTOR: u16 = 0x23",
            "GDT_TSS_SELECTOR: u16 = 0x28",
            "static mut GDT_ENTRIES: [u64; GDT_ENTRY_COUNT]",
            "gdt_set_tss_descriptor",
        ):
            self.assertIn(token, text)
        self.assertIn("@packed\npub struct DescriptorTablePointer", text)

    def test_tss_is_packed_and_uses_104_byte_long_mode_layout(self):
        text = (ARCH / "tss.sotlas").read_text(encoding="utf-8")
        self.assertIn("@repr(C)\n@packed\npub struct Tss64", text)
        self.assertIn("TSS.io_map_base = 104", text)
        self.assertIn("pub fn tss_limit() -> u32", text)
        self.assertIn("return 103;", text)
        self.assertIn("pub fn tss_size() -> u32", text)
        self.assertIn("return 104;", text)

    def test_idt_owns_256_concrete_16_byte_gates(self):
        text = (ARCH / "idt.sotlas").read_text(encoding="utf-8")
        self.assertIn("IDT_VECTOR_COUNT: usize = 256", text)
        self.assertIn("static mut IDT: [IdtGate; IDT_VECTOR_COUNT]", text)
        self.assertIn("handler >> 32", text)
        self.assertIn("IDT[idx].ist = ist & 7", text)
        self.assertIn("((IDT_VECTOR_COUNT * 16) - 1) as u16", text)

    def test_kernel_prepares_but_does_not_claim_cpu_tables_are_loaded(self):
        main = (ROOT / "kernel/src/main.sotlas").read_text(encoding="utf-8")
        for token in (
            "tss_prepare(0, 0, 0, 0)",
            "gdt_prepare()",
            "gdt_set_tss_descriptor(tss_base(), tss_limit())",
            "idt_prepare_empty()",
        ):
            self.assertIn(token, main)
        self.assertNotIn("__lgdt(", main)
        self.assertNotIn("__lidt(", main)
        self.assertNotIn("__ltr(", main)


if __name__ == "__main__":
    unittest.main()

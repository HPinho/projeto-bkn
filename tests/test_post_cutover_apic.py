#!/usr/bin/env python3
"""Guardrails para ACPI/APIC depois de ExitBootServices."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
ACPI = ROOT / "kernel/src/acpi/tables.sotlas"
LAPIC = ROOT / "kernel/src/interrupts/lapic.sotlas"
IOAPIC = ROOT / "kernel/src/interrupts/ioapic.sotlas"
ACTIVE = ROOT / "kernel/src/memory/active_page_tables.sotlas"
X86 = ROOT / "tools/sotlas_compile/x86_intrinsics.py"


class PostCutoverApicTests(unittest.TestCase):
    def test_acpi_post_cutover_translates_physical_sdts(self):
        text = ACPI.read_text(encoding="utf-8")
        self.assertIn("acpi_init_post_cutover", text)
        self.assertIn("ACPI_POST_CUTOVER_DIRECT_MAP", text)
        self.assertIn("direct_map_virtual_address(physical_address)", text)
        self.assertIn("let table = acpi_sdt_pointer(address);", text)

    def test_mmio_backend_is_volatile(self):
        text = X86.read_text(encoding="utf-8")
        self.assertIn("__mmio_read32", text)
        self.assertIn("__mmio_write32", text)
        self.assertIn("volatile uint32_t", text)
        self.assertIn('__asm__ __volatile__("" : : : "memory");', text)

    def test_active_mapper_only_maps_explicit_mmio_pages(self):
        text = ACTIVE.read_text(encoding="utf-8")
        self.assertIn("active_page_tables_map_mmio_identity_4k", text)
        self.assertIn("X86_PTE_CACHE_DISABLE", text)
        self.assertIn("X86_PTE_NX", text)
        self.assertNotIn("map_all_mmio", text)

    def test_lapic_rejects_x2apic_and_masks_lvts(self):
        text = LAPIC.read_text(encoding="utf-8")
        self.assertIn("IA32_APIC_BASE_X2APIC", text)
        self.assertIn("if (apic_base & IA32_APIC_BASE_X2APIC) != 0 { return false; }", text)
        for reg in (
            "LAPIC_REG_LVT_TIMER", "LAPIC_REG_LVT_THERMAL", "LAPIC_REG_LVT_PERF",
            "LAPIC_REG_LVT_LINT0", "LAPIC_REG_LVT_LINT1", "LAPIC_REG_LVT_ERROR",
        ):
            self.assertIn(f"lapic_write({reg}, LAPIC_LVT_MASKED)", text)

    def test_ioapic_masks_all_redirection_entries(self):
        text = IOAPIC.read_text(encoding="utf-8")
        self.assertIn("ioapic_init_all_masked", text)
        self.assertIn("current_low | IOAPIC_REDIR_MASKED", text)
        self.assertIn("madt_ioapic_count()", text)

    def test_post_cutover_order_keeps_sti_disabled(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        cpu = body.index("post_cutover_activate_cpu")
        pmm = body.index("post_cutover_activate_pmm")
        vmm = body.index("post_cutover_activate_vmm")
        acpi = body.index("post_cutover_activate_acpi")
        apic = body.index("post_cutover_activate_interrupt_controllers")
        self.assertLess(cpu, pmm)
        self.assertLess(pmm, vmm)
        self.assertLess(vmm, acpi)
        self.assertLess(acpi, apic)
        code = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
        self.assertNotIn("__sti(", code)
        self.assertNotIn("x86_sti", code)


if __name__ == "__main__":
    unittest.main()

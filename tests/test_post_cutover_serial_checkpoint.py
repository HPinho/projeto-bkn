#!/usr/bin/env python3
"""Guardrails do checkpoint serial nativo do bring-up."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SERIAL = ROOT / "kernel/src/arch/x86_64/serial.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class PostCutoverSerialCheckpointTests(unittest.TestCase):
    def test_serial_is_native_bounded_and_best_effort(self):
        text = SERIAL.read_text(encoding="utf-8")
        self.assertIn("X86_SERIAL_COM1: u16 = 0x3F8", text)
        self.assertIn("X86_SERIAL_MAX_SPINS", text)
        self.assertIn("__outb", text)
        self.assertIn("__inb", text)
        self.assertNotIn("BootServices", text)
        self.assertNotIn("Stall", text)

    def test_markers_bound_each_post_cutover_phase_and_timer_remains_last(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_post_cutover_entry", 1)[1]
        serial = body.index("x86_serial_init()")
        cpu = body.index("post_cutover_activate_cpu(context)")
        pmm = body.index("post_cutover_activate_pmm(context)")
        vmm = body.index("post_cutover_activate_vmm(context)")
        acpi = body.index("post_cutover_activate_acpi(context)")
        apic = body.index("post_cutover_activate_interrupt_controllers()")
        irqs = body.index("post_cutover_prepare_irqs()")
        timer = body.index("post_cutover_prepare_timer()")
        marker = body.index("x86_serial_write_timer_ready_marker()")
        self.assertLess(serial, cpu)
        self.assertLess(cpu, pmm)
        self.assertLess(pmm, vmm)
        self.assertLess(vmm, acpi)
        self.assertLess(acpi, apic)
        self.assertLess(apic, irqs)
        self.assertLess(irqs, timer)
        self.assertLess(timer, marker)
        for stage in ("'B' as u8", "'C' as u8", "'P' as u8", "'V' as u8", "'A' as u8", "'I' as u8", "'R' as u8"):
            self.assertIn(f"x86_serial_write_stage_marker({stage})", body)

    def test_cpu_cutover_has_bounded_substage_checkpoints(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_activate_cpu", 1)[1].split(
            "pub fn post_cutover_cpu_tables_active", 1
        )[0]
        context = body.index("x86_serial_write_stage_marker('0' as u8)")
        cr3 = body.index("x86_mmu_activate_root(context.root_physical)")
        after_cr3 = body.index("x86_serial_write_stage_marker('1' as u8)")
        tables = body.index("x86_serial_write_stage_marker('2' as u8)")
        loaded = body.index("x86_serial_write_stage_marker('3' as u8)")
        self.assertLess(context, cr3)
        self.assertLess(cr3, after_cr3)
        self.assertLess(after_cr3, tables)
        self.assertLess(tables, loaded)

    def test_qemu_smoke_requires_actual_post_cutover_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("-no-reboot", text)
        self.assertIn("-serial file:build/qemu-serial.log", text)
        self.assertIn('grep -q "BAKEN:TIMER_READY" build/qemu-serial.log', text)
        self.assertIn('test "$status" -eq 124', text)


if __name__ == "__main__":
    unittest.main()

"""Guardrails da fase userspace/FPU do kernel."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class KernelUserspacePhaseTests(unittest.TestCase):
    def test_reschedule_gate_is_user_callable_but_other_irqs_remain_kernel_only(self):
        idt = (ROOT / "kernel/src/arch/x86_64/idt.sotlas").read_text(encoding="utf-8")
        irq = (ROOT / "kernel/src/interrupts/irq.sotlas").read_text(encoding="utf-8")
        self.assertIn("IDT_GATE_USER_INTERRUPT: u8 = 0xEE", idt)
        self.assertIn("idt_set_user_irq_gate", idt)
        self.assertIn("irq_install_user_gate(IRQ_VECTOR_RESCHEDULE)", irq)
        for vector in ("IRQ_VECTOR_TIMER", "IRQ_VECTOR_KEYBOARD", "IRQ_VECTOR_MOUSE"):
            self.assertIn(f"irq_install_gate({vector})", irq)

    def test_syscall_requires_cpl3_and_user_copy_validates_pte_permissions(self):
        irq = (ROOT / "kernel/src/interrupts/irq.sotlas").read_text(encoding="utf-8")
        copy = (ROOT / "kernel/src/process/user_copy.sotlas").read_text(encoding="utf-8")
        self.assertIn("x86_saved_frame_is_user(frame_address)", irq)
        self.assertIn("syscall_dispatch_frame(frame_address)", irq)
        self.assertIn("x86_pte_present(pte)", copy)
        self.assertIn("X86_PTE_USER", copy)
        self.assertIn("X86_PTE_WRITABLE", copy)
        self.assertIn("direct_map_virtual_address(physical_page)", copy)

    def test_loader_enforces_wx_guard_page_and_runtime_teardown(self):
        loader = (ROOT / "kernel/src/process/userspace_loader.sotlas").read_text(encoding="utf-8")
        self.assertIn("process_map_user_page(pid, USERSPACE_CODE_ADDRESS, code, false, true)", loader)
        self.assertIn("process_map_user_page(pid, USERSPACE_STACK_ADDRESS, stack, true, false)", loader)
        self.assertIn("process_user_pte(pid, USERSPACE_STACK_GUARD) != 0", loader)
        self.assertLess(loader.index("userspace_materialize_probe(code, data)"),
                        loader.index("process_map_user_page(pid, USERSPACE_CODE_ADDRESS"))
        self.assertIn("process_reference_count(USERSPACE_PID) == 0", loader)
        self.assertIn("process_destroy(USERSPACE_PID)", loader)

    def test_fpu_storage_aligns_each_fxsave_region_without_ignored_attribute(self):
        fpu = (ROOT / "kernel/src/arch/x86_64/fpu.sotlas").read_text(encoding="utf-8")
        irq = (ROOT / "kernel/src/interrupts/irq.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("@align(", fpu)
        self.assertIn("FPU_STATE_STORAGE_BYTES: usize = 527", fpu)
        self.assertIn("let address = (base + 15) & FPU_ALIGNMENT_MASK", fpu)
        self.assertIn("state_end > storage_end", fpu)
        self.assertIn("__fxsave(address)", fpu)
        self.assertIn("__fxrstor(address)", fpu)
        switch = irq.split("fn irq_schedule_with_fpu", 1)[1].split("@export", 1)[0]
        self.assertLess(switch.index("fpu_save_thread(old_tid)"), switch.index("scheduler_on_timer_interrupt"))
        self.assertLess(switch.index("scheduler_on_timer_interrupt"), switch.index("fpu_restore_thread(new_tid)"))

    def test_smoke_gate_requires_runtime_userspace_proof(self):
        from tools.scripts.verify_kernel_smoke import REQUIRED
        for marker in ("FPU_CONTEXT_READY", "RING3_ENTERED", "RING3_READY",
                       "SYSCALL_READY", "USER_COPY_READY", "USERSPACE_LOADER_READY",
                       "USER_FAULT_ISOLATED_READY"):
            self.assertIn(marker, REQUIRED)

    def test_madt_records_processor_lapic_entries(self):
        madt = (ROOT / "kernel/src/acpi/madt.sotlas").read_text(encoding="utf-8")
        self.assertIn("MADT_ENTRY_LOCAL_APIC: u8 = 0", madt)
        self.assertIn("MADT_CPU_COUNT", madt)
        self.assertIn("MADT_CPUS[idx].apic_id", madt)
        self.assertIn("pub fn madt_cpu_count()", madt)


if __name__ == "__main__":
    unittest.main()

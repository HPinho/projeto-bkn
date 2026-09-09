"""Guardrails do runtime per-CPU SMP e das transicoes de contexto BSP/AP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "kernel/src/arch/x86_64"
GDT = ARCH / "gdt.sotlas"
TSS = ARCH / "tss.sotlas"
CPU = ARCH / "cpu.sotlas"
FPU = ARCH / "fpu.sotlas"
SMP = ARCH / "smp.sotlas"
LAPIC = ROOT / "kernel/src/interrupts/lapic.sotlas"
LAPIC_TIMER = ROOT / "kernel/src/interrupts/lapic_timer.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
USERSPACE = ROOT / "kernel/src/process/userspace_loader.sotlas"
INTRINSICS = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpRuntimeTests(unittest.TestCase):
    def test_gdt_keeps_bsp_contract_and_adds_private_ap_storage(self):
        text = GDT.read_text(encoding="utf-8")
        for token in (
            "static mut GDT_ENTRIES: [u64; GDT_ENTRY_COUNT]",
            "static mut GDT_AP_ENTRIES: [u64; GDT_AP_ENTRY_COUNT]",
            "GDT_CPU_SLOT_COUNT: usize = 32",
            "pub fn gdt_prepare_for_cpu(cpu_slot: usize) -> bool",
            "pub fn gdt_set_tss_descriptor_for_cpu",
            "pub fn gdt_base_for_cpu(cpu_slot: usize)",
        ):
            self.assertIn(token, text)

    def test_tss_keeps_bsp_contract_and_gives_aps_private_tss_and_ists(self):
        text = TSS.read_text(encoding="utf-8")
        for token in (
            "static mut TSS: Tss64",
            "static mut KERNEL_RSP0_STACK",
            "static mut AP_TSS: [Tss64; TSS_CPU_SLOT_COUNT]",
            "static mut AP_DOUBLE_FAULT_STACKS",
            "static mut AP_NMI_STACKS",
            "static mut AP_MACHINE_CHECK_STACKS",
            "pub fn tss_prepare_for_cpu(cpu_slot: usize, kernel_rsp0: u64) -> bool",
            "pub fn tss_set_rsp0_for_cpu(cpu_slot: usize, kernel_rsp0: u64) -> bool",
            "pub fn tss_base_for_cpu(cpu_slot: usize) -> u64",
            "AP_TSS[cpu_slot].io_map_base = 104",
        ):
            self.assertIn(token, text)

    def test_ap_runtime_loads_private_tables_before_controlled_scheduler_release(self):
        text = SMP.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_smp_ap_runtime_entry", 1)[1].split("fn smp_start_one_ap", 1)[0]
        for token in (
            "x86_cli_raw()",
            "tss_prepare_for_cpu(cpu_slot, stack_top)",
            "gdt_prepare_for_cpu(cpu_slot)",
            "gdt_set_tss_descriptor_for_cpu",
            "x86_gdt_activate_segments_raw(",
            "x86_ltr_raw(GDT_TSS_SELECTOR)",
            "x86_lidt_table_raw(idt_address, idt_limit())",
            "SMP_AP_RUNTIME_READY",
            "while x86_mmio_read32(release) != 1",
            "x86_mmio_write32(active, 1)",
            "x86_sti_raw()",
        ):
            self.assertIn(token, text if token == "SMP_AP_RUNTIME_READY" else body)
        self.assertLess(body.index("x86_mmio_write32(runtime_ready, 1)"), body.index("while x86_mmio_read32(release) != 1"))
        self.assertLess(body.index("while x86_mmio_read32(release) != 1"), body.index("x86_sti_raw()"))
        self.assertNotIn("scheduler_initialize", body)
        self.assertNotIn("scheduler_on_timer_interrupt", body)
        self.assertNotIn("scheduler_create_", body)

    def test_ap_runtime_initializes_cpu_local_state_and_keeps_timer_masked(self):
        smp = SMP.read_text(encoding="utf-8")
        body = smp.split("pub fn sotlas_x86_smp_ap_runtime_entry", 1)[1].split("fn smp_start_one_ap", 1)[0]
        for token in (
            "fpu_enable_current_cpu()",
            "__pat_install_wc()",
            "lapic_prepare_current_cpu_masked()",
            "lapic_timer_prepare_current_cpu_masked()",
        ):
            self.assertIn(token, body)
        self.assertNotIn("lapic_timer_unmask_periodic()", body)
        self.assertIn("pub fn fpu_enable_current_cpu() -> bool", FPU.read_text(encoding="utf-8"))
        self.assertIn("pub fn lapic_prepare_current_cpu_masked() -> bool", LAPIC.read_text(encoding="utf-8"))
        timer = LAPIC_TIMER.read_text(encoding="utf-8")
        self.assertIn("pub fn lapic_timer_prepare_current_cpu_masked() -> bool", timer)
        self.assertIn("LAPIC_TIMER_MASKED | LAPIC_TIMER_PERIODIC", timer)

    def test_irq_switch_updates_cpu_local_user_rsp0_and_releases_terminated_fpu_slot(self):
        text = IRQ.read_text(encoding="utf-8")
        body = text.split("fn irq_schedule_with_fpu", 1)[1].split("@system\n@export", 1)[0]
        for token in (
            "scheduler_switch_lock()",
            "let cpu_slot = scheduler_current_cpu_slot();",
            "cpu_slot == SCHEDULER_INVALID_CPU_SLOT",
            "let old_terminated = scheduler_thread_is_terminated(old_tid);",
            "let selected = scheduler_on_timer_interrupt(frame_address);",
            "if x86_saved_frame_is_user(selected)",
            "selected + X86_KERNEL_THREAD_FRAME_BYTES",
            "tss_set_rsp0_for_cpu(cpu_slot, kernel_rsp0)",
            "fpu_restore_thread(new_tid)",
            "fpu_release_thread(old_tid)",
            "scheduler_switch_unlock()",
        ):
            self.assertIn(token, body)
        self.assertNotIn("if cpu_slot != 0", body)

    def test_userspace_bootstrap_uses_current_cpu_tss_before_iret(self):
        text = USERSPACE.read_text(encoding="utf-8")
        body = text.split("pub fn sotlas_x86_userspace_bootstrap_entry() -> !", 1)[1].split("@system", 1)[0]
        self.assertIn("let cpu_slot = scheduler_current_cpu_slot();", body)
        self.assertIn("cpu_slot == SCHEDULER_INVALID_CPU_SLOT", body)
        self.assertIn("tss_set_rsp0_for_cpu(cpu_slot, kernel_stack_top)", body)
        self.assertLess(body.index("tss_set_rsp0_for_cpu"), body.index("__enter_user"))
        self.assertNotIn("tss_set_rsp0(kernel_stack_top)", body)

    def test_backend_exposes_native_ap_runtime_and_smp_probe_addresses(self):
        cpu = CPU.read_text(encoding="utf-8")
        intrinsic = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn("pub fn x86_smp_ap_runtime_entry_address() -> u64", cpu)
        self.assertIn("return __smp_ap_runtime_entry_address();", cpu)
        self.assertIn("extern void sotlas_x86_smp_ap_runtime_entry(void);", intrinsic)
        self.assertIn("static inline uint64_t __smp_ap_runtime_entry_address", intrinsic)
        self.assertIn('"__smp_ap_runtime_entry_address": Function(', intrinsic)
        self.assertIn("pub fn x86_scheduler_smp_probe_entry_address() -> u64", cpu)
        self.assertIn("extern void sotlas_x86_scheduler_smp_probe_entry(void);", intrinsic)

    def test_smp_workflow_requires_runtime_ready_marker(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_runtime.py", workflow)
        self.assertIn("BAKEN:SMP_AP_RUNTIME_READY", workflow)
        self.assertIn("require_marker()", workflow)
        self.assertIn("require_marker 'BAKEN:SMP_AP_RUNTIME_READY'", workflow)


if __name__ == "__main__":
    unittest.main()

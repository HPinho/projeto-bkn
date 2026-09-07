"""Guardrails do runtime per-CPU SMP e das transicoes de contexto BSP."""
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
            "pub fn tss_base_for_cpu(cpu_slot: usize) -> u64",
            "AP_TSS[cpu_slot].io_map_base = 104",
        ):
            self.assertIn(token, text)

    def test_ap_runtime_loads_private_gdt_tss_shared_idt_and_keeps_if_clear(self):
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
            "if x86_interrupts_enabled()",
            "SMP_AP_RUNTIME_READY",
        ):
            self.assertIn(token, text if token == "SMP_AP_RUNTIME_READY" else body)
        self.assertNotIn("x86_sti_raw()", body)
        self.assertNotIn("scheduler_", body)

    def test_ap_runtime_initializes_cpu_local_fpu_pat_lapic_and_masked_timer(self):
        smp = SMP.read_text(encoding="utf-8")
        body = smp.split("pub fn sotlas_x86_smp_ap_runtime_entry", 1)[1].split("fn smp_start_one_ap", 1)[0]
        for token in (
            "fpu_enable_current_cpu()",
            "__pat_install_wc()",
            "lapic_prepare_current_cpu_masked()",
            "lapic_timer_prepare_current_cpu_masked()",
        ):
            self.assertIn(token, body)
        self.assertIn("pub fn fpu_enable_current_cpu() -> bool", FPU.read_text(encoding="utf-8"))
        self.assertIn("pub fn lapic_prepare_current_cpu_masked() -> bool", LAPIC.read_text(encoding="utf-8"))
        timer = LAPIC_TIMER.read_text(encoding="utf-8")
        self.assertIn("pub fn lapic_timer_prepare_current_cpu_masked() -> bool", timer)
        self.assertIn("LAPIC_TIMER_MASKED | LAPIC_TIMER_PERIODIC", timer)

    def test_irq_switch_updates_user_rsp0_and_releases_terminated_fpu_slot(self):
        text = IRQ.read_text(encoding="utf-8")
        body = text.split("fn irq_schedule_context", 1)[1].split("@system\n@export", 1)[0]
        for token in (
            "let old_terminated = scheduler_thread_is_terminated(old_tid);",
            "let selected = scheduler_on_timer_interrupt(frame_address);",
            "if x86_saved_frame_is_user(selected)",
            "selected + X86_KERNEL_THREAD_FRAME_BYTES",
            "tss_set_rsp0(kernel_rsp0)",
            "fpu_restore_thread(new_tid)",
            "fpu_release_thread(old_tid)",
        ):
            self.assertIn(token, body)

    def test_backend_exposes_native_ap_runtime_entry_address(self):
        cpu = CPU.read_text(encoding="utf-8")
        intrinsic = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn("pub fn x86_smp_ap_runtime_entry_address() -> u64", cpu)
        self.assertIn("return __smp_ap_runtime_entry_address();", cpu)
        self.assertIn("extern void sotlas_x86_smp_ap_runtime_entry(void);", intrinsic)
        self.assertIn("static inline uint64_t __smp_ap_runtime_entry_address", intrinsic)
        self.assertIn('"__smp_ap_runtime_entry_address": Function(', intrinsic)

    def test_smp_workflow_requires_runtime_ready_marker(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_runtime.py", workflow)
        self.assertIn("BAKEN:SMP_AP_RUNTIME_READY", workflow)
        self.assertIn("grep -Fq 'BAKEN:SMP_AP_RUNTIME_READY'", workflow)


if __name__ == "__main__":
    unittest.main()

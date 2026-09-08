"""Guardrails da preempcao periodica real em Application Processor."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "kernel/src/scheduler/smp_probe.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
SMP = ROOT / "kernel/src/arch/x86_64/smp.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpTimerPreemptionTests(unittest.TestCase):
    def test_ap_timer_is_enabled_only_from_a_pinned_ap_thread(self):
        text = PROBE.read_text(encoding="utf-8")
        self.assertIn("import kernel::interrupts::lapic_timer::*;", text)
        self.assertIn("SCHEDULER_SMP_PROBE_MODE_TIMER: u32 = 2", text)
        entry = text.split("pub fn sotlas_x86_scheduler_smp_probe_entry", 1)[1]
        entry = entry.split("fn scheduler_smp_probe_wait_executed", 1)[0]
        self.assertIn("if mode == SCHEDULER_SMP_PROBE_MODE_TIMER", entry)
        self.assertIn("lapic_timer_unmask_periodic()", entry)
        self.assertIn("scheduler_thread_owner_cpu(thread_id) != cpu_slot as u32", entry)

        # Bring-up continua fail-closed: INIT/SIPI nao pode desmascarar timer.
        smp = SMP.read_text(encoding="utf-8")
        ap_runtime = smp.split("pub fn sotlas_x86_smp_ap_runtime_entry", 1)[1]
        ap_runtime = ap_runtime.split("fn smp_start_one_ap", 1)[0]
        self.assertNotIn("lapic_timer_unmask_periodic()", ap_runtime)

    def test_timer_proof_runs_after_ipi_dispatch_and_needs_no_cleanup_ipi(self):
        text = PROBE.read_text(encoding="utf-8")
        run = text.split("pub fn scheduler_smp_probe_run() -> bool", 1)[1]
        thread_marker = run.index("scheduler_smp_probe_emit_thread_marker()")
        timer_mode = run.index("SCHEDULER_SMP_PROBE_MODE_TIMER", thread_marker)
        timer_create = run.index("scheduler_create_kernel_thread_on_cpu(", timer_mode)
        timer_ipi = run.index("lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)", timer_create)
        timer_enabled = run.index("scheduler_smp_probe_wait_timer_enabled()", timer_ipi)
        timer_tick = run.index("scheduler_smp_probe_wait_timer_tick", timer_enabled)
        timer_idle = run.index("scheduler_smp_probe_wait_idle(", timer_tick)
        timer_marker = run.index("scheduler_smp_probe_emit_timer_marker()", timer_idle)
        self.assertLess(thread_marker, timer_mode)
        self.assertLess(timer_mode, timer_create)
        self.assertLess(timer_create, timer_ipi)
        self.assertLess(timer_ipi, timer_enabled)
        self.assertLess(timer_enabled, timer_tick)
        self.assertLess(timer_tick, timer_idle)
        self.assertLess(timer_idle, timer_marker)
        after_timer_ipi = run[timer_ipi + len("lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)"):timer_marker]
        self.assertNotIn("lapic_send_fixed(", after_timer_ipi)

    def test_ap_timer_count_is_per_cpu_and_sleep_clock_remains_bsp_only(self):
        irq = IRQ.read_text(encoding="utf-8")
        self.assertIn("static mut IRQ_CPU_TIMER_COUNT", irq)
        self.assertIn("pub fn irq_timer_count_for_cpu(cpu_slot: usize) -> u64", irq)
        timer = irq.split("if vector == IRQ_VECTOR_TIMER as u64", 1)[1]
        timer = timer.split("if vector == IRQ_VECTOR_KEYBOARD", 1)[0]
        self.assertIn("let bsp_clock = cpu_slot == 0", timer)
        self.assertIn("IRQ_CPU_TIMER_COUNT[cpu_slot] += 1", timer)
        self.assertIn("if bsp_clock", timer)
        self.assertIn("scheduler_sleep_on_timer_tick(timer_count)", timer)
        self.assertLess(timer.index("if bsp_clock"), timer.index("scheduler_sleep_on_timer_tick(timer_count)"))

    def test_qemu_gate_requires_real_ap_timer_interrupt(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_timer_preemption.py", workflow)
        self.assertIn("BAKEN:SMP_THREAD_ON_AP", workflow)
        self.assertIn("BAKEN:SMP_TIMER_ON_AP", workflow)
        self.assertIn("grep -Fq 'BAKEN:SMP_TIMER_ON_AP'", workflow)


if __name__ == "__main__":
    unittest.main()

"""Guardrails do primeiro dispatch real de thread em AP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPIN = ROOT / "kernel/src/sync/spinlock.sotlas"
CPU = ROOT / "kernel/src/arch/x86_64/cpu.sotlas"
SMP = ROOT / "kernel/src/arch/x86_64/smp.sotlas"
CORE = ROOT / "kernel/src/scheduler/core.sotlas"
PROBE = ROOT / "kernel/src/scheduler/smp_probe.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
LAPIC = ROOT / "kernel/src/interrupts/lapic.sotlas"
INTRINSICS = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpSchedulerDispatchTests(unittest.TestCase):
    def test_spinlock_is_backed_by_real_x86_atomic_exchange(self):
        spin = SPIN.read_text(encoding="utf-8")
        cpu = CPU.read_text(encoding="utf-8")
        backend = INTRINSICS.read_text(encoding="utf-8")
        for token in (
            "pub struct SpinLock",
            "x86_atomic_exchange_u32(address, SPINLOCK_LOCKED)",
            "x86_cpu_pause()",
            "x86_atomic_exchange_u32(address, SPINLOCK_UNLOCKED)",
        ):
            self.assertIn(token, spin)
        self.assertIn("pub fn x86_atomic_exchange_u32", cpu)
        self.assertIn("static inline uint32_t __atomic_exchange_u32", backend)
        self.assertIn('"xchgl %0,(%1)"', backend)
        self.assertIn('"__atomic_exchange_u32": Function(', backend)

    def test_hardware_ipi_uses_dedicated_vector_and_eoi(self):
        irq = IRQ.read_text(encoding="utf-8")
        backend = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn("IRQ_VECTOR_RESCHEDULE_IPI: u16 = 0x44", irq)
        self.assertIn("irq_install_gate(IRQ_VECTOR_RESCHEDULE_IPI)", irq)
        self.assertIn("SOTLAS_X86_IRQ_STUB(68)", backend)
        self.assertIn("case 68: return", backend)
        ipi = irq.split("if vector == IRQ_VECTOR_RESCHEDULE_IPI as u64", 1)[1].split("if vector == IRQ_VECTOR_TIMER", 1)[0]
        self.assertIn("lapic_eoi();", ipi)
        self.assertIn("irq_schedule_with_fpu(frame_address)", ipi)
        software = irq.split("if vector == IRQ_VECTOR_RESCHEDULE as u64", 1)[1].split("if vector == IRQ_VECTOR_RESCHEDULE_IPI", 1)[0]
        self.assertNotIn("lapic_eoi();", software)

    def test_lapic_can_send_fixed_delivery_ipi(self):
        text = LAPIC.read_text(encoding="utf-8")
        self.assertIn("pub fn lapic_send_fixed(destination_apic_id: u8, vector: u8) -> bool", text)
        self.assertIn("return lapic_send_icr(destination_apic_id, vector as u32);", text)
        self.assertIn("LAPIC_FIXED_VECTOR_MIN: u8 = 0x20", text)
        self.assertIn("LAPIC_FIXED_VECTOR_MAX: u8 = 0xFE", text)

    def test_scheduler_has_per_cpu_current_idle_and_thread_ownership(self):
        text = CORE.read_text(encoding="utf-8")
        for token in (
            "static mut SCHEDULER_LOCK: SpinLock",
            "static mut SCHEDULER_CPU_CURRENT_SLOT",
            "static mut SCHEDULER_CPU_IDLE_FRAME",
            "static mut SCHEDULER_CPU_IDLE_EPOCH",
            "static mut SCHEDULER_THREAD_OWNER_CPU",
            "static mut SCHEDULER_THREAD_AFFINITY_CPU",
            "pub fn scheduler_current_cpu_slot() -> usize",
            "fn scheduler_on_secondary_interrupt",
            "fn scheduler_select_slot_for_cpu",
        ):
            self.assertIn(token, text)
        self.assertIn("SCHEDULER_THREAD_OWNER_CPU[slot] == SCHEDULER_CPU_NONE", text)

    def test_reaper_never_frees_a_stack_still_owned_by_an_ap(self):
        text = CORE.read_text(encoding="utf-8")
        reaper = text.split("fn scheduler_reap_terminated_noncurrent", 1)[1].split("pub fn scheduler_initialize", 1)[0]
        self.assertIn("let current = SCHEDULER_CURRENT_SLOT", reaper)
        self.assertIn("SCHEDULER_THREAD_OWNER_CPU[slot] == SCHEDULER_CPU_NONE", reaper)
        self.assertLess(reaper.index("SCHEDULER_THREAD_OWNER_CPU[slot] == SCHEDULER_CPU_NONE"),
                        reaper.index("pmm_free_pages_lifo(stack_base, stack_pages)"))

    def test_ap_release_keeps_periodic_timer_masked(self):
        smp = SMP.read_text(encoding="utf-8")
        body = smp.split("pub fn sotlas_x86_smp_ap_runtime_entry", 1)[1].split("fn smp_start_one_ap", 1)[0]
        self.assertIn("SMP_AP_SCHEDULER_RELEASE", smp)
        self.assertIn("SMP_AP_SCHEDULER_ACTIVE", smp)
        self.assertIn("while x86_mmio_read32(release) != 1", body)
        self.assertIn("x86_sti_raw()", body)
        self.assertNotIn("lapic_timer_unmask_periodic()", body)
        self.assertIn("pub fn smp_release_aps_for_scheduler() -> bool", smp)

    def test_probe_pins_thread_before_releasing_aps_and_uses_two_ipis(self):
        text = PROBE.read_text(encoding="utf-8")
        create = text.index("scheduler_create_kernel_thread_on_cpu(")
        release = text.index("smp_release_aps_for_scheduler()")
        first_ipi = text.index("lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)")
        second_ipi = text.index("lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)", first_ipi + 1)
        idle = text.index("scheduler_smp_probe_wait_idle", second_ipi)
        self.assertLess(create, release)
        self.assertLess(release, first_ipi)
        self.assertLess(first_ipi, second_ipi)
        self.assertLess(second_ipi, idle)
        self.assertIn("scheduler_thread_owner_cpu(thread_id) == cpu_slot as u32", text)
        self.assertIn("BAKEN", "BAKEN")
        marker_bytes = "66,65,75,69,78,58,83,77,80,95,84,72,82,69,65,68,95,79,78,95,65,80,10"
        self.assertIn(marker_bytes, text.replace(" ", ""))

    def test_runtime_runs_ap_dispatch_only_after_bsp_and_userspace_proofs(self):
        text = RUNTIME.read_text(encoding="utf-8")
        body = text.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertIn("scheduler_smp_probe_run()", body)
        self.assertLess(body.index("userspace_loader_emit_ready_markers()"), body.index("scheduler_smp_probe_run()"))

    def test_qemu_gate_requires_actual_thread_execution_on_ap(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_scheduler_dispatch.py", workflow)
        self.assertIn("BAKEN:SMP_THREAD_ON_AP", workflow)
        self.assertIn("grep -Fq 'BAKEN:SMP_THREAD_ON_AP'", workflow)


if __name__ == "__main__":
    unittest.main()

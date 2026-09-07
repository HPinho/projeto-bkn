import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YIELD = ROOT / "kernel/src/scheduler/yield.sotlas"
CPU = ROOT / "kernel/src/arch/x86_64/cpu.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
DIAG = ROOT / "kernel/src/scheduler/diagnostics.sotlas"
INTRINSICS = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
NVME_WORKFLOW = ROOT / ".github/workflows/baken_nvme_only.yml"


class KernelSchedulerYieldTests(unittest.TestCase):
    def test_yield_is_real_x86_software_interrupt(self):
        cpu = CPU.read_text(encoding="utf-8")
        intrinsics = INTRINSICS.read_text(encoding="utf-8")
        api = YIELD.read_text(encoding="utf-8")

        self.assertIn("pub fn scheduler_yield() -> bool", api)
        self.assertIn("x86_scheduler_yield_interrupt();", api)
        self.assertIn("pub fn x86_scheduler_yield_interrupt() -> void", cpu)
        self.assertIn("__scheduler_yield_interrupt();", cpu)
        self.assertIn("static inline void __scheduler_yield_interrupt(void)", intrinsics)
        self.assertIn('"int $0x43"', intrinsics)
        self.assertIn('"__scheduler_yield_interrupt": Function(', intrinsics)

    def test_reschedule_vector_has_own_idt_gate_and_backend_stub(self):
        irq = IRQ.read_text(encoding="utf-8")
        intrinsics = INTRINSICS.read_text(encoding="utf-8")

        self.assertIn("IRQ_VECTOR_RESCHEDULE: u16 = 0x43", irq)
        self.assertIn("irq_install_gate(IRQ_VECTOR_RESCHEDULE)", irq)
        self.assertIn("SOTLAS_X86_IRQ_STUB(67)", intrinsics)
        self.assertIn("case 67: return (uint64_t)(uintptr_t)&__sotlas_x86_irq_67;", intrinsics)

    def test_software_reschedule_never_sends_lapic_eoi(self):
        irq = IRQ.read_text(encoding="utf-8")
        reschedule = irq.split("if vector == IRQ_VECTOR_RESCHEDULE as u64", 1)[1]
        reschedule = reschedule.split("if vector == IRQ_VECTOR_TIMER as u64", 1)[0]
        self.assertIn("return scheduler_on_timer_interrupt(frame_address);", reschedule)
        self.assertNotIn("lapic_eoi();", reschedule)

    def test_runtime_forces_probe_via_yield_before_waiting_for_timer_policy(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        create = body.index("scheduler_start_run_queue_probe()")
        yield_call = body.index("scheduler_yield()")
        yield_marker = body.index("scheduler_diag_yield_round_trip()")
        wait = body.index("scheduler_wait_run_queue_probe()")
        self.assertLess(create, yield_call)
        self.assertLess(yield_call, yield_marker)
        self.assertLess(yield_marker, wait)

    def test_qemu_gate_requires_yield_round_trip_marker(self):
        diag = DIAG.read_text(encoding="utf-8")
        workflow = NVME_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pub fn scheduler_diag_yield_round_trip() -> void", diag)
        self.assertIn("BAKEN:YIELD_ROUND_TRIP", workflow)
        self.assertIn('grep -Fq "$marker"', workflow)
        self.assertIn('require_serial_marker "$marker"', workflow)


if __name__ == "__main__":
    unittest.main()

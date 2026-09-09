"""Prova real de concorrência do heap global entre BSP e AP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "kernel/src/scheduler/smp_probe.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpHeapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = PROBE.read_text(encoding="utf-8")

    def test_probe_uses_current_public_heap_and_pinned_scheduler_apis(self):
        text = self.probe
        self.assertIn("import kernel::memory::kernel_heap::*;", text)
        self.assertIn("SCHEDULER_SMP_PROBE_MODE_HEAP: u32 = 5", text)
        self.assertIn("scheduler_create_kernel_thread_on_cpu(", text)
        self.assertIn("kernel_heap_alloc(", text)
        self.assertIn("kernel_heap_free(", text)

    def test_ap_heap_path_never_reaches_allocator_internals(self):
        text = self.probe
        body = text.split("if mode == SCHEDULER_SMP_PROBE_MODE_HEAP", 1)[1].split(
            "if mode == SCHEDULER_SMP_PROBE_MODE_TLB", 1
        )[0]
        for required in (
            "kernel_heap_alloc(96)",
            "scheduler_smp_heap_stress(SCHEDULER_SMP_HEAP_AP_PATTERN)",
            "kernel_heap_free(held)",
            "x86_mmio_write32(done_address, 1)",
        ):
            self.assertIn(required, body)
        for forbidden in (
            "KERNEL_HEAP_LOCK",
            "spinlock_",
            "pmm_alloc",
            "pmm_free",
            "kernel_heap_alloc_locked",
            "kernel_heap_free_locked",
        ):
            self.assertNotIn(forbidden, body)

    def test_stress_keeps_two_live_blocks_and_checks_contents_before_free(self):
        body = self.probe.split("fn scheduler_smp_heap_stress", 1)[1].split(
            "pub fn sotlas_x86_scheduler_smp_probe_entry", 1
        )[0]
        self.assertIn("let first = kernel_heap_alloc(64)", body)
        self.assertIn("let second = kernel_heap_alloc(128)", body)
        self.assertIn("if (first as u64) == (second as u64)", body)
        self.assertIn("*first_word = first_value", body)
        self.assertIn("*second_word = second_value", body)
        self.assertIn("*first_word != first_value", body)
        self.assertIn("*second_word != second_value", body)
        self.assertIn("while iteration < SCHEDULER_SMP_HEAP_ITERATIONS", body)

    def test_bsp_and_ap_overlap_then_restore_heap_accounting(self):
        body = self.probe.split("fn scheduler_smp_probe_run_heap", 1)[1].split(
            "fn scheduler_smp_probe_run_tlb", 1
        )[0]
        for token in (
            "let before_bytes = kernel_heap_allocated_bytes()",
            "let before_count = kernel_heap_allocation_count()",
            "scheduler_create_kernel_thread_on_cpu(",
            "lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)",
            "scheduler_smp_probe_wait_flag(ready_address)",
            "let held = kernel_heap_alloc(160)",
            "x86_mmio_write32(go_address, 1)",
            "scheduler_smp_heap_stress(SCHEDULER_SMP_HEAP_BSP_PATTERN)",
            "scheduler_smp_probe_wait_flag(done_address)",
            "kernel_heap_allocated_bytes() != before_bytes",
            "kernel_heap_allocation_count() != before_count",
            "scheduler_smp_probe_emit_heap_marker()",
        ):
            self.assertIn(token, body)

        ready = body.index("scheduler_smp_probe_wait_flag(ready_address)")
        stress = body.index("scheduler_smp_heap_stress(SCHEDULER_SMP_HEAP_BSP_PATTERN)")
        success_go = body.rfind("x86_mmio_write32(go_address, 1)", ready, stress)
        success_done = body.find("scheduler_smp_probe_wait_flag(done_address)", stress)
        self.assertNotEqual(success_go, -1)
        self.assertNotEqual(success_done, -1)
        self.assertLess(ready, success_go)
        self.assertLess(success_go, stress)
        self.assertLess(stress, success_done)

    def test_heap_proof_runs_before_tlb_and_ring3_without_replacing_them(self):
        run = self.probe.split("pub fn scheduler_smp_probe_run() -> bool", 1)[1]
        heap = run.index("scheduler_smp_probe_run_heap(apic_id, entry)")
        tlb = run.index("scheduler_smp_probe_run_tlb(apic_id)")
        ring3 = run.index("scheduler_smp_probe_run_ring3(apic_id)")
        self.assertLess(heap, tlb)
        self.assertLess(tlb, ring3)

    def test_smp_workflow_requires_heap_contract_and_runtime_marker(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_heap.py", workflow)
        self.assertIn("BAKEN:SMP_HEAP_READY", workflow)
        self.assertIn("grep -Fxq 'BAKEN:SMP_HEAP_READY'", workflow)


if __name__ == "__main__":
    unittest.main()

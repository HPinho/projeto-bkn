import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAIT = ROOT / "kernel/src/scheduler/wait_queue.sotlas"
PROBE = ROOT / "kernel/src/scheduler/wait_queue_probe.sotlas"
CPU = ROOT / "kernel/src/arch/x86_64/cpu.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
INTRINSICS = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
NVME_WORKFLOW = ROOT / ".github/workflows/baken_nvme_only.yml"


class KernelSchedulerWaitQueueTests(unittest.TestCase):
    def test_wait_queue_is_bounded_fifo_with_explicit_count(self):
        text = WAIT.read_text(encoding="utf-8")
        self.assertIn("KERNEL_WAIT_QUEUE_CAPACITY: usize = 8", text)
        self.assertIn("pub thread_ids: [u64; KERNEL_WAIT_QUEUE_CAPACITY]", text)
        self.assertIn("pub head: usize", text)
        self.assertIn("pub tail: usize", text)
        self.assertIn("pub count: usize", text)
        self.assertIn("wait_queue_push_locked", text)
        self.assertIn("wait_queue_pop_locked", text)

    def test_sleep_rejects_disabled_interrupt_callers(self):
        text = WAIT.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_wait_queue_sleep", 1)[1]
        self.assertIn("if !x86_interrupts_enabled() { return false; }", body)
        self.assertIn("let flags = x86_irq_save_disable();", body)

    def test_enqueue_and_block_happen_before_atomic_handoff(self):
        text = WAIT.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_wait_queue_sleep", 1)[1]
        body = body.split("pub fn scheduler_wait_queue_wake_one", 1)[0]
        push = body.index("wait_queue_push_locked(queue, thread_id)")
        block = body.index("scheduler_block_current()")
        handoff = body.index("x86_scheduler_block_switch()")
        self.assertLess(push, block)
        self.assertLess(block, handoff)

    def test_backend_closes_lost_wakeup_window_with_sti_interrupt_shadow(self):
        cpu = CPU.read_text(encoding="utf-8")
        backend = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn("pub fn x86_scheduler_block_switch() -> void", cpu)
        self.assertIn("static inline void __scheduler_block_switch(void)", backend)
        self.assertIn('"sti\\n\\tint $0x43"', backend)
        self.assertNotIn('"sti" : : : "memory");\n    __asm__ __volatile__("int $0x43"', backend)

    def test_irq_state_is_saved_and_restored_without_full_rflags_pop(self):
        backend = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn("static inline uint64_t __irq_save_disable(void)", backend)
        self.assertIn("static inline void __irq_restore(uint64_t flags)", backend)
        restore = backend.split("static inline void __irq_restore", 1)[1]
        restore = restore.split("static inline void __scheduler_block_switch", 1)[0]
        self.assertRegex(restore, r"1ull\s*<<\s*9")
        self.assertNotIn("popfq", restore)

    def test_wake_paths_run_with_interrupts_masked_and_preserve_previous_if(self):
        text = WAIT.read_text(encoding="utf-8")
        wake_one = text.split("pub fn scheduler_wait_queue_wake_one", 1)[1]
        wake_one = wake_one.split("pub fn scheduler_wait_queue_wake_all", 1)[0]
        self.assertIn("let flags = x86_irq_save_disable();", wake_one)
        self.assertIn("scheduler_wake_thread(thread_id)", wake_one)
        self.assertIn("x86_irq_restore(flags);", wake_one)

    def test_dynamic_probe_blocks_wakes_resumes_and_reaps(self):
        probe = PROBE.read_text(encoding="utf-8")
        runtime = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("sotlas_x86_scheduler_wait_probe_entry", probe)
        self.assertIn("scheduler_wait_queue_sleep(&mut WAIT_PROBE_QUEUE)", probe)
        self.assertIn("scheduler_wait_probe_wake", probe)
        self.assertIn("WAIT_PROBE_RESUMED", probe)
        self.assertIn("scheduler_reap_count() >= WAIT_PROBE_REAP_BASE + 1", probe)

        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        start = body.index("scheduler_wait_probe_start()")
        first_yield = body.index("scheduler_yield()", start)
        blocked = body.index("scheduler_wait_probe_blocked()", first_yield)
        wake = body.index("scheduler_wait_probe_wake()", blocked)
        second_yield = body.index("scheduler_yield()", wake)
        resumed = body.index("scheduler_wait_probe_resumed()", second_yield)
        complete = body.index("scheduler_wait_probe_wait_complete()", resumed)
        self.assertLess(start, first_yield)
        self.assertLess(first_yield, blocked)
        self.assertLess(blocked, wake)
        self.assertLess(wake, second_yield)
        self.assertLess(second_yield, resumed)
        self.assertLess(resumed, complete)

    def test_completion_wait_drives_scheduler_progress_instead_of_host_speed(self):
        probe = PROBE.read_text(encoding="utf-8")
        self.assertIn("import kernel::scheduler::yield::*;", probe)
        body = probe.split("pub fn scheduler_wait_probe_wait_complete() -> bool", 1)[1]
        self.assertIn("scheduler_reap_count() >= WAIT_PROBE_REAP_BASE + 1", body)
        self.assertIn("if !scheduler_yield() { return false; }", body)
        self.assertNotIn("x86_cpu_pause()", body)
        self.assertLess(body.index("scheduler_reap_count() >= WAIT_PROBE_REAP_BASE + 1"),
                        body.index("scheduler_yield()"))

    def test_nvme_qemu_gate_requires_wait_queue_proof_markers(self):
        workflow = NVME_WORKFLOW.read_text(encoding="utf-8")
        for marker in ("BAKEN:WAIT_BLOCKED", "BAKEN:WAIT_WAKE", "BAKEN:WAIT_RESUME"):
            self.assertIn(marker, workflow)
        self.assertIn('grep -Fq "$marker"', workflow)
        self.assertIn('require_serial_marker "$marker"', workflow)


if __name__ == "__main__":
    unittest.main()

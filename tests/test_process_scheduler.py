"""Contracts for the CPL0 process-root probe; QEMU supplies runtime evidence."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProcessSchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (ROOT / "kernel/src/scheduler/core.sotlas").read_text(encoding="utf-8")

    def test_retain_precedes_ready_publication_and_pid_binding_is_irq_off(self):
        body = self.code.split("pub fn scheduler_create_process_thread", 1)[1].split(
            "pub fn scheduler_block_current", 1)[0]
        self.assertLess(body.index("x86_irq_save_disable()"), body.index("process_retain(pid)"))
        self.assertLess(body.index("process_retain(pid)"), body.index("scheduler_create_kernel_thread("))
        self.assertIn("SCHEDULER_THREADS[slot].process_id = pid", body)
        self.assertIn("SCHEDULER_THREADS[slot].address_space_root = root", body)

        # Every failure after process_retain() must drop the acquired reference
        # before restoring IRQ state and returning.  Do not pin this invariant to
        # an exact occurrence count: adding a new rollback point must stay safe.
        normalized = " ".join(body.split())
        for rollback in (
            "if root == 0 { process_release(pid); x86_irq_restore(flags); return 0; }",
            "if tid == 0 { process_release(pid); x86_irq_restore(flags); return 0; }",
            "if !scheduler_switch_lock() { process_release(pid); x86_irq_restore(flags); return 0; }",
        ):
            with self.subTest(rollback=rollback):
                self.assertIn(rollback, normalized)

    def test_root_switch_precedes_current_slot_publication(self):
        body = self.code.split("fn scheduler_select_slot", 1)[1].split(
            "fn scheduler_return_unpublished_stack", 1)[0]
        self.assertIn("process_id == 0", body)
        self.assertIn("root = SCHEDULER_KERNEL_ROOT", body)
        self.assertLess(body.index("x86_write_cr3_raw(root)"), body.index("SCHEDULER_CURRENT_SLOT = slot"))

    def test_reaper_releases_reference_after_stack_and_before_slot_reset(self):
        body = self.code.split("fn scheduler_reap_terminated_noncurrent", 1)[1].split(
            "pub fn scheduler_initialize", 1)[0]
        self.assertIn("slot != current", body)
        self.assertLess(body.index("pmm_free_pages_lifo"), body.index("process_release(pid)"))
        self.assertLess(body.index("process_release(pid)"), body.index("kernel_thread_empty(0)"))

    def test_probe_observes_real_cr3_and_requires_reap_before_destroy(self):
        entry = self.code.split("pub fn sotlas_x86_scheduler_exit_probe_entry", 1)[1].split(
            "fn scheduler_reset_thread_slots", 1)[0]
        self.assertIn("x86_read_cr3_raw()", entry)
        self.assertIn("root != SCHEDULER_KERNEL_ROOT", entry)
        finish = self.code.split("pub fn scheduler_finish_process_probe", 1)[1].split(
            "pub fn scheduler_wait_reaper_probe", 1)[0]
        for token in ("SCHEDULER_PROCESS_PROBE_EXECUTED", "SCHEDULER_RUN_QUEUE_PROBE_REAPED",
                      "process_destroy(SCHEDULER_PROCESS_PROBE_PID)", "if !passed { return false; }"):
            self.assertIn(token, finish)
        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("PROCESS_SCHEDULER_READY", REQUIRED)

    def test_tid_exhaustion_does_not_wrap(self):
        self.assertIn("SCHEDULER_NEXT_THREAD_ID == 0xFFFFFFFFFFFFFFFF", self.code)

    def test_root_borrow_requires_live_reference(self):
        registry = (ROOT / "kernel/src/process/registry.sotlas").read_text(encoding="utf-8")
        body = registry.split("pub fn process_borrow_root", 1)[1].split("pub fn process_release", 1)[0]
        self.assertIn("PROCESS_REFERENCES[slot] != 0", body)

    def test_creation_inherits_canonical_kernel_root(self):
        source = (ROOT / "kernel/src/process/address_space.sotlas").read_text(encoding="utf-8")
        self.assertIn("source_root = process_address_space_page(PROCESS_KERNEL_ROOT_PHYSICAL)", source)
        self.assertIn("if PROCESS_ADDRESS_SPACE_READY { return true; }", source)

    def test_local_qemu_uses_full_gate_and_read_fixture(self):
        source = (ROOT / "tools/scripts/run_foundation_qemu.py").read_text(encoding="utf-8")
        self.assertIn("if not validate(text) and all(marker in text for marker in args.required_marker):", source)
        self.assertIn("if 'BAKEN:HEX=E:' in text:", source)
        self.assertIn("image.seek(1023 * 512)", source)
        self.assertNotIn("if 'BAKEN:BARE_METAL_READY' in text:", source)
        self.assertIn("'-smp', str(args.smp)", source)
        self.assertIn("all(marker in text for marker in args.required_marker)", source)

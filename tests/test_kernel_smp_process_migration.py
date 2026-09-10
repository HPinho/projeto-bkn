"""Guardrails da migração real de uma process thread Ring3 e do estado FPU/SSE BSP -> AP."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "kernel/src/scheduler/core.sotlas"
LOADER = ROOT / "kernel/src/process/userspace_loader.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_smp.yml"


class KernelSmpProcessMigrationTests(unittest.TestCase):
    def test_process_creation_is_pinned_before_ready_can_escape_to_an_ap(self):
        text = CORE.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_create_process_thread(pid", 1)[1].split(
            "pub fn scheduler_create_process_thread_on_cpu", 1
        )[0]
        self.assertIn(
            "scheduler_create_kernel_thread_with_affinity(entry_rip, stack_pages, 0)", body
        )
        self.assertNotIn("scheduler_create_kernel_thread(entry_rip, stack_pages)", body)
        self.assertLess(body.index("x86_irq_save_disable()"),
                        body.index("scheduler_create_kernel_thread_with_affinity"))
        self.assertLess(body.index("scheduler_create_kernel_thread_with_affinity"),
                        body.index("SCHEDULER_THREADS[slot].process_id = pid"))
        self.assertLess(body.index("SCHEDULER_THREADS[slot].address_space_root = root"),
                        body.rindex("x86_irq_restore(flags)"))

    def test_repin_accepts_ready_thread_without_releasing_retirement_owner(self):
        text = CORE.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_set_thread_affinity", 1)[1].split(
            "pub fn scheduler_block_current", 1
        )[0]
        for token in (
            "x86_irq_save_disable()",
            "scheduler_switch_lock()",
            "scheduler_find_thread_slot(thread_id)",
            "KERNEL_THREAD_READY",
            "saved_frame == 0",
            "SCHEDULER_THREAD_AFFINITY_CPU[slot] = cpu_slot as u32",
            "scheduler_switch_unlock()",
            "x86_irq_restore(flags)",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("scheduler_switch_lock()"),
                        body.index("SCHEDULER_THREAD_AFFINITY_CPU[slot] = cpu_slot as u32"))
        self.assertLess(body.index("SCHEDULER_THREAD_AFFINITY_CPU[slot] = cpu_slot as u32"),
                        body.rindex("scheduler_switch_unlock()"))
        self.assertIn("pub fn scheduler_thread_affinity_cpu(thread_id: u64) -> u32", text)
        self.assertNotIn("SCHEDULER_THREAD_OWNER_CPU[slot]", body)

    def test_ring3_payload_uses_sse_compare_and_exits_only_after_result(self):
        text = LOADER.read_text(encoding="utf-8")
        materialize = text.split("fn userspace_materialize_migration_probe", 1)[1].split(
            "fn userspace_release_frames", 1
        )[0]
        self.assertIn("USERSPACE_MIGRATION_CODE_BYTES: usize = 90", text)
        self.assertIn("USERSPACE_MIGRATION_PATTERN_BYTES: usize = 16", text)
        # movdqu xmm0,[rbx+64], movdqu xmm1,[rbx+64], pcmpeqb, pmovmskb.
        for opcode in (
            "243,15,111,67,64",
            "243,15,111,75,64",
            "102,15,116,200",
            "102,15,215,193",
            "61,255,255,0,0",
        ):
            self.assertIn(opcode, materialize)
        self.assertIn("USERSPACE_MIGRATION_PATTERN_OFFSET", materialize)
        self.assertIn("199,67,8,1,0,0,0", materialize)
        self.assertIn("199,67,12,1,0,0,0", materialize)

    def test_migration_borrows_root_only_while_registry_reference_is_live(self):
        text = LOADER.read_text(encoding="utf-8")
        body = text.split("pub fn userspace_loader_run_migration_probe() -> bool", 1)[1]
        retain = body.index("process_retain(pid)")
        borrow = body.index("process_borrow_root(pid)")
        create = body.index(
            "scheduler_create_process_thread(pid, entry, SCHEDULER_DEFAULT_THREAD_STACK_PAGES)"
        )
        tid_publish = body.index("unsafe { USERSPACE_TID = tid; }")
        drop_probe_ref = body.rindex(
            "if !process_release(pid) { loop { x86_cpu_pause(); } }",
            0,
            tid_publish,
        )
        self.assertNotIn("process_borrow_root(pid)", body[:retain])
        self.assertLess(retain, borrow)
        self.assertLess(borrow, create)
        self.assertLess(create, drop_probe_ref)
        self.assertLess(drop_probe_ref, tid_publish)

    def test_same_tid_moves_from_bsp_to_ap_before_user_is_released(self):
        text = LOADER.read_text(encoding="utf-8")
        body = text.split("pub fn userspace_loader_run_migration_probe() -> bool", 1)[1]
        for token in (
            "scheduler_create_process_thread(pid, entry, SCHEDULER_DEFAULT_THREAD_STACK_PAGES)",
            "scheduler_thread_affinity_cpu(tid) != 0",
            "scheduler_yield()",
            "let flags = x86_irq_save_disable();",
            "scheduler_set_thread_affinity(tid, USERSPACE_MIGRATION_CPU_SLOT)",
            "lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)",
            "userspace_migration_wait_ap(tid, root)",
            "x86_mmio_write32(release_address, 1)",
            "userspace_migration_wait_result(passed_address, failed_address)",
            "userspace_migration_wait_reaped(pid, reap_before)",
        ):
            self.assertIn(token, body)
        repin = body.index("scheduler_set_thread_affinity(tid, USERSPACE_MIGRATION_CPU_SLOT)")
        ipi = body.index("lapic_send_fixed(apic_id, IRQ_VECTOR_RESCHEDULE_IPI as u8)")
        ap = body.index("userspace_migration_wait_ap(tid, root)")
        release = body.index("x86_mmio_write32(release_address, 1)")
        self.assertLess(repin, ipi)
        self.assertLess(ipi, ap)
        self.assertLess(ap, release)
        self.assertNotIn("x86_write_cr3_raw", body)

        retry = body.split("while handoffs < SCHEDULER_ROUND_TRIP_SPIN_LIMIT && !repinned", 1)[1].split(
            "if !repinned ||", 1
        )[0]
        self.assertIn("repinned = scheduler_set_thread_affinity", retry)
        self.assertIn("if repinned { break; }", retry)
        self.assertNotIn("if !repinned { return false; }", retry)
        self.assertLess(retry.index("scheduler_yield()"), retry.index("scheduler_set_thread_affinity"))

        wait_ap = text.split("fn userspace_migration_wait_ap", 1)[1].split(
            "fn userspace_migration_wait_result", 1
        )[0]
        self.assertIn("scheduler_thread_owner_cpu(thread_id) == USERSPACE_MIGRATION_CPU_SLOT as u32", wait_ap)
        self.assertIn("scheduler_thread_affinity_cpu(thread_id) == USERSPACE_MIGRATION_CPU_SLOT as u32", wait_ap)
        self.assertIn("tlb_shootdown_cpu_root(USERSPACE_MIGRATION_CPU_SLOT) == root", wait_ap)
        self.assertLess(wait_ap.index("x86_irq_save_disable()"), wait_ap.index("scheduler_switch_lock()"))
        self.assertLess(wait_ap.index("scheduler_switch_lock()"), wait_ap.index("let observed ="))
        self.assertLess(wait_ap.index("== root;"), wait_ap.index("let unlocked = scheduler_switch_unlock()"))
        self.assertLess(wait_ap.index("let unlocked = scheduler_switch_unlock()"), wait_ap.rindex("x86_irq_restore(flags)"))

    def test_timer_may_claim_destination_before_reschedule_ipi(self):
        body = LOADER.read_text(encoding="utf-8").split(
            "pub fn userspace_loader_run_migration_probe() -> bool", 1
        )[1]
        # READY/unowned is checked inside the setter's lock (tested above).
        # Once published, AP timer dispatch is legal even before the BSP's IPI.
        # Do not reject that interleaving by testing a transient owner here.
        published = body.split("if !repinned ||", 1)[1].split(
            "userspace_migration_wait_ap(tid, root)", 1
        )[0]
        self.assertNotIn("scheduler_thread_owner_cpu", published)
        self.assertIn("scheduler_thread_affinity_cpu(tid)", published)

    def test_irq_serializes_fxsave_schedule_and_fxrstor_for_all_cpus(self):
        text = IRQ.read_text(encoding="utf-8")
        body = text.split("fn irq_schedule_with_fpu", 1)[1].split("@export", 1)[0]
        save = body.index("fpu_save_thread(old_tid)")
        schedule = body.index("scheduler_on_timer_interrupt(frame_address)")
        restore = body.index("fpu_restore_thread(new_tid)")
        self.assertLess(save, schedule)
        self.assertLess(schedule, restore)
        self.assertLess(body.index("scheduler_switch_lock()"), save)
        self.assertLess(restore, body.rindex("scheduler_switch_unlock()"))
        self.assertNotIn("if cpu_slot == 0 {", body)

    def test_runtime_and_smp_ci_require_final_migration_marker(self):
        runtime = RUNTIME.read_text(encoding="utf-8")
        body = runtime.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertIn("scheduler_smp_probe_run()", body)
        self.assertIn("userspace_loader_run_migration_probe()", body)
        self.assertLess(body.index("scheduler_smp_probe_run()"),
                        body.index("userspace_loader_run_migration_probe()"))

        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python3 tests/test_kernel_smp_process_migration.py", workflow)
        self.assertIn("BAKEN:SMP_PROCESS_MIGRATED", workflow)
        self.assertIn("BAKEN:SMP_FPU_MIGRATION_READY", workflow)
        self.assertIn("require_marker 'BAKEN:SMP_FPU_MIGRATION_READY'", workflow)

    def test_migration_probe_has_stage_diagnostics_and_ci_retries_runner_packages(self):
        loader = LOADER.read_text(encoding="utf-8")
        body = loader.split("pub fn userspace_loader_run_migration_probe() -> bool", 1)[1]
        self.assertIn("fn userspace_migration_diag(stage: u32) -> void", loader)
        self.assertIn("x86_serial_write_hex32_marker('M' as u8, stage)", loader)
        for stage in range(1, 11):
            self.assertIn(f"userspace_migration_diag({stage});", body)

        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("apt_retry()", workflow)
        self.assertIn("Acquire::Retries=5", workflow)
        self.assertIn("apt_retry update", workflow)
        self.assertIn("apt_retry install -y qemu-system-x86", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn("actions/upload-artifact@v6", workflow)


if __name__ == "__main__":
    unittest.main()

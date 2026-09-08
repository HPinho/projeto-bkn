import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "kernel/src/scheduler/core.sotlas"
THREAD = ROOT / "kernel/src/scheduler/thread.sotlas"
STACK_CACHE = ROOT / "kernel/src/scheduler/stack_cache.sotlas"
FRAME = ROOT / "kernel/src/arch/x86_64/thread_context.sotlas"
IRQ = ROOT / "kernel/src/interrupts/irq.sotlas"
CPU = ROOT / "kernel/src/arch/x86_64/cpu.sotlas"
RUNTIME = ROOT / "kernel/src/baken_native_runtime.sotlas"
INTRINSICS = ROOT / "tools/sotlas_compile/x86_intrinsics.py"
NVME_WORKFLOW = ROOT / ".github/workflows/baken_nvme_only.yml"


class KernelSchedulerTests(unittest.TestCase):
    def test_thread_model_has_explicit_lifecycle_and_saved_frame(self):
        text = THREAD.read_text(encoding="utf-8")
        for state in (
            "KERNEL_THREAD_UNUSED",
            "KERNEL_THREAD_READY",
            "KERNEL_THREAD_RUNNING",
            "KERNEL_THREAD_BLOCKED",
            "KERNEL_THREAD_TERMINATED",
        ):
            self.assertIn(state, text)
        self.assertIn("pub saved_frame: u64", text)
        self.assertIn("pub stack_physical_base: u64", text)
        self.assertIn("pub stack_virtual_top: u64", text)

    def test_x86_thread_frame_matches_irq_restore_shape(self):
        text = FRAME.read_text(encoding="utf-8")
        self.assertIn("X86_KERNEL_THREAD_FRAME_QWORDS: u64 = 21", text)
        self.assertIn("X86_KERNEL_THREAD_FRAME_BYTES: u64 = 168", text)
        fields = [
            "pub r15: u64", "pub r14: u64", "pub r13: u64", "pub r12: u64",
            "pub r11: u64", "pub r10: u64", "pub r9: u64", "pub r8: u64",
            "pub rdi: u64", "pub rsi: u64", "pub rbp: u64", "pub rbx: u64",
            "pub rdx: u64", "pub rcx: u64", "pub rax: u64", "pub vector: u64",
            "pub rip: u64", "pub cs: u64", "pub rflags: u64",
            "pub rsp: u64", "pub ss: u64",
        ]
        positions = [text.index(field) for field in fields]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("GDT_KERNEL_CODE_SELECTOR as u64", text)
        self.assertIn("GDT_KERNEL_DATA_SELECTOR as u64", text)
        self.assertIn("(*frame).rsp = aligned_top", text)
        self.assertIn("(*frame).ss = GDT_KERNEL_DATA_SELECTOR as u64", text)
        self.assertIn("X86_KERNEL_THREAD_INITIAL_RFLAGS: u64 = 0x2", text)
        self.assertNotIn("X86_KERNEL_THREAD_INITIAL_RFLAGS: u64 = 0x202", text)

    def test_new_thread_entry_uses_native_trampoline_and_explicit_stack_top(self):
        frame = FRAME.read_text(encoding="utf-8")
        cpu = CPU.read_text(encoding="utf-8")
        intrinsics = INTRINSICS.read_text(encoding="utf-8")

        self.assertIn("x86_scheduler_thread_trampoline_address()", frame)
        self.assertIn("(*frame).r11 = entry_rip", frame)
        self.assertIn("(*frame).r10 = aligned_top", frame)
        self.assertIn("(*frame).rip = trampoline_rip", frame)
        self.assertIn("(*frame).rsp = aligned_top", frame)
        self.assertIn("(*frame).ss = GDT_KERNEL_DATA_SELECTOR as u64", frame)
        self.assertNotIn("synthetic_return", frame)

        self.assertIn("pub fn x86_scheduler_thread_trampoline_address() -> u64", cpu)
        self.assertIn("__scheduler_thread_trampoline_address()", cpu)

        trampoline = intrinsics.split("static void __scheduler_thread_trampoline(void)", 1)[1]
        trampoline = trampoline.split("static inline uint64_t __scheduler_thread_trampoline_address", 1)[0]
        restore = trampoline.index('"movq %r10, %rsp\\n\\t"')
        home = trampoline.index('"subq $32, %rsp\\n\\t"')
        sti = trampoline.index('"sti\\n\\t"')
        entry_call = trampoline.index('"call *%r11\\n\\t"')
        exit_call = trampoline.index('"call sotlas_x86_scheduler_thread_exit\\n\\t"')
        self.assertLess(restore, home)
        self.assertLess(home, sti)
        self.assertLess(sti, entry_call)
        self.assertLess(entry_call, exit_call)

    def test_irq_backend_can_restore_dispatcher_selected_frame(self):
        text = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn(
            "extern uint64_t sotlas_x86_irq_dispatch(uint64_t vector, uint64_t frame_address);",
            text,
        )
        self.assertIn('"movq %r12, %rdx\\n\\t"', text)
        self.assertIn('"movq %rax, %rsp\\n\\t"', text)
        self.assertIn('"iretq\\n\\t"', text)

    def test_timer_dispatch_returns_scheduler_resume_frame(self):
        text = IRQ.read_text(encoding="utf-8")
        self.assertIn(
            "pub fn sotlas_x86_irq_dispatch(vector: u64, frame_address: u64) -> u64",
            text,
        )
        timer = text.split("if vector == IRQ_VECTOR_TIMER as u64", 1)[1]
        timer = timer.split("if vector == IRQ_VECTOR_KEYBOARD as u64", 1)[0]
        self.assertIn("lapic_eoi();", timer)
        self.assertIn("return scheduler_on_timer_interrupt(frame_address);", timer)

    def test_scheduler_allocates_real_idle_stack_and_initial_frame(self):
        text = CORE.read_text(encoding="utf-8")
        self.assertIn("pmm_alloc_pages(SCHEDULER_IDLE_STACK_PAGES)", text)
        self.assertIn("direct_map_virtual_address(stack_physical)", text)
        self.assertIn("x86_scheduler_idle_entry_address()", text)
        self.assertIn("x86_kernel_thread_prepare_frame(stack_top, idle_entry)", text)
        self.assertIn("pub fn sotlas_x86_scheduler_idle_entry() -> !", text)

    def test_scheduler_has_fixed_run_queue_with_bootstrap_idle_and_dynamic_slots(self):
        text = CORE.read_text(encoding="utf-8")
        self.assertIn("SCHEDULER_THREAD_SLOT_COUNT: usize = 8", text)
        self.assertIn("SCHEDULER_BOOT_SLOT: usize = 0", text)
        self.assertIn("SCHEDULER_IDLE_SLOT: usize = 1", text)
        self.assertIn("SCHEDULER_FIRST_DYNAMIC_SLOT: usize = 2", text)
        self.assertIn(
            "static mut SCHEDULER_THREADS: [KernelThread; SCHEDULER_THREAD_SLOT_COUNT]",
            text,
        )
        self.assertIn("scheduler_find_next_ready_normal", text)
        self.assertIn("scheduler_select_slot", text)

    def test_generic_kernel_thread_creation_reuses_or_allocates_owned_stack(self):
        text = CORE.read_text(encoding="utf-8")
        create = text.split("pub fn scheduler_create_kernel_thread", 1)[1]
        create = create.split("pub fn scheduler_block_current", 1)[0]
        self.assertIn("scheduler_find_free_dynamic_slot()", create)
        self.assertIn("scheduler_stack_cache_take(stack_pages)", create)
        self.assertIn("pmm_alloc_pages(stack_pages)", create)
        self.assertIn("direct_map_virtual_address(stack_physical)", create)
        self.assertIn("x86_kernel_thread_prepare_frame(stack_top, entry_rip)", create)
        self.assertIn("scheduler_return_unpublished_stack", create)
        self.assertIn("KERNEL_THREAD_READY", create)

    def test_terminated_slots_are_not_reused_before_reaper(self):
        text = CORE.read_text(encoding="utf-8")
        finder = text.split("fn scheduler_find_free_dynamic_slot", 1)[1]
        finder = finder.split("fn scheduler_find_thread_slot", 1)[0]
        self.assertIn("KERNEL_THREAD_UNUSED", finder)
        condition = finder.split("if SCHEDULER_THREADS[slot].state", 1)[1]
        condition = condition.split("{", 1)[0]
        self.assertNotIn("KERNEL_THREAD_TERMINATED", condition)

    def test_stack_cache_transfers_ownership_without_firmware_or_heap(self):
        text = STACK_CACHE.read_text(encoding="utf-8")
        for token in (
            "SCHEDULER_STACK_CACHE_CAPACITY",
            "scheduler_stack_cache_reset()",
            "scheduler_stack_cache_put(base: u64, pages: u64)",
            "scheduler_stack_cache_take(pages: u64)",
            "scheduler_stack_cache_count()",
        ):
            self.assertIn(token, text)
        code = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
        for forbidden in ("BootServices", "AllocatePages", "malloc(", "free("):
            self.assertNotIn(forbidden, code)

    def test_reaper_never_frees_current_stack_and_has_safe_cache_fallback(self):
        text = CORE.read_text(encoding="utf-8")
        reaper = text.split("fn scheduler_reap_terminated_noncurrent", 1)[1]
        reaper = reaper.split("pub fn scheduler_initialize", 1)[0]
        self.assertIn("let current = SCHEDULER_CURRENT_SLOT", reaper)
        self.assertIn("slot != current", reaper)
        self.assertIn("KERNEL_THREAD_TERMINATED", reaper)
        lifo = reaper.index("pmm_free_pages_lifo(stack_base, stack_pages)")
        cache = reaper.index("scheduler_stack_cache_put(stack_base, stack_pages)")
        clear = reaper.index("SCHEDULER_THREADS[slot] = kernel_thread_empty(0)")
        self.assertLess(lifo, cache)
        self.assertLess(cache, clear)
        self.assertIn("SCHEDULER_RUN_QUEUE_PROBE_REAPED = true", reaper)
        self.assertIn("scheduler_write_thread_reap_marker_once()", reaper)
        self.assertIn("scheduler_write_stack_release_marker_once()", reaper)

    def test_block_and_wake_are_explicit_thread_state_transitions(self):
        text = CORE.read_text(encoding="utf-8")
        block = text.split("pub fn scheduler_block_current", 1)[1]
        block = block.split("pub fn scheduler_wake_thread", 1)[0]
        wake = text.split("pub fn scheduler_wake_thread", 1)[1]
        wake = wake.split("pub fn scheduler_terminate_current", 1)[0]
        self.assertIn("KERNEL_THREAD_BLOCKED", block)
        self.assertIn("KERNEL_THREAD_BLOCKED", wake)
        self.assertIn("KERNEL_THREAD_READY", wake)

    def test_thread_exit_marks_terminated_without_freeing_current_stack(self):
        text = CORE.read_text(encoding="utf-8")
        terminate = text.split("pub fn scheduler_terminate_current", 1)[1]
        terminate = terminate.split("pub fn sotlas_x86_scheduler_thread_exit", 1)[0]
        exit_path = text.split("pub fn sotlas_x86_scheduler_thread_exit", 1)[1]
        exit_path = exit_path.split("pub fn scheduler_is_active", 1)[0]

        self.assertIn("KERNEL_THREAD_TERMINATED", terminate)
        self.assertIn("scheduler_write_thread_exit_marker_once()", terminate)
        self.assertNotIn("pmm_free_pages_lifo", terminate)
        self.assertIn("x86_cli_raw();", exit_path)
        self.assertIn("scheduler_terminate_current()", exit_path)
        self.assertIn("x86_sti_raw();", exit_path)
        self.assertNotIn("pmm_free_pages_lifo", exit_path)

    def test_idle_is_only_fallback_when_no_normal_thread_is_ready(self):
        text = CORE.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_on_timer_interrupt", 1)[1]
        normal_pick = body.index("scheduler_find_next_ready_normal(start)")
        idle_pick = body.index("scheduler_select_slot(SCHEDULER_IDLE_SLOT, frame_address)", normal_pick)
        self.assertLess(normal_pick, idle_pick)

    def test_reaper_runs_on_bsp_after_current_frame_is_saved(self):
        text = CORE.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_on_timer_interrupt", 1)[1]
        save = body.index("SCHEDULER_THREADS[current].saved_frame = frame_address")
        reap = body.index("scheduler_reap_terminated_noncurrent()")
        self.assertLess(save, reap)

        secondary = text.split("fn scheduler_on_secondary_interrupt", 1)[1]
        secondary = secondary.split("pub fn scheduler_on_timer_interrupt", 1)[0]
        self.assertNotIn("scheduler_reap_terminated_noncurrent()", secondary)
        self.assertIn("if cpu_slot != 0 { return scheduler_on_secondary_interrupt(cpu_slot, frame_address); }", body)

    def test_scheduler_round_trip_run_queue_and_reaper_are_required_before_runtime(self):
        text = RUNTIME.read_text(encoding="utf-8")
        body = text.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertIn("x86_cli_raw();", body)
        self.assertIn("scheduler_initialize()", body)
        self.assertIn("x86_sti_raw();", body)
        self.assertIn("scheduler_wait_first_round_trip()", body)
        self.assertIn("scheduler_start_run_queue_probe()", body)
        self.assertIn("scheduler_wait_run_queue_probe()", body)
        self.assertIn("scheduler_wait_reaper_probe()", body)
        self.assertLess(body.index("scheduler_wait_first_round_trip()"), body.index("scheduler_start_run_queue_probe()"))
        self.assertLess(body.index("scheduler_wait_run_queue_probe()"), body.index("scheduler_wait_reaper_probe()"))
        self.assertLess(body.index("scheduler_wait_reaper_probe()"), body.index("display_init("))

    def test_run_queue_probe_is_a_real_returning_thread_with_terminated_or_reaped_state(self):
        text = CORE.read_text(encoding="utf-8")
        cpu = CPU.read_text(encoding="utf-8")
        intrinsics = INTRINSICS.read_text(encoding="utf-8")

        self.assertIn("pub fn sotlas_x86_scheduler_exit_probe_entry() -> void", text)
        probe = text.split("pub fn scheduler_start_run_queue_probe", 1)[1]
        probe = probe.split("pub fn scheduler_on_timer_interrupt", 1)[0]
        self.assertIn("x86_scheduler_exit_probe_entry_address()", probe)
        self.assertIn(
            "scheduler_create_process_thread(pid, entry, SCHEDULER_DEFAULT_THREAD_STACK_PAGES)",
            probe,
        )
        self.assertIn("pub fn x86_scheduler_exit_probe_entry_address() -> u64", cpu)
        self.assertIn("__scheduler_exit_probe_entry_address()", cpu)
        self.assertIn("extern void sotlas_x86_scheduler_thread_exit(void);", intrinsics)
        self.assertIn('"call sotlas_x86_scheduler_thread_exit\\n\\t"', intrinsics)

        irq_path = text.split("pub fn scheduler_on_timer_interrupt", 1)[1]
        self.assertIn("current_terminated", irq_path)
        self.assertIn("SCHEDULER_RUN_QUEUE_PROBE_COMPLETE = true", irq_path)
        wait = text.split("pub fn scheduler_wait_run_queue_probe", 1)[1]
        wait = wait.split("pub fn scheduler_wait_reaper_probe", 1)[0]
        self.assertIn("scheduler_thread_is_terminated(SCHEDULER_RUN_QUEUE_PROBE_THREAD_ID)", wait)
        self.assertIn("SCHEDULER_RUN_QUEUE_PROBE_REAPED", wait)
        reap_wait = text.split("pub fn scheduler_wait_reaper_probe", 1)[1]
        self.assertIn("SCHEDULER_RUN_QUEUE_PROBE_REAPED", reap_wait)
        self.assertIn("SCHEDULER_REAP_COUNT != 0", reap_wait)

    def test_qemu_gate_requires_round_trip_dynamic_thread_exit_and_reap_proof(self):
        text = NVME_WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "BAKEN:SCHEDULER_SWITCH",
            "BAKEN:SCHEDULER_ROUND_TRIP",
            "BAKEN:RUN_QUEUE_CREATED",
            "BAKEN:RUN_QUEUE_SWITCH",
            "BAKEN:THREAD_EXIT",
            "BAKEN:THREAD_REAP",
            "BAKEN:STACK_RELEASE",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertIn('grep -Fq "$marker"', text)
        self.assertIn('require_serial_marker "$marker"', text)

    def test_idle_entry_address_is_low_level_backend_helper(self):
        cpu = CPU.read_text(encoding="utf-8")
        intrinsics = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn("pub fn x86_scheduler_idle_entry_address() -> u64", cpu)
        self.assertIn("__scheduler_idle_entry_address()", cpu)
        self.assertIn("extern void sotlas_x86_scheduler_idle_entry(void);", intrinsics)
        self.assertIn("static inline uint64_t __scheduler_idle_entry_address(void)", intrinsics)


if __name__ == "__main__":
    unittest.main()
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "kernel/src/scheduler/core.sotlas"
THREAD = ROOT / "kernel/src/scheduler/thread.sotlas"
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
        self.assertIn("X86_KERNEL_THREAD_FRAME_QWORDS: u64 = 19", text)
        self.assertIn("X86_KERNEL_THREAD_FRAME_BYTES: u64 = 152", text)
        fields = [
            "pub r15: u64", "pub r14: u64", "pub r13: u64", "pub r12: u64",
            "pub r11: u64", "pub r10: u64", "pub r9: u64", "pub r8: u64",
            "pub rdi: u64", "pub rsi: u64", "pub rbp: u64", "pub rbx: u64",
            "pub rdx: u64", "pub rcx: u64", "pub rax: u64", "pub vector: u64",
            "pub rip: u64", "pub cs: u64", "pub rflags: u64",
        ]
        positions = [text.index(field) for field in fields]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("GDT_KERNEL_CODE_SELECTOR as u64", text)
        self.assertIn("X86_KERNEL_THREAD_INITIAL_RFLAGS: u64 = 0x202", text)

    def test_new_thread_entry_reserves_full_win64_home_space(self):
        text = FRAME.read_text(encoding="utf-8")
        self.assertIn("X86_KERNEL_THREAD_RETURN_SLOT_BYTES: u64 = 8", text)
        self.assertIn("X86_KERNEL_THREAD_HOME_SPACE_BYTES: u64 = 32", text)
        self.assertIn("X86_KERNEL_THREAD_ENTRY_RESERVE_BYTES", text)
        self.assertIn("let entry_stack = aligned_top - X86_KERNEL_THREAD_ENTRY_RESERVE_BYTES", text)
        self.assertIn("if (entry_stack & 0x0F) != 8", text)
        self.assertIn("let synthetic_return = entry_stack as *mut u64", text)
        self.assertIn("(*synthetic_return) = 0", text)

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

    def test_generic_kernel_thread_creation_owns_pmm_backed_stack(self):
        text = CORE.read_text(encoding="utf-8")
        create = text.split("pub fn scheduler_create_kernel_thread", 1)[1]
        create = create.split("pub fn scheduler_block_current", 1)[0]
        self.assertIn("scheduler_find_free_dynamic_slot()", create)
        self.assertIn("pmm_alloc_pages(stack_pages)", create)
        self.assertIn("direct_map_virtual_address(stack_physical)", create)
        self.assertIn("x86_kernel_thread_prepare_frame(stack_top, entry_rip)", create)
        self.assertIn("KERNEL_THREAD_READY", create)
        self.assertGreaterEqual(create.count("pmm_free_pages_lifo(stack_physical, stack_pages)"), 4)

    def test_block_and_wake_are_explicit_thread_state_transitions(self):
        text = CORE.read_text(encoding="utf-8")
        block = text.split("pub fn scheduler_block_current", 1)[1]
        block = block.split("pub fn scheduler_wake_thread", 1)[0]
        wake = text.split("pub fn scheduler_wake_thread", 1)[1]
        wake = wake.split("pub fn scheduler_is_active", 1)[0]
        self.assertIn("KERNEL_THREAD_BLOCKED", block)
        self.assertIn("KERNEL_THREAD_BLOCKED", wake)
        self.assertIn("KERNEL_THREAD_READY", wake)

    def test_idle_is_only_fallback_when_no_normal_thread_is_ready(self):
        text = CORE.read_text(encoding="utf-8")
        body = text.split("pub fn scheduler_on_timer_interrupt", 1)[1]
        normal_pick = body.index("scheduler_find_next_ready_normal(start)")
        idle_pick = body.index("scheduler_select_slot(SCHEDULER_IDLE_SLOT, frame_address)", normal_pick)
        self.assertLess(normal_pick, idle_pick)

    def test_scheduler_round_trip_and_run_queue_probe_are_required_before_runtime(self):
        text = RUNTIME.read_text(encoding="utf-8")
        body = text.split("pub fn baken_native_kernel_run", 1)[1]
        self.assertIn("x86_cli_raw();", body)
        self.assertIn("scheduler_initialize()", body)
        self.assertIn("x86_sti_raw();", body)
        self.assertIn("scheduler_wait_first_round_trip()", body)
        self.assertIn("scheduler_start_run_queue_probe()", body)
        self.assertIn("scheduler_wait_run_queue_probe()", body)
        self.assertLess(body.index("scheduler_wait_first_round_trip()"), body.index("scheduler_start_run_queue_probe()"))
        self.assertLess(body.index("scheduler_wait_run_queue_probe()"), body.index("display_init("))

    def test_run_queue_probe_is_a_real_third_thread_with_own_stack(self):
        text = CORE.read_text(encoding="utf-8")
        probe = text.split("pub fn scheduler_start_run_queue_probe", 1)[1]
        probe = probe.split("pub fn scheduler_on_timer_interrupt", 1)[0]
        self.assertIn("x86_scheduler_idle_entry_address()", probe)
        self.assertIn(
            "scheduler_create_kernel_thread(entry, SCHEDULER_DEFAULT_THREAD_STACK_PAGES)",
            probe,
        )
        irq_path = text.split("pub fn scheduler_on_timer_interrupt", 1)[1]
        self.assertIn("SCHEDULER_RUN_QUEUE_PROBE_THREAD_ID", irq_path)
        self.assertIn("KERNEL_THREAD_BLOCKED", irq_path)
        self.assertIn("SCHEDULER_RUN_QUEUE_PROBE_COMPLETE = true", irq_path)

    def test_qemu_gate_requires_round_trip_and_dynamic_thread_proof(self):
        text = NVME_WORKFLOW.read_text(encoding="utf-8")
        for marker in (
            "BAKEN:SCHEDULER_SWITCH",
            "BAKEN:SCHEDULER_ROUND_TRIP",
            "BAKEN:RUN_QUEUE_CREATED",
            "BAKEN:RUN_QUEUE_SWITCH",
        ):
            with self.subTest(marker=marker):
                self.assertIn(f"grep -Fq '{marker}'", text)

    def test_idle_entry_address_is_low_level_backend_helper(self):
        cpu = CPU.read_text(encoding="utf-8")
        intrinsics = INTRINSICS.read_text(encoding="utf-8")
        self.assertIn("pub fn x86_scheduler_idle_entry_address() -> u64", cpu)
        self.assertIn("__scheduler_idle_entry_address()", cpu)
        self.assertIn("extern void sotlas_x86_scheduler_idle_entry(void);", intrinsics)
        self.assertIn("static inline uint64_t __scheduler_idle_entry_address(void)", intrinsics)


if __name__ == "__main__":
    unittest.main()

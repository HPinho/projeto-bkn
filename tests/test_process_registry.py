"""Source contracts supplement the registry's PMM-backed QEMU self-test."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProcessRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "kernel/src/process/registry.sotlas").read_text(encoding="utf-8")

    def test_pid_never_wraps_or_recycles(self):
        self.assertIn("PROCESS_NEXT_ID == PROCESS_ID_MAX", self.source)
        self.assertIn("PROCESS_NEXT_ID += 1", self.source)
        self.assertEqual(self.source.count("PROCESS_NEXT_ID: u64 = 1"), 1)
        self.assertIn("if pid == 0", self.source)

    def test_destruction_requires_no_references_and_releases_tables_first(self):
        body = self.source.split("fn process_destroy_locked", 1)[1].split("fn process_retain_locked", 1)[0]
        self.assertLess(body.index("PROCESS_REFERENCES[slot] != 0"), body.index("process_address_space_destroy"))
        self.assertLess(body.index("process_address_space_destroy"), body.index("PROCESS_IDS[slot] = 0"))

    def test_refcount_overflow_and_underflow_are_rejected(self):
        self.assertIn("PROCESS_REFERENCES[slot] == PROCESS_ID_MAX", self.source)
        self.assertIn("PROCESS_REFERENCES[slot] == 0", self.source)

    def test_public_lifetime_operations_use_smp_registry_lock(self):
        for name in ("create", "destroy", "retain", "release"):
            body = self.source.split(f"pub fn process_{name}(", 1)[1].split("\n}", 1)[0]
            self.assertIn("process_registry_lock_irq()", body)
            self.assertIn("process_registry_unlock_irq(flags)", body)

    def test_registry_lock_masks_irq_and_serializes_all_cpus(self):
        self.assertIn("import kernel::sync::spinlock::*;", self.source)
        self.assertIn("static mut PROCESS_REGISTRY_LOCK: SpinLock", self.source)
        lock = self.source.split("fn process_registry_lock_irq() -> u64", 1)[1].split(
            "fn process_registry_unlock_irq", 1
        )[0]
        self.assertLess(lock.index("x86_irq_save_disable()"), lock.index("spinlock_lock(&mut PROCESS_REGISTRY_LOCK)"))
        unlock = self.source.split("fn process_registry_unlock_irq(flags: u64)", 1)[1].split(
            "fn process_find_locked", 1
        )[0]
        self.assertLess(unlock.index("spinlock_unlock(&mut PROCESS_REGISTRY_LOCK)"), unlock.index("x86_irq_restore(flags)"))

    def test_registry_documents_one_way_pmm_lock_hierarchy(self):
        self.assertIn("PROCESS_REGISTRY_LOCK -> PMM_ALLOCATOR_LOCK", self.source)
        pmm = (ROOT / "kernel/src/memory/pmm_allocator.sotlas").read_text(encoding="utf-8")
        self.assertNotIn("process_registry_", pmm)

    def test_runtime_probe_covers_capacity_stale_ids_and_reclamation(self):
        for token in ("let unexpected = process_create_locked()", "process_retain_locked(first)",
                      "process_destroy_locked(first)", "process_release_locked(first)",
                      "ids[0] <= ids[PROCESS_SLOT_COUNT - 1]",
                      "pmm_allocator_allocated_pages() == before"):
            self.assertIn(token, self.source)

    def test_boot_gate_runs_before_scheduler(self):
        source = (ROOT / "kernel/src/baken_native_runtime.sotlas").read_text(encoding="utf-8")
        self.assertLess(source.index("process_registry_activate()"), source.index("scheduler_initialize()"))
        self.assertLess(source.index("process_registry_activate()"), source.index("process_registry_emit_ready_marker()"))
        from tools.scripts.verify_kernel_smoke import REQUIRED
        self.assertIn("PROCESS_REGISTRY_READY", REQUIRED)

    def test_registry_does_not_claim_userspace_execution(self):
        self.assertNotIn("x86_write_cr3_raw", self.source)
        self.assertNotIn("scheduler_create_kernel_thread", self.source)

"""DF-1: mutacoes e snapshots serializados; IF=0 nao equivale a erro."""
import unittest
from pathlib import Path

REGISTRY = (Path(__file__).resolve().parents[1] / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")


class DeviceSmpSafetyTests(unittest.TestCase):
    def test_irq_save_lock_uses_separate_success_channel(self):
        self.assertIn("fn device_lock_irq(saved_flags: *mut u64) -> bool", REGISTRY)
        self.assertIn("*saved_flags = flags", REGISTRY)
        self.assertNotIn("if flags == 0", REGISTRY)
        self.assertIn("spinlock_unlock(&mut DEVICE_CORE_LOCK)", REGISTRY)
        self.assertIn("x86_irq_restore(flags)", REGISTRY)

    def test_every_public_operation_uses_same_lock(self):
        for op in ("device_core_attach", "device_core_snapshot", "device_core_attached_count",
                   "device_core_mark_failed", "device_core_detach"):
            body = REGISTRY.split(f"pub fn {op}", 1)[1].split("\n@system", 1)[0]
            self.assertIn("device_lock_irq(&mut flags)", body)
            self.assertIn("device_unlock_irq(flags)", body)


if __name__ == "__main__":
    unittest.main()

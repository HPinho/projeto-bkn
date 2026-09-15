"""DF-1: handles velhos nunca revalidam depois de reuse."""
import unittest
from pathlib import Path

REGISTRY = (Path(__file__).resolve().parents[1] / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")


class DeviceGenerationTests(unittest.TestCase):
    def test_reuse_increments_generation_before_publish(self):
        attach = REGISTRY.split("pub fn device_core_attach", 1)[1].split("pub fn device_core_snapshot", 1)[0]
        self.assertLess(attach.index("device_generation_next(DEVICE_GENERATIONS[slot])"),
                        attach.index("DEVICE_RECORDS[slot] = DeviceRecord"))
        self.assertIn("DEVICE_RECORDS[slot].state == DEVICE_STATE_DETACHED", attach)

    def test_all_lookups_compare_both_id_and_generation(self):
        check = REGISTRY.split("fn device_handle_live_locked", 1)[1].split("pub fn device_core_init", 1)[0]
        self.assertIn("DEVICE_RECORDS[slot].handle.generation == handle.generation", check)
        self.assertIn("DEVICE_RECORDS[slot].state != DEVICE_STATE_DETACHED", check)
        for op in ("device_core_snapshot", "device_core_mark_failed", "device_core_detach"):
            body = REGISTRY.split(f"pub fn {op}", 1)[1].split("\n@system", 1)[0]
            self.assertIn("device_handle_live_locked(handle)", body)


if __name__ == "__main__":
    unittest.main()

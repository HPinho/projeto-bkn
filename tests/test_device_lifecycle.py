"""DF-1: transitions e arvore possuem politica conservadora."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (ROOT / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")
LIFECYCLE = (ROOT / "kernel/src/device/lifecycle.sotlas").read_text(encoding="utf-8")


class DeviceLifecycleTests(unittest.TestCase):
    def test_attach_active_failed_detached_are_explicit(self):
        for name in ("ATTACHED", "ACTIVE", "FAILED", "DETACHED"):
            self.assertIn(f"DEVICE_STATE_{name}", REGISTRY)
        self.assertIn("device_core_set_state(handle, DEVICE_STATE_ATTACHED, DEVICE_STATE_ACTIVE)", LIFECYCLE)
        self.assertIn("device_core_detach(handle)", LIFECYCLE)

    def test_parent_must_be_live_and_children_detach_first(self):
        self.assertIn("parent.valid && !device_handle_live_locked(parent)", REGISTRY)
        self.assertIn("DEVICE_RECORDS[parent_slot].child_count += 1", REGISTRY)
        self.assertIn("DEVICE_RECORDS[slot].child_count == 0", REGISTRY)
        self.assertIn("DEVICE_RECORDS[parent_slot].child_count -= 1", REGISTRY)

    def test_detach_never_leaves_old_driver_owner(self):
        detach = REGISTRY.split("pub fn device_core_detach", 1)[1]
        self.assertIn("DEVICE_RECORDS[slot].state = DEVICE_STATE_DETACHED", detach)
        self.assertIn("DEVICE_RECORDS[slot].driver_id = 0", detach)


if __name__ == "__main__":
    unittest.main()

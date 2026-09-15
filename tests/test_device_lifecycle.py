"""DF-3.1a: lifecycle universal nao possui atalho para ACTIVE."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (ROOT / "kernel/src/device/registry.sotlas").read_text(encoding="utf-8")
LIFECYCLE = (ROOT / "kernel/src/device/lifecycle.sotlas").read_text(encoding="utf-8")


class DeviceLifecycleTests(unittest.TestCase):
    def test_states_are_explicit_and_active_has_no_public_shortcut(self):
        for name in ("ATTACHED", "BINDING", "ACTIVE", "UNBINDING", "FAILED", "DETACHED"):
            self.assertIn(f"DEVICE_STATE_{name}", REGISTRY)
        self.assertNotIn("pub fn device_activate", LIFECYCLE)
        self.assertNotIn("pub fn device_core_set_state", REGISTRY)
        self.assertIn("device_core_mark_failed(handle)", LIFECYCLE)
        self.assertIn("device_core_detach(handle)", LIFECYCLE)

    def test_active_is_reached_only_by_transactional_bind_commit(self):
        commit = REGISTRY.split("pub fn device_core_commit_bind", 1)[1].split(
            "pub fn device_core_abort_bind", 1)[0]
        self.assertIn("DEVICE_STATE_BINDING", commit)
        self.assertIn("DEVICE_STATE_ACTIVE", commit)
        self.assertIn("driver_handle_equal(DEVICE_RECORDS[slot].driver, driver)", commit)
        self.assertNotIn("DEVICE_STATE_ATTACHED", commit)

    def test_failure_api_cannot_promote_a_device(self):
        failed = REGISTRY.split("pub fn device_core_mark_failed", 1)[1].split(
            "pub fn device_core_begin_bind", 1)[0]
        self.assertIn("DEVICE_STATE_FAILED", failed)
        self.assertIn("DEVICE_STATE_ATTACHED", failed)
        self.assertIn("DEVICE_STATE_ACTIVE", failed)
        self.assertNotIn("DEVICE_STATE_BINDING", failed)
        self.assertNotIn("DEVICE_STATE_UNBINDING", failed)

    def test_parent_must_be_live_and_children_detach_first(self):
        self.assertIn("parent.valid && !device_handle_live_locked(parent)", REGISTRY)
        self.assertIn("DEVICE_RECORDS[parent_slot].child_count += 1", REGISTRY)
        self.assertIn("DEVICE_RECORDS[slot].child_count == 0", REGISTRY)
        self.assertIn("DEVICE_RECORDS[parent_slot].child_count -= 1", REGISTRY)

    def test_detach_never_leaves_old_driver_owner(self):
        detach = REGISTRY.split("pub fn device_core_detach", 1)[1]
        self.assertIn("DEVICE_RECORDS[slot].state = DEVICE_STATE_DETACHED", detach)
        self.assertIn("DEVICE_RECORDS[slot].driver = driver_invalid_handle()", detach)
        self.assertIn("!DEVICE_RECORDS[slot].driver.valid", detach)
        self.assertIn("DEVICE_RECORDS[slot].state == DEVICE_STATE_ATTACHED", detach)


if __name__ == "__main__":
    unittest.main()

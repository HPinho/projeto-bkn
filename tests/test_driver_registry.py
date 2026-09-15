"""DF-2: registro, matching e callbacks de drivers."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "kernel/src/device/driver_registry.sotlas").read_text(encoding="utf-8")
TYPES = (ROOT / "kernel/src/device/types.sotlas").read_text(encoding="utf-8")


class DriverRegistryTests(unittest.TestCase):
    def test_descriptor_has_match_priority_probe_and_remove(self):
        for token in ("pub struct DriverMatch", "pub struct DriverDescriptor",
                      "priority: u32", "probe: fn(DeviceHandle) -> bool",
                      "remove: fn(DeviceHandle) -> bool"):
            self.assertIn(token, TYPES + SOURCE)

    def test_matching_is_bus_class_vendor_and_hardware_aware(self):
        body = SOURCE.split("fn driver_matches", 1)[1].split("pub fn driver_registry_init", 1)[0]
        for token in ("rule.bus != device.bus", "rule.class_code != device.class_code",
                      "rule.vendor_id != DRIVER_MATCH_ANY",
                      "rule.hardware_id != DRIVER_MATCH_ANY"):
            self.assertIn(token, body)

    def test_highest_priority_matching_driver_wins(self):
        body = SOURCE.split("pub fn driver_bind", 1)[1].split("pub fn driver_unbind", 1)[0]
        self.assertIn("DRIVER_RECORDS[search_slot].descriptor.priority > selected_priority", body)
        self.assertIn("selected = DRIVER_RECORDS[search_slot].handle", body)

    def test_callbacks_run_outside_registry_lock(self):
        bind = SOURCE.split("pub fn driver_bind", 1)[1].split("pub fn driver_unbind", 1)[0]
        self.assertLess(bind.index("driver_unlock_irq(flags)"), bind.index("let probe_ok = selected_record.descriptor.probe(device)"))
        unbind = SOURCE.split("pub fn driver_unbind", 1)[1]
        self.assertLess(unbind.index("driver_unlock_irq(flags)"), unbind.index("let remove_ok = selected_record.descriptor.remove(device)"))


if __name__ == "__main__":
    unittest.main()

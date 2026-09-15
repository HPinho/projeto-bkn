"""DF-2: handles de drivers também são generation-safe."""
import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "kernel/src/device/driver_registry.sotlas").read_text(encoding="utf-8")


class DriverGenerationTests(unittest.TestCase):
    def test_registration_advances_generation_before_publish(self):
        body = SOURCE.split("pub fn driver_register", 1)[1].split("pub fn driver_unregister", 1)[0]
        self.assertLess(body.index("driver_generation_next(DRIVER_GENERATIONS[slot])"),
                        body.index("DRIVER_RECORDS[slot].handle = result"))

    def test_operations_validate_id_and_generation(self):
        live = SOURCE.split("fn driver_handle_live_locked", 1)[1].split("fn driver_rule_valid", 1)[0]
        self.assertIn("DRIVER_RECORDS[slot].handle.generation == handle.generation", live)
        for operation in ("driver_unregister", "driver_unbind"):
            body = SOURCE.split(f"pub fn {operation}", 1)[1]
            self.assertIn("driver_handle_live_locked", body)


if __name__ == "__main__":
    unittest.main()

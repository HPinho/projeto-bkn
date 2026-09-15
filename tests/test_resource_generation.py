"""DF-3: handles de recursos são protegidos contra ABA."""
import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] /
          "kernel/src/device/resource_manager.sotlas").read_text(encoding="utf-8")


class ResourceGenerationTests(unittest.TestCase):
    def test_slots_have_persistent_generation(self):
        self.assertIn("RESOURCE_GENERATIONS", SOURCE)
        self.assertIn("resource_generation_next", SOURCE)
        self.assertIn("RESOURCE_GENERATIONS[free_slot] = generation", SOURCE)

    def test_lookup_compares_generation(self):
        body = SOURCE.split("fn resource_handle_live_locked", 1)[1].split(
            "pub fn resource_manager_init", 1)[0]
        self.assertIn("RESOURCE_CLAIMS[slot].handle.generation == handle.generation", body)

    def test_release_invalidates_claim_without_resetting_generation(self):
        release = SOURCE.split("pub fn resource_release", 1)[1].split(
            "pub fn resource_release_all", 1)[0]
        self.assertIn("RESOURCE_CLAIMS[slot] = resource_invalid_claim()", release)
        self.assertNotIn("RESOURCE_GENERATIONS[slot] = 0", release)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/scripts/validate_i2c_hardware_fixture.py"
FIXTURE = ROOT / "tests/fixtures/i2c_hardware/synthetic_designware.json"

SPEC = importlib.util.spec_from_file_location("i2c_fixture_validator", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class I2cHardwareFixtureValidatorTests(unittest.TestCase):
    def load(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_repository_fixture_is_valid(self):
        MODULE.validate_fixture(self.load())

    def test_synthetic_capture_cannot_claim_physical_success(self):
        data = self.load()
        data["controllers"][0]["observations"]["hid_report"] = "pass"
        with self.assertRaises(MODULE.FixtureError):
            MODULE.validate_fixture(data)

    def test_privacy_sensitive_fields_are_rejected_recursively(self):
        data = self.load()
        data["platform"]["serial_number"] = "must-not-enter-git"
        with self.assertRaises(MODULE.FixtureError):
            MODULE.validate_fixture(data)

    def test_controller_identity_must_be_unique_and_versioned(self):
        data = self.load()
        data["controllers"].append(dict(data["controllers"][0]))
        with self.assertRaises(MODULE.FixtureError):
            MODULE.validate_fixture(data)
        data = self.load()
        data["schema_version"] = 2
        with self.assertRaises(MODULE.FixtureError):
            MODULE.validate_fixture(data)


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"


class StorageNativeReadinessTests(unittest.TestCase):
    def test_generic_readiness_tracks_published_native_block_device(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("pub fn storage_generic_block_io_is_ready() -> bool", 1)[1]
        body = body.split("@system pub fn storage_ahci_total_sectors", 1)[0]
        self.assertIn("STORAGE_BLOCK_DEVICE_READY", body)
        self.assertIn("block_device_has_native_target()", body)
        self.assertNotIn("return STORAGE_GENERIC_BLOCK_IO_READY", body)

    def test_gpt_gate_uses_normal_native_io_readiness(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_probe_backup_gpt_header() -> bool", 1)[1]
        body = body.split("pub fn post_cutover_probe_backup_gpt_entries()", 1)[0]
        self.assertIn("storage_generic_block_io_is_ready()", body)
        self.assertIn("gpt_probe_backup_header()", body)

    def test_fixture_certification_remains_best_effort_and_separate(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        scan = text.split("pub fn storage_discovery_scan() -> u32", 1)[1]
        self.assertIn("if storage_certify_ahci_fixture() { STORAGE_GENERIC_BLOCK_IO_READY = true; }", scan)
        self.assertLess(scan.index("storage_register_ahci_block_device()"), scan.index("storage_certify_ahci_fixture()"))
        self.assertIn("return STORAGE_CONTROLLER_NVME;", scan)


if __name__ == "__main__":
    unittest.main()

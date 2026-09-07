from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/baken_nvme_only.yml"
FIXTURE = ROOT / "tools/scripts/create_foundation_storage_fixture.py"


class NvmeOnlyQemuGateTests(unittest.TestCase):
    def test_workflow_has_only_nvme_storage_media(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        run = text.split("- name: Run NVMe-only Headless QEMU Boot Proof", 1)[1]
        self.assertIn("-drive file=build/nvme-only-test.img,format=raw,if=none,id=nvme_only_disk", run)
        self.assertIn("-device nvme,drive=nvme_only_disk,serial=BAKEN-CI-NVME-ONLY", run)
        self.assertNotIn("storage-test.img", run)
        self.assertNotIn("if=ide,index=0", run)

    def test_workflow_requires_full_bare_metal_proof(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            "extend_foundation_fixture.py",
            "BAKEN:STEP=k",
            "BAKEN:STEP=)",
            "BAKEN:BARE_METAL_READY",
            "BAKEN:STEP=v",
            "BAKENNV1",
        ):
            self.assertIn(token, text)

    def test_fixture_builder_is_regular_file_only_and_places_nvme_sentinel(self):
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("IMAGE_SIZE = 64 * 1024 * 1024", text)
        self.assertIn("with path.open(\"wb\") as image", text)
        self.assertIn("image.write(b\"BAKENNV1\")", text)
        self.assertIn("extend(path)", text)
        for forbidden in ("/dev/", "os.open(", "subprocess", "dd if="):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()

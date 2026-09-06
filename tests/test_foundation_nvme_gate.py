from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
NVME = ROOT / "kernel/src/drivers/nvme.sotlas"
PROBE = ROOT / "kernel/src/storage/foundation_probe.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"
VERIFY = ROOT / "tools/scripts/extend_foundation_fixture.py"


class FoundationNvmeGateTests(unittest.TestCase):
    def test_qemu_uses_separate_real_nvme_fixture(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            "truncate -s 64M build/nvme-test.img",
            "printf 'BAKENNV1' | dd of=build/nvme-test.img bs=512 seek=1024",
            "-drive file=build/nvme-test.img,format=raw,if=none,id=nvme_disk",
            "-device nvme,drive=nvme_disk,serial=BAKEN-CI-NVME",
        ):
            self.assertIn(token, text)

    def test_native_driver_performs_controller_and_namespace_bringup(self):
        text = NVME.read_text(encoding="utf-8")
        body = text.split("pub fn nvme_initialize_first()", 1)[1]
        for token in (
            "(*dev).class_code == 1 && (*dev).subclass == 8 && (*dev).prog_if == 2",
            "nvme_bar_size(dev)",
            "active_page_tables_map_mmio_identity_4k(NVME_BASE)",
            "nvme_wait_ready(0)",
            "dma_alloc_for_device(20480, 4096, 0xFFFFFFFFFFFFFFFF, 0)",
            "dma_share_with_device(&mut arena)",
            "nvme_store64(NVME_BASE + 0x28, NVME_PHYSICAL)",
            "nvme_store64(NVME_BASE + 0x30, NVME_PHYSICAL + 4096)",
            "nvme_wait_ready(1)",
            "nvme_command(0, 6, 0, data, 1, 0, 0)",
            "nvme_command(0, 6, 0, data, 2, 0, 0)",
            "nvme_command(0, 6, NVME_NS, data, 0, 0, 0)",
            "((lbaf >> 16) & 255) != 9",
            "nvme_command(0, 9, 0, 0, 7, 0, 0)",
            "nvme_command(0, 5, 0, NVME_PHYSICAL + 12288",
            "nvme_command(0, 1, 0, NVME_PHYSICAL + 8192",
        ):
            self.assertIn(token, body)

    def test_command_path_tracks_cid_phase_sqid_and_poisoning(self):
        text = NVME.read_text(encoding="utf-8")
        body = text.split("fn nvme_command", 1)[1].split("pub fn nvme_initialize_first", 1)[0]
        for token in (
            "NVME_CID = (NVME_CID + 1) & 0xFFFF",
            "__dma_fence()",
            "(result & 0xFFFF) == cid",
            "(source >> 16) == queue",
            "(source & 0xFFFF) < 16",
            "NVME_HEAD[queue as usize] = (NVME_HEAD[queue as usize] + 1) % 16",
            "NVME_PHASE[queue as usize] = NVME_PHASE[queue as usize] ^ 1",
            "NVME_POISONED = true",
            "NVME_READY = false",
        ):
            self.assertIn(token, body)

    def test_block_device_probe_does_read_write_restore_and_phase_wrap(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("pub fn foundation_nvme_probe()", 1)[1]
        for token in (
            "nvme_initialize_first()",
            "block_device_register_native(BLOCK_DEVICE_NVME, 0, 512, nvme_last_lba(), true, true)",
            "block_device_bind_driver_context(nvme_context())",
            "block_device_read_sector(1024, page.virtual_address)",
            "let expected: [u8; 8] = [66,65,75,69,78,78,86,49]",
            "*last = 0x5A",
            "block_device_write_sector(1024, page.virtual_address as *const u8)",
            "block_device_read_sector(1024, page.virtual_address) && *last == 0x5A",
            "block_device_write_sector(1024, ((page.virtual_address as usize) + 512) as *const u8)",
            "while i < 20 && ok",
            "block_device_register_native(old_kind, old_index, old_size, old_last, old_write, true)",
            "block_device_bind_driver_context(old_context)",
            "x86_serial_write_stage_marker(')' as u8)",
        ):
            self.assertIn(token, body)

    def test_sector_io_is_native_and_write_uses_fua(self):
        text = NVME.read_text(encoding="utf-8")
        read_body = text.split("pub fn nvme_read_sector", 1)[1].split("pub fn nvme_write_sector", 1)[0]
        write_body = text.split("pub fn nvme_write_sector", 1)[1]
        self.assertIn("nvme_command(1, 2, NVME_NS", read_body)
        self.assertIn("nvme_command(1, 1, NVME_NS", write_body)
        self.assertIn("1 << 30", write_body)

    def test_post_cutover_orders_nvme_after_fat_and_before_pat(self):
        text = POST.read_text(encoding="utf-8")
        fat = text.index("foundation_fat_path_probe()")
        nvme = text.index("foundation_nvme_probe()", fat)
        pat = text.index("active_framebuffer_write_combining", nvme)
        self.assertLess(fat, nvme)
        self.assertLess(nvme, pat)

    def test_qemu_verifier_demands_nvme_runtime_marker(self):
        text = VERIFY.read_text(encoding="utf-8")
        self.assertIn("BAKEN:STEP=)", text)


if __name__ == "__main__":
    unittest.main()

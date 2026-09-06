from pathlib import Path
import unittest

from tools.scripts.extend_foundation_fixture import CHAIN, PAYLOAD

ROOT = Path(__file__).resolve().parents[1]
PATH_IMPL = ROOT / "kernel/src/storage/fat32_path.sotlas"
PROBE = ROOT / "kernel/src/storage/foundation_probe.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
FIXTURE = ROOT / "tools/scripts/extend_foundation_fixture.py"


class FoundationFat32PathGateTests(unittest.TestCase):
    def test_fixture_requires_multicluster_directory_lfn_and_file_chain(self):
        self.assertEqual(CHAIN[2], 142)
        self.assertEqual(CHAIN[144], 145)
        self.assertEqual((CHAIN[5], CHAIN[140], CHAIN[7]), (140, 7, 0x0FFFFFFF))
        self.assertEqual(len(PAYLOAD), 1300)
        self.assertNotEqual(5 // 128, 140 // 128)

        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("long_entries('Long sample.txt', alias)", text)
        self.assertIn("put(144, (b'\\xe5' + bytes(31)) * 15 + last)", text)
        self.assertIn("put(145, first + short_entry(alias, 5, len(PAYLOAD)))", text)
        self.assertIn("for i, cluster in enumerate((5, 140, 7))", text)

    def test_lookup_walks_real_fat_chains_and_preserves_lfn_across_boundaries(self):
        text = PATH_IMPL.read_text(encoding="utf-8")
        for token in (
            "fat32_chain_length(directory)",
            "block_device_read_sector(lba, buffer)",
            "cluster = fat32_next_cluster(cluster)",
            "fat_path_checksum(entry)",
            "let mut lfn: [u16; 260]",
            "let offsets: [usize; 13]",
            "lfn_valid && expected == 0",
            "short_matches",
            "fat32_data_cluster_valid(first_cluster)",
            "dma_release(&mut buffer)",
        ):
            self.assertIn(token, text)

        # Absolute paths only; reject dot traversal and trailing slash on files.
        self.assertIn("*path != 47", text)
        self.assertIn("n == 1 && *component == 46", text)
        self.assertIn("n == 2 && *component == 46", text)
        self.assertIn("start == length && (result.attributes & 0x10) == 0", text)

    def test_file_crc_consumes_exact_multicluster_payload(self):
        text = PATH_IMPL.read_text(encoding="utf-8")
        body = text.split("pub fn fat32_file_crc", 1)[1]
        for token in (
            "fat32_chain_length(file.cluster)",
            "while remaining > 0 && ok",
            "block_device_read_sector(base + (sector as u64), buffer.virtual_address)",
            "let take: u64 = if remaining < 512 { remaining } else { 512 }",
            "crc32_ieee_update",
            "cluster = fat32_next_cluster(cluster)",
            "crc32_ieee_finish(crc)",
        ):
            self.assertIn(token, body)

    def test_runtime_probe_requires_long_name_alias_chain_length_crc_and_size(self):
        text = PROBE.read_text(encoding="utf-8")
        body = text.split("pub fn foundation_fat_path_probe()", 1)[1]
        body = body.split("pub fn foundation_nvme_probe()", 1)[0]
        for token in (
            "fat32_lookup(&long_path[0], 26)",
            "fat32_lookup(&short_path[0], 23)",
            "file.cluster != alias.cluster",
            "file.size != alias.size",
            "file.size != 1300",
            "fat32_chain_length(fat32_runtime_root_cluster()) < 2",
            "fat32_chain_length(file.cluster) != 3",
            "fat32_file_crc(file, &mut crc)",
            "x86_serial_write_hex32_marker('+' as u8, crc)",
            "x86_serial_write_hex32_marker('=' as u8, file.size)",
            "x86_serial_write_stage_marker('+' as u8)",
        ):
            self.assertIn(token, body)

    def test_post_cutover_orders_fat_path_after_mbr_and_before_nvme(self):
        text = POST.read_text(encoding="utf-8")
        mbr = text.index("foundation_protective_mbr()")
        fat = text.index("foundation_fat_path_probe()", mbr)
        nvme = text.index("foundation_nvme_probe()", fat)
        self.assertLess(mbr, fat)
        self.assertLess(fat, nvme)

    def test_qemu_verifier_demands_fat32_path_runtime_proof(self):
        text = FIXTURE.read_text(encoding="utf-8")
        self.assertIn("BAKEN:HEX=+:{expected:08X}", text)
        self.assertIn("BAKEN:HEX==:00000514", text)
        self.assertIn("BAKEN:STEP=+", text)


if __name__ == "__main__":
    unittest.main()

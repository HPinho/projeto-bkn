import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAT32 = ROOT / "kernel/src/storage/fat32.sotlas"
WORKFLOW = ROOT / ".github/workflows/baken_ci.yml"


class Fat32RootFileContentRuntimeTests(unittest.TestCase):
    def test_runtime_reads_payload_through_native_block_device(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("fn fat32_probe_root_file_content_runtime(", 1)[1]
        body = body.split("pub fn fat32_probe_esp_bpb()", 1)[0]
        for token in (
            "fat32_runtime_root_file_is_ready()",
            "fat32_runtime_root_file_first_cluster()",
            "fat32_runtime_root_file_size()",
            "block_device_has_native_target()",
            "block_device_read_sector(lba, sector)",
            "let file_lba = data_start_lba + file_index * (sectors_per_cluster as u64)",
        ):
            self.assertIn(token, body)
        self.assertNotIn("BAKENOS", body)

    def test_runtime_crc_covers_exact_file_size_and_validates_chain(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("fn fat32_probe_root_file_content_runtime(", 1)[1]
        body = body.split("pub fn fat32_probe_esp_bpb()", 1)[0]
        for token in (
            "import kernel::storage::crc32::*;",
            "let chain_length = fat32_chain_length(first_cluster);",
            "chain_length != expected_clusters",
            "current_cluster = fat32_next_cluster(current_cluster)",
            "let mut remaining = file_size as u64;",
            "let mut crc = crc32_ieee_begin();",
            "crc32_ieee_update(crc, sector as *const u8, bytes_this_sector as usize)",
            "let computed = crc32_ieee_finish(crc);",
        ):
            self.assertIn(token, text if token.startswith("import ") else body)

    def test_content_state_is_published_before_marker(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("fn fat32_probe_root_file_content_runtime(", 1)[1]
        body = body.split("pub fn fat32_probe_esp_bpb()", 1)[0]
        publish = body.index("FAT32_RUNTIME_ROOT_FILE_CONTENT_READY = true")
        hex_marker = body.index("x86_serial_write_hex32_marker('_' as u8, computed)")
        stage_marker = body.index("x86_serial_write_stage_marker('_' as u8)")
        self.assertLess(publish, hex_marker)
        self.assertLess(hex_marker, stage_marker)
        for token in (
            "pub fn fat32_runtime_root_file_content_is_ready()",
            "pub fn fat32_runtime_root_file_content_bytes()",
            "pub fn fat32_runtime_root_file_content_crc32()",
        ):
            self.assertIn(token, text)

    def test_gate_order_is_root_entry_then_payload(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("pub fn fat32_probe_esp_bpb()", 1)[1]
        entry = body.index("fat32_probe_first_root_file_entry_runtime(")
        content = body.index("fat32_probe_root_file_content_runtime(")
        ready = body.index("fat32_runtime_root_file_content_is_ready()")
        self.assertLess(entry, content)
        self.assertLess(content, ready)

    def test_ci_independently_checks_fixture_crc_and_runtime_marker(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            'file_data[0:8] = b"BAKENOS\\n"',
            "0x68244BD8",
            'BAKEN:HEX=_:68244BD8',
            "STEP=l STEP=_ STEP=m STEP=J",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

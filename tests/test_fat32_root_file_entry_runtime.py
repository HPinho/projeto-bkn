from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAT32 = ROOT / "kernel" / "src" / "storage" / "fat32.sotlas"
WORKFLOW = ROOT / ".github" / "workflows" / "baken_ci.yml"


class Fat32RootFileEntryRuntimeTests(unittest.TestCase):
    def test_runtime_parser_reads_regular_root_entry_metadata(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("fn fat32_probe_first_root_file_entry_runtime(", 1)[1]
        body = body.split("pub fn fat32_probe_esp_bpb()", 1)[0]
        for token in (
            "block_device_read_sector(lba, sector)",
            "attributes != FAT32_ATTR_LONG_NAME",
            "FAT32_ATTR_VOLUME_ID | FAT32_ATTR_DIRECTORY",
            "fat32_read_u16(base, offset + 20)",
            "fat32_read_u16(base, offset + 26)",
            "fat32_read_u32(base, offset + 28)",
            "FAT32_RUNTIME_ROOT_FILE_FIRST_CLUSTER = first_cluster",
            "FAT32_RUNTIME_ROOT_FILE_SIZE = file_size",
            "FAT32_RUNTIME_ROOT_FILE_READY = true",
            "x86_serial_write_stage_marker('l' as u8)",
        ):
            self.assertIn(token, body)
        self.assertNotIn("block_device_write_sector", body)
        self.assertLess(body.index("FAT32_RUNTIME_ROOT_FILE_READY = true"), body.index("x86_serial_write_stage_marker('l' as u8)"))

    def test_parser_is_chained_after_root_directory_gate(self):
        text = FAT32.read_text(encoding="utf-8")
        body = text.split("pub fn fat32_probe_esp_bpb()", 1)[1]
        root = body.index("fat32_probe_root_directory_cluster_runtime(")
        file_entry = body.index("fat32_probe_first_root_file_entry_runtime(")
        ready = body.index("fat32_runtime_root_file_is_ready()")
        self.assertLess(root, file_entry)
        self.assertLess(file_entry, ready)

    def test_ci_fixture_contains_real_regular_file_entry(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for token in (
            'root_dir[0:11] = b"BAKEN   TXT"',
            'root_dir[11] = 0x20',
            'struct.pack_into("<H", root_dir, 26, 3)',
            'struct.pack_into("<I", root_dir, 28, 8)',
            'file_data[0:8] = b"BAKENOS\\n"',
            'STEP=x STEP=o STEP=l STEP=m STEP=J',
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()

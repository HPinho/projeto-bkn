from pathlib import Path
import struct
import unittest
from tools.scripts.extend_foundation_fixture import CHAIN, PAYLOAD, long_entries
from tools.scripts.audit_post_cutover import audit

ROOT = Path(__file__).resolve().parents[1]


class FoundationIntegrationTests(unittest.TestCase):
    def test_fixture_is_fragmented_and_crosses_fat_sector(self):
        self.assertEqual((CHAIN[5], CHAIN[140], CHAIN[7]), (140, 7, 0xFFFFFFF))
        self.assertEqual(len(PAYLOAD), 1300)
        self.assertNotEqual(5 // 128, 140 // 128)
        self.assertEqual(CHAIN[2], 142)

    def test_lfn_fixture_checksum_order_and_padding(self):
        entries = long_entries('Long sample.txt', b'LONGSA~1TXT')
        self.assertEqual([e[0] for e in entries], [0x42, 1])
        self.assertEqual(entries[0][13], entries[1][13])
        units = []
        for entry in reversed(entries):
            units.extend(struct.unpack_from('<H', entry, n)[0] for n in (1,3,5,7,9,14,16,18,20,22,24,28,30))
        self.assertEqual(''.join(chr(n) for n in units[:15]), 'Long sample.txt')
        self.assertEqual(units[15], 0)
        self.assertTrue(all(n == 65535 for n in units[16:]))

    def test_post_cutover_direct_calls_do_not_reenter_firmware(self):
        report = audit()
        self.assertFalse(report['firmware_violations'], report)
        self.assertGreater(report['reachable_functions'], 100)

    def test_nvme_and_memory_gates_remain_real_operations(self):
        probe = (ROOT / 'kernel/src/storage/foundation_probe.sotlas').read_text(encoding='utf-8')
        for token in ('active_runtime_map(', 'active_runtime_unmap(', 'dma_release(',
                      'irq_keyboard_count()', 'block_device_read_sector(', 'block_device_write_sector(',
                      'i < 20 && ok', 'fat32_lookup(', 'fat32_file_crc('):
            self.assertIn(token, probe)
        nvme = (ROOT / 'kernel/src/drivers/nvme.sotlas').read_text(encoding='utf-8')
        for token in ('NVME_PHASE', 'NVME_POISONED = true', '__dma_fence()', 'nvme_wait_ready(0)', 'nvme_wait_ready(1)'):
            self.assertIn(token, nvme)

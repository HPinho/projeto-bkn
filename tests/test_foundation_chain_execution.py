"""Execute the production Sotlas FAT traversal against injected sector reads.

This is not a Python reimplementation of the algorithm: parse the actual
module, emit its functions and link to a tiny hostile-media C harness.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from tools.sotlas_compile import compiler

ROOT = Path(__file__).resolve().parents[1]


class FoundationChainExecutionTests(unittest.TestCase):
    def test_real_sotlas_chain_with_corruption_and_mirror_mismatch(self):
        backend = compiler._bootstrap_backend()
        source = ROOT / 'kernel/src/storage/fat32.sotlas'
        module = backend.parse(source.read_text(encoding='utf-8'), filename=str(source))
        wanted = {'fat32_read_u8', 'fat32_read_u16', 'fat32_read_u32',
                  'fat32_next_cluster', 'fat32_chain_length', 'fat32_data_cluster_valid'}
        module.functions = [fn for fn in module.functions if fn.name in wanted]
        module.imports = []
        module.globals = [g for g in module.globals if g.name in {'FAT32_RESERVED_MIN', 'FAT32_EOC_MIN', 'FAT32_ENTRY_MASK'}]
        prelude = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
static uint8_t disk[2048], a[512], b[512];
bool fat32_runtime_is_ready(void) { return true; }
uint64_t fat32_runtime_cluster_count(void) { return 254; }
uint32_t fat32_runtime_fat_size_sectors(void) { return 2; }
uint64_t fat32_runtime_partition_first_lba(void) { return 0; }
uint32_t fat32_runtime_reserved_sectors(void) { return 0; }
uint64_t fat32_runtime_partition_last_lba(void) { return 3; }
uint8_t *fat32_runtime_sector_buffer(void) { return a; }
uint8_t *fat32_runtime_backup_sector_buffer(void) { return b; }
bool block_device_read_sector(uint64_t lba, uint8_t *out) {
    if (lba > 3) return false;
    memcpy(out, disk + lba * 512, 512); return true;
}
'''
        driver = r'''
static void entry(unsigned cluster, uint32_t value) {
    memcpy(disk + cluster * 4, &value, 4);
    memcpy(disk + 1024 + cluster * 4, &value, 4);
}
int main(void) {
    entry(5, 140); entry(140, 7); entry(7, 0x0fffffff);
    assert(fat32_chain_length(5) == 3);
    entry(7, 5); assert(fat32_chain_length(5) == 0);
    entry(7, 7); assert(fat32_chain_length(5) == 0);
    entry(7, 0x0ffffff7); assert(fat32_chain_length(5) == 0);
    entry(7, 0x0ffffff0); assert(fat32_chain_length(5) == 0);
    entry(7, 1); assert(fat32_chain_length(5) == 0);
    entry(7, 0); assert(fat32_chain_length(5) == 0);
    entry(7, 256); assert(fat32_chain_length(5) == 0);
    entry(7, 0x0fffffff); disk[1024 + 140 * 4] ^= 1;
    assert(fat32_chain_length(5) == 0);
    assert(fat32_chain_length(0) == 0);
    assert(fat32_chain_length(256) == 0);
    entry(140, 7); entry(7, 0xafffffff);
    assert(fat32_chain_length(5) == 3); /* upper nibble reserved */
    return 0;
}
'''
        gcc = compiler.find_gcc(ROOT)
        env = dict(os.environ, PATH=str(gcc.parent) + os.pathsep + os.environ.get('PATH', ''))
        build_dir = ROOT / 'build'
        build_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='fat-chain-', dir=build_dir) as temp:
            path = Path(temp)
            c = path / 'chain.c'
            exe = path / ('chain.exe' if os.name == 'nt' else 'chain')
            c.write_text(prelude + backend.emit_c(module, include_preamble=False) + driver, encoding='utf-8')
            result = subprocess.run([str(gcc), '-std=c11', '-O2', str(c), '-o', str(exe)], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)

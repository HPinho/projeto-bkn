#!/usr/bin/env python3
"""Contratos do disco instalado e da apresentação do instalador Sotlas."""

import importlib.util
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_builder():
    path = ROOT / "tools/scripts/create_installed_disk.py"
    spec = importlib.util.spec_from_file_location("baken_installed_disk", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILDER = load_builder()


class StorageInstallerTests(unittest.TestCase):
    def test_builder_owns_the_bakenfs_layout_contract(self):
        self.assertEqual(BUILDER.DATA_FIRST_LBA, BUILDER.ESP_LAST_LBA + 1)
        self.assertEqual(BUILDER.DATA_FIRST_LBA, 86016)
        self.assertEqual(BUILDER.BAKENFS_MAGIC, b"BAKENFS1")
        self.assertEqual(BUILDER.SECTOR_SIZE, 512)

    def test_builder_initializes_bakenfs_header_preferences_and_notes(self):
        disk = bytearray(BUILDER.TOTAL_SECTORS * BUILDER.SECTOR_SIZE)
        BUILDER.write_baken_data_marker(disk)
        base = BUILDER.DATA_FIRST_LBA * BUILDER.SECTOR_SIZE
        self.assertEqual(bytes(disk[base:base + 8]), BUILDER.BAKENFS_MAGIC)
        version, count = struct.unpack_from("<II", disk, base + 8)
        self.assertEqual((version, count), (1, 4))
        header = bytes(disk[base:base + 512])
        self.assertIn(b"/home/notas.txt", header)
        self.assertIn(b"/config/theme.cfg", header)
        preferences = (BUILDER.DATA_FIRST_LBA + 1) * 512
        self.assertIn(b"Usuario", disk[preferences:preferences + 64])
        notes = (BUILDER.DATA_FIRST_LBA + 2) * 512
        self.assertEqual(struct.unpack_from("<Q", disk, notes)[0], 0x31544E4E454B4142)

    def test_installer_ui_contract_lives_in_sotlas_not_the_compiler(self):
        installer = (ROOT / "kernel/src/baken_installer.sotlas").read_text(encoding="utf-8")
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        for text in (
            "TasteTrack Systems LTDA", "Comecar agora", "Restaurar ou Corrigir Computador",
            "Modo Live RAM", "1. Criando tabela de particoes GPT",
            "2. Formatando volume de dados BakenFS", "3. Instalando microkernel Sotlas",
            "4. Configurando ponto de restauracao",
        ):
            self.assertIn(text, installer)
            self.assertNotIn(text, compiler)

    def test_oobe_navigation_and_continuous_transition_are_native(self):
        oobe = (ROOT / "kernel/src/baken_oobe_screen.sotlas").read_text(encoding="utf-8")
        self.assertIn("oobe_go_to", oobe)
        self.assertIn("transition_tick", oobe)
        self.assertIn("Pronto para Explorar!", oobe)
        self.assertIn("Abrir meu Baken OS", oobe)

    def test_installed_gpt_contract_is_native_and_not_bootloader_owned(self):
        bootloader = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        gpt = (ROOT / "kernel/src/storage/gpt.sotlas").read_text(encoding="utf-8")

        # O loader UEFI não deve mais descobrir ou ler armazenamento. A leitura e
        # validação GPT pertencem ao caminho nativo Block Device pós-cutover.
        for forbidden in (
            "EFI_BLOCK_IO_PROTOCOL",
            "ReadBlocks",
            "find_boot_media",
            "find_install_target",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, bootloader)

        for native in (
            "import kernel::storage::block_device::*;",
            "pub fn gpt_probe_backup_header() -> bool",
            "block_device_read_sector(last_lba, sector)",
            "*sector != ('E' as u8)",
            "pub fn gpt_probe_backup_entries() -> bool",
            "gpt_probe_primary_backup_redundancy(",
            "gpt_partition_is_ready()",
        ):
            with self.subTest(native=native):
                self.assertIn(native, gpt)

        # O formato da imagem instalada continua tendo identidade própria Baken.
        self.assertEqual(str(BUILDER.BAKEN_DATA_GUID), "7f3c7258-2f1c-4e03-bf20-42414b454e31")


if __name__ == "__main__":
    unittest.main()

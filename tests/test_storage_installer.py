#!/usr/bin/env python3
"""Contratos do BakenFS persistente e instalador/particionador UEFI."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class StorageInstallerTests(unittest.TestCase):
    def test_kernel_and_installed_builder_share_the_bakenfs_layout(self):
        bridge_c = (ROOT / "kernel/src/baken_kernel_all.c").read_text(encoding="utf-8")
        disk_builder = (ROOT / "tools/scripts/create_installed_disk.py").read_text(encoding="utf-8")
        self.assertRegex(bridge_c, r"BAKENFS_DATA_LBA\s+86016")
        self.assertIn("BAKENFS_MAGIC", bridge_c)
        self.assertIn("bakenfs_mount", bridge_c)
        self.assertIn("bakenfs_save_preferences", bridge_c)
        self.assertIn("bakenfs_save_notes", bridge_c)
        self.assertIn("DATA_FIRST_LBA = ESP_LAST_LBA + 1", disk_builder)
        self.assertIn('BAKENFS_MAGIC = b"BAKENFS1"', disk_builder)
        self.assertIn('"/home/notas.txt"', disk_builder)

    def test_installer_initializes_bakenfs_data(self):
        bridge_c = (ROOT / "kernel/src/baken_kernel_all.c").read_text(encoding="utf-8")
        self.assertIn("BakenFsHeader", bridge_c)
        self.assertIn("g_bakenfs.magic=BAKENFS_MAGIC", bridge_c)
        self.assertIn("INSTALL_DATA_FIRST+2", bridge_c)
        self.assertIn("/config/theme.cfg", bridge_c)
        self.assertIn("/home/notas.txt", bridge_c)

    def test_sotlas_compile_contains_advanced_partitioner_and_real_installer(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        self.assertIn("BakenPartition", compiler)
        self.assertIn("BakenInstallerState", compiler)
        self.assertIn("installer_apply_default", compiler)
        self.assertIn("installer_add_partition", compiler)
        self.assertIn("installer_delete_partition", compiler)
        self.assertIn("installer_format_partition", compiler)
        self.assertIn("find_boot_file", compiler)
        self.assertIn("installer_execute_installation", compiler)
        self.assertIn("installer_handle_click", compiler)
        self.assertIn("Instalador e Setup - Baken OS", compiler)
        self.assertIn("Volume", compiler)

    def test_sotlas_compile_contains_complete_setup_wizard_stages(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        self.assertIn("INSTALLER_STAGE_WELCOME", compiler)
        self.assertIn("INSTALLER_STAGE_LANGUAGE", compiler)
        self.assertIn("INSTALLER_STAGE_LICENSE", compiler)
        self.assertIn("INSTALLER_STAGE_HARDWARE", compiler)
        self.assertIn("INSTALLER_STAGE_PROFILE", compiler)
        self.assertIn("INSTALLER_STAGE_ACCOUNT", compiler)
        self.assertIn("INSTALLER_STAGE_DISK", compiler)
        self.assertIn("INSTALLER_STAGE_INSTALLING", compiler)
        self.assertIn("INSTALLER_STAGE_COMPLETE", compiler)
        self.assertIn("INSTALLER_STAGE_REPAIR", compiler)
        self.assertIn("installer_next_stage", compiler)
        self.assertIn("installer_prev_stage", compiler)
        self.assertIn("installer_select_option", compiler)
        self.assertIn("installer_execute_repair", compiler)

    def test_bakenfs_contains_profile_user_and_snapshot_structures(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        self.assertIn("SotlasProfileConfig", compiler)
        self.assertIn("SotlasUserConfig", compiler)
        self.assertIn("SotlasSnapshotMeta", compiler)
        self.assertIn("/config/profile.cfg", compiler)
        self.assertIn("/config/user.cfg", compiler)
        self.assertIn("/config/snapshot.meta", compiler)

    def test_bootloader_recognizes_installed_gpt_as_its_own_boot_media(self):
        bootloader = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        self.assertIn("GUID de tipo Baken Data", bootloader)
        self.assertIn("sector[0]!='E'", bootloader)
        self.assertIn("data_guid", bootloader)

    def test_installer_presentation_benchmark_and_oobe_contracts(self):
        compiler = (ROOT / "tools/sotlas_compile/compiler.py").read_text(encoding="utf-8")
        installer = (ROOT / "kernel/src/baken_installer.sotlas").read_text(encoding="utf-8")
        oobe = (ROOT / "kernel/src/baken_oobe_screen.sotlas").read_text(encoding="utf-8")
        # Apresentação e TasteTrack Systems
        self.assertIn("TasteTrack Systems LTDA", installer)
        self.assertIn("Comecar agora", installer)
        self.assertIn("Restaurar ou Corrigir Computador", installer)
        # Escolha de modo nativa
        self.assertIn("Teste de Desempenho e Telemetria de Hardware", installer)
        self.assertIn("Modo Live RAM", installer)
        # Benchmark com medições dinâmicas e nota calculada
        self.assertIn("st_rdtsc", compiler)
        self.assertIn("st_cpuid", compiler)
        self.assertIn("installer_run_hardware_benchmark", compiler)
        # Proteção estrita da mídia de boot
        self.assertIn("Protecao ativa", compiler)
        self.assertIn("boot_disk_is_protected", compiler)
        # 4 passos nativos de instalação
        self.assertIn("1. Criando tabela de particoes GPT", installer)
        self.assertIn("2. Formatando volume de dados BakenFS", installer)
        self.assertIn("3. Instalando microkernel Sotlas", installer)
        self.assertIn("4. Configurando ponto de restauracao", installer)
        # OOBE nativo, com navegação e transição contínua
        self.assertIn("oobe_go_to", oobe)
        self.assertIn("transition_tick", oobe)
        self.assertIn("Pronto para Explorar!", oobe)
        self.assertIn("Abrir meu Baken OS", oobe)


if __name__ == "__main__":
    unittest.main()

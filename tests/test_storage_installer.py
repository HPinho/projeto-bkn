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

    def test_vortexc_contains_advanced_partitioner_and_real_installer(self):
        vortexc_py = (ROOT / "tools/vortexc/vortexc.py").read_text(encoding="utf-8")
        self.assertIn("BakenPartition", vortexc_py)
        self.assertIn("BakenInstallerState", vortexc_py)
        self.assertIn("installer_apply_default", vortexc_py)
        self.assertIn("installer_add_partition", vortexc_py)
        self.assertIn("installer_delete_partition", vortexc_py)
        self.assertIn("installer_format_partition", vortexc_py)
        self.assertIn("find_boot_file", vortexc_py)
        self.assertIn("installer_execute_installation", vortexc_py)
        self.assertIn("installer_handle_click", vortexc_py)
        self.assertIn("Instalador e Setup - Baken OS Sovereign", vortexc_py)
        self.assertIn("Volume", vortexc_py)

    def test_vortexc_contains_complete_setup_wizard_stages(self):
        vortexc_py = (ROOT / "tools/vortexc/vortexc.py").read_text(encoding="utf-8")
        self.assertIn("INSTALLER_STAGE_WELCOME", vortexc_py)
        self.assertIn("INSTALLER_STAGE_LANGUAGE", vortexc_py)
        self.assertIn("INSTALLER_STAGE_LICENSE", vortexc_py)
        self.assertIn("INSTALLER_STAGE_HARDWARE", vortexc_py)
        self.assertIn("INSTALLER_STAGE_PROFILE", vortexc_py)
        self.assertIn("INSTALLER_STAGE_ACCOUNT", vortexc_py)
        self.assertIn("INSTALLER_STAGE_DISK", vortexc_py)
        self.assertIn("INSTALLER_STAGE_INSTALLING", vortexc_py)
        self.assertIn("INSTALLER_STAGE_COMPLETE", vortexc_py)
        self.assertIn("INSTALLER_STAGE_REPAIR", vortexc_py)
        self.assertIn("installer_next_stage", vortexc_py)
        self.assertIn("installer_prev_stage", vortexc_py)
        self.assertIn("installer_select_option", vortexc_py)
        self.assertIn("installer_execute_repair", vortexc_py)

    def test_bakenfs_contains_profile_user_and_snapshot_structures(self):
        vortexc_py = (ROOT / "tools/vortexc/vortexc.py").read_text(encoding="utf-8")
        self.assertIn("CqProfileConfig", vortexc_py)
        self.assertIn("CqUserConfig", vortexc_py)
        self.assertIn("CqSnapshotMeta", vortexc_py)
        self.assertIn("/config/profile.cfg", vortexc_py)
        self.assertIn("/config/user.cfg", vortexc_py)
        self.assertIn("/config/snapshot.meta", vortexc_py)

    def test_bootloader_recognizes_installed_gpt_as_its_own_boot_media(self):
        bootloader = (ROOT / "boot/uefi_bootloader.st").read_text(encoding="utf-8")
        self.assertIn("GUID de tipo Baken Data", bootloader)
        self.assertIn("sector[0]!='E'", bootloader)
        self.assertIn("data_guid", bootloader)


if __name__ == "__main__":
    unittest.main()


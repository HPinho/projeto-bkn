#!/usr/bin/env python3
"""Verifica contratos da mídia UEFI sem gerar uma ISO ou disco no workspace."""

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fat_disk = load("create_fat32_img", "tools/scripts/create_fat32_img.py")
optical_iso = load("create_uefi_iso", "tools/scripts/create_uefi_iso.py")


class PackagingContractTests(unittest.TestCase):
    def test_optical_esp_contains_bootx64_without_writing_media(self):
        image = optical_iso.create_fat_efi_img(b"MZ" + b"\0" * 2048)
        # A ESP óptica comporta os atlas Inter/Material de alta densidade.
        self.assertEqual(len(image), 12 * 1024 * 1024)
        self.assertEqual(image[54:62], b"FAT12   ")
        self.assertIn(b"EFI        ", image)
        self.assertIn(b"BOOTX64 EFI", image)

    def test_optical_esp_refuses_an_empty_or_oversized_efi_image(self):
        with self.assertRaises(ValueError):
            optical_iso.create_fat_efi_img(b"")
        with self.assertRaisesRegex(ValueError, "excede a capacidade"):
            optical_iso.create_fat_efi_img(b"MZ" + b"\0" * 13_000_000)

    def test_packagers_require_a_real_efi_binary(self):
        missing = ROOT / "build" / "definitely-missing-bootx64.efi"
        output = ROOT / "build" / "packaging-contract-output-does-not-exist.img"
        self.assertFalse(output.exists())
        with self.assertRaises(FileNotFoundError):
            fat_disk.create_esp_disk_image(str(output), str(missing))
        with self.assertRaises(FileNotFoundError):
            optical_iso.build_uefi_iso(str(output), str(missing))
        self.assertFalse(output.exists())

    def test_disk_builder_reserves_the_raw_install_record_cluster(self):
        self.assertEqual(fat_disk.INSTALL_RECORD_LBA, 8192)
        builder = (ROOT / "tools/scripts/create_fat32_img.py").read_text(encoding="utf-8")
        self.assertIn("reserve_raw_lba(INSTALL_RECORD_LBA)", builder)

    def test_launchers_do_not_confuse_disk_and_optical_media(self):
        iso_launcher = (ROOT / "run_baken_iso.ps1").read_text(encoding="utf-8")
        disk_launcher = (ROOT / "run_baken.ps1").read_text(encoding="utf-8")
        vbox_launcher = (ROOT / "run_baken_vbox.ps1").read_text(encoding="utf-8")
        self.assertIn("media=cdrom,readonly=on,file=$iso", iso_launcher)
        self.assertIn("create_fat32_img.py", vbox_launcher)
        self.assertNotIn("virtio-net-pci", disk_launcher)
        self.assertIn('"-smp", "1"', iso_launcher)
        self.assertIn('$ErrorActionPreference = "Stop"', disk_launcher)
        self.assertIn("FAT16 de teste", disk_launcher)
        self.assertNotIn("- pulando.", disk_launcher)
        qemu_test = (ROOT / "tools/test_qemu_desktop.py").read_text(encoding="utf-8")
        self.assertIn('"-smp", "1"', qemu_test)
        self.assertIn('media.add_argument("--iso"', qemu_test)
        self.assertIn('media.add_argument("--installed"', qemu_test)
        self.assertIn('parser.add_argument("--target"', qemu_test)
        self.assertIn('mode.add_argument("--installer"', qemu_test)
        self.assertIn("add_mutually_exclusive_group", qemu_test)
        self.assertIn("media=cdrom,readonly=on", qemu_test)
        self.assertIn("framebuffer_has_color", qemu_test)

    def test_installed_disk_builder_is_safe_and_uses_gpt_fat32(self):
        builder = (ROOT / "tools/scripts/create_installed_disk.py").read_text(encoding="utf-8")
        self.assertIn("assert_build_output", builder)
        self.assertIn('b"EFI PART"', builder)
        self.assertIn('b"FAT32   "', builder)
        self.assertIn("BAKENFS_MAGIC", builder)
        self.assertIn("/home/notas.txt", builder)

    def test_virtualbox_launcher_is_isolated_from_personal_vms(self):
        vbox_launcher = (ROOT / "run_baken_vbox.ps1").read_text(encoding="utf-8")
        self.assertIn('"BakenOS-MVP-Test"', vbox_launcher)
        self.assertNotIn("Get-Process *virtualboxvm*", vbox_launcher)
        self.assertNotIn('match \'"(BakenOS', vbox_launcher)

    def test_virtualbox_automated_test_runner_contract(self):
        vbox_test = (ROOT / "tools/test_vbox_desktop.py").read_text(encoding="utf-8")
        self.assertIn('f"BakenOS-AutoTest-{RUN_ID}"', vbox_test)
        self.assertIn("uuid.uuid4", vbox_test)
        self.assertIn('"--basefolder", str(TEST_VM_ROOT)', vbox_test)
        self.assertIn('env["VBOX_USER_HOME"]', vbox_test)
        self.assertIn('"screenshotpng"', vbox_test)
        self.assertIn('"headless"', vbox_test)
        self.assertIn("convertfromraw", vbox_test)

    def test_parallel_unsafe_vm_launchers_are_absent(self):
        self.assertFalse((ROOT / "test_in_virtualbox.ps1").exists())
        self.assertFalse((ROOT / "tools/test_fat16_boot.py").exists())
        self.assertFalse((ROOT / "tools/scripts/run_qemu.py").exists())

    def test_uefi_build_delegates_to_vortexc_with_checked_bare_metal_flags(self):
        build = (ROOT / "tools/build_uefi_desktop.ps1").read_text(encoding="utf-8")
        vortex = (ROOT / "tools/vortexc/vortexc.py").read_text(encoding="utf-8")
        self.assertIn("$vortex", build)
        self.assertIn("kernel\\src\\main.cq", build)
        self.assertIn("generate_baken_app_icons.py", build)
        self.assertIn("baken_app_icons_atlas.h", build)
        self.assertIn("generate_motion_icons.py", build)
        self.assertIn("baken_motion_icons_atlas.h", build)
        self.assertIn('"-fshort-wchar"', vortex)
        self.assertIn('"-mno-red-zone"', vortex)
        self.assertLess(build.index("param("), build.index('$ErrorActionPreference = "Stop"'))
        vbox = (ROOT / "run_baken_vbox.ps1").read_text(encoding="utf-8")
        self.assertLess(vbox.index("param("), vbox.index('$ErrorActionPreference = "Stop"'))


if __name__ == "__main__":
    unittest.main()

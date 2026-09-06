#!/usr/bin/env python3
"""Gate que impede a volta do runtime híbrido/firmware."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class FoundationLegacyRuntimeRetirementGateTests(unittest.TestCase):
    def test_compatibility_runtime_was_deleted(self):
        self.assertFalse((ROOT / "kernel/src/baken_runtime.sotlas").exists())

    def test_kernel_and_compiler_have_no_legacy_runtime_aliases(self):
        paths = list((ROOT / "kernel").rglob("*.sotlas")) + [
            ROOT / "tools/sotlas_compile/compiler.py", ROOT / "tools/sotlas_compile/bootstrap.py"
        ]
        code = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for forbidden in ("baken_efi_", "baken_runtime_run", "baken_runtime_init_assets", "baken_kernel_main"):
            with self.subTest(forbidden=forbidden): self.assertNotIn(forbidden, code)

    def test_bootstrap_loader_stays_out_of_input_and_storage_discovery(self):
        text = (ROOT / "boot/uefi_bootloader.sotlas").read_text(encoding="utf-8")
        for forbidden in ("EFI_SIMPLE_POINTER_PROTOCOL_GUID", "EFI_ABSOLUTE_POINTER_PROTOCOL_GUID",
                          "EFI_BLOCK_IO_PROTOCOL", "ReadBlocks", "find_boot_media", "find_install_target"):
            with self.subTest(forbidden=forbidden): self.assertNotIn(forbidden, text)
        self.assertIn("baken_exit_boot_services_final(", text)

if __name__ == "__main__": unittest.main()

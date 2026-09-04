#!/usr/bin/env python3
"""Guardrails para impedir progresso/sucesso fictício no instalador."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "kernel/src/install_engine.sotlas"
BLOCK = ROOT / "kernel/src/storage/block_device.sotlas"
COMPOSITOR = ROOT / "kernel/src/desktop_compositor.sotlas"
INSTALLER = ROOT / "kernel/src/baken_installer.sotlas"


class InstallEngineTests(unittest.TestCase):
    def test_engine_refuses_install_without_native_writable_storage(self):
        text = ENGINE.read_text(encoding="utf-8")
        self.assertIn("block_device_has_writable_native_target()", text)
        self.assertIn("INSTALL_STATE = INSTALL_STATE_UNAVAILABLE", text)
        self.assertIn("return false;", text)

    def test_engine_has_no_frame_counted_progress(self):
        text = ENGINE.read_text(encoding="utf-8")
        self.assertNotIn("INSTALL_PROGRESS +=", text)
        self.assertNotIn("INSTALL_PROGRESS++", text)
        self.assertNotIn("frame_delta", text)
        self.assertNotIn("anim_tick", text)

    def test_block_registry_requires_real_native_io_ready(self):
        text = BLOCK.read_text(encoding="utf-8")
        self.assertIn("BLOCK_NATIVE_IO_READY", text)
        self.assertIn("if (block_size == 0 || last_lba == 0 || !io_ready)", text)
        self.assertIn("BLOCK_DEVICE_AHCI", text)
        self.assertIn("BLOCK_DEVICE_NVME", text)

    def test_canonical_compositor_never_ticks_legacy_fake_progress(self):
        compositor = COMPOSITOR.read_text(encoding="utf-8")
        self.assertIn("install_engine_tick();", compositor)
        self.assertNotIn("baken_installer_tick();", compositor)

        # O helper legado ainda existe nesta etapa apenas para permitir uma
        # remoção incremental do arquivo de UI, mas não pode ganhar outro caller.
        installer = INSTALLER.read_text(encoding="utf-8")
        self.assertIn("pub fn baken_installer_tick()", installer)


if __name__ == "__main__":
    unittest.main()

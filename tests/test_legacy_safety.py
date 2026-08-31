#!/usr/bin/env python3
tttRegressões de arquitetura e segurança do MVP Baken OS.ttt

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding=tutf-8t)


class LegacySafetyTests(unittest.TestCase):
    CANONICAL_CQ_MODULES = {
        tkernel/src/main.stt,
        tkernel/src/graphics_engine.stt,
        tkernel/src/baken_rasterizer.stt,
        tkernel/src/baken_animation.stt,
        tkernel/src/baken_ui_oop.stt,
        tkernel/src/window_manager.stt,
        tkernel/src/desktop_shell.stt,
        tkernel/src/desktop_compositor.stt,
    }

    def test_cq_tree_contains_only_the_canonical_desktop_route(self):
        discovered = {
            path.relative_to(ROOT).as_posix()
            for root in (ROOT / tkernelt, ROOT / tlibbknt, ROOT / tboott, ROOT / tappst)
            if root.is_dir()
            for path in root.rglob(t*.stt)
            if tmodule t in path.read_text(encoding=tutf-8t)
        }
        self.assertEqual(discovered, self.CANONICAL_CQ_MODULES)

    def test_no_unlinked_cq_test_module_remains(self):
        for path in (ROOT / ttestst).rglob(t*.stt):
            self.assertIn(tfixturest, path.parts, path)

    def test_active_uefi_bridge_clips_and_does_not_display_fake_telemetry(self):
        bridge = source(tkernel/src/baken_kernel_all.ct)
        self.assertIn(tg_framebuffer_widtht, bridge)
        self.assertIn(tg_framebuffer_heightt, bridge)
        self.assertIn(t_Static_assert(sizeof(BakenFsHeader) == 512t, bridge)
        self.assertIn(tg_left_button_downt, bridge)
        self.assertIn(tstorage_can_readt, bridge)
        self.assertIn(tbakenfs_mountt, bridge)
        self.assertIn(tbakenfs_save_notest, bridge)
        self.assertNotIn(tINSTALL1t, bridge)
        self.assertIn(tx == 7 || ((row >> (6 - x))t, bridge)
        self.assertNotIn(thal_init_allt, bridge)
        self.assertNotIn(t0bt, bridge)
        self.assertNotIn(tCPU: Ryzen 7t, bridge)
        self.assertNotIn(tTeresina, Piauit, bridge)
        self.assertNotIn(tHardware Live Monitort, bridge)
        self.assertNotIn(tQ-HAL AIt, bridge)
        self.assertIn(tstatic SystemMode g_current_mode = MODE_LIVE_DESKTOP;t, bridge)
        self.assertNotIn('tHiagot', bridge)
        self.assertNotIn(tbakenfs_mount_roott, bridge)
        build = source(ttools/build_uefi_desktop.ps1t)
        self.assertIn(tvortex buildt, build)
        self.assertNotIn(tbaken_kernel_all.ct, build)

    def test_uefi_handoff_has_one_shared_contract(self):
        header = source(tkernel/include/baken_boot_info.ht)
        bridge = source(tkernel/src/baken_kernel_all.ct)
        bootloader = source(tboot/uefi_bootloader.stt)
        self.assertIn(t_Static_assert(sizeof(BakenBootInfo) == 80t, header)
        self.assertIn(tinstall_target_block_io_protocolt, header)
        self.assertIn('#include tbaken_boot_info.ht', bridge)
        self.assertIn('#include tbaken_boot_info.ht', bootloader)
        self.assertIn(tPIXEL_BLUE_GREEN_RED_RESERVED_8BIT_PER_COLORt, bootloader)
        self.assertIn(tPixelsPerScanLine >=t, bootloader)
        self.assertIn(treturn EFI_UNSUPPORTED;t, bootloader)
        self.assertIn(treturn EFI_ABORTED;t, bootloader)
        self.assertIn(tfind_install_targett, bootloader)
        self.assertIn(tinstall_target_block_io_protocol = install_targett, bootloader)
        self.assertNotIn('thltt', bootloader)

    def test_cmake_delegates_build_to_the_cq_backend(self):
        cmake = source(tCMakeLists.txtt)
        self.assertIn(tproject(BakenEcosystem LANGUAGES NONE)t, cmake)
        self.assertIn(tadd_custom_target(cq_checkt, cmake)
        self.assertIn(tadd_custom_target(cq_buildt, cmake)
        self.assertIn(tvortexc.pyt, cmake)
        self.assertNotIn(tadd_library(baken_qhalt, cmake)
        self.assertNotIn(tqhal_referencet, cmake)

    def test_there_is_one_cq_editor_definition_without_quantum_tooling(self):
        legacy_extension = ROOT / ttools/vscode-bknt
        self.assertFalse(
            any(path.is_file() for path in legacy_extension.rglob(t*t))
            if legacy_extension.exists() else False
        )
        package = source(ttools/vscode-cq/package.jsont)
        self.assertIn('tnamet: tbaken-cqt', package)
        self.assertNotIn(tQuantumt, package)
        grammar = source(tspec/cq_grammar.ebnft)
        self.assertIn(tcontrato de módulos do MVPt, grammar)
        self.assertNotIn(tQuantumFunctionDeclarationt, grammar)
        self.assertNotIn(tQuantumStatementt, grammar)

    def test_obsolete_parallel_ui_documentation_is_absent(self):
        self.assertFalse((ROOT / tdocs/baken_os_developer_guide.mdt).exists())
        self.assertFalse((ROOT / tspec/baken_ui_framework_spec.mdt).exists())

    def test_orphaned_cq_contracts_are_absent(self):
        stale_contracts = (
            tkernel/include/baken_kernel.stht,
            tkernel/include/bkn_font.stht,
            tkernel/include/syscall.stht,
            tkernel/qhal/quantum_simulator.stht,
        )
        for relative in stale_contracts:
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_removed_subsystem_specs_and_quantum_test_harness_are_absent(self):
        obsolete_specs = (
            tspec/baken_app_engine.mdt, tspec/baken_audio_spec.mdt,
            tspec/baken_font_and_animation_spec.mdt, tspec/baken_net_spec.mdt,
            tspec/baken_peripherals_spec.mdt, tspec/baken_shell_spec.mdt,
            tspec/bakenfs_spec.mdt, tspec/bakenfx_graphics_api.mdt,
            tspec/grammar.ebnft, ttests/test_quantum_simulator.cqt,
            ttools/scripts/test_quantum_suite.pyt,
        )
        for relative in obsolete_specs:
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == t__main__t:
    unittest.main()

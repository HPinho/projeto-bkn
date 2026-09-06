#!/usr/bin/env python3
"""Guardrails do discovery PCI, probe MMIO, reset, DMA, IDENTIFY e READ AHCI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISCOVERY = ROOT / "kernel/src/drivers/storage_discovery.sotlas"
AHCI_RUNTIME = ROOT / "kernel/src/drivers/ahci_runtime.sotlas"
AHCI_READ = ROOT / "kernel/src/drivers/ahci_block_read.sotlas"
POST = ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas"
ENGINE = ROOT / "kernel/src/install_engine.sotlas"


class StorageDiscoveryTests(unittest.TestCase):
    def test_ahci_and_nvme_class_tuples_are_explicit(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        for token in (
            "PCI_CLASS_MASS_STORAGE: u8 = 0x01",
            "PCI_SUBCLASS_SATA: u8 = 0x06",
            "PCI_PROGIF_AHCI: u8 = 0x01",
            "PCI_SUBCLASS_NVM: u8 = 0x08",
            "PCI_PROGIF_NVME: u8 = 0x02",
        ):
            self.assertIn(token, text)

    def test_bar_choice_matches_controller_abi(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        self.assertIn("(*dev).bars[5].base_address", text)
        self.assertIn("(*dev).bars[0].base_address", text)

    def test_mmio_probe_only_enables_memory_space_and_preserves_bus_master(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("fn storage_probe_mmio_after_cutover()", 1)[1]
        body = body.split("fn storage_reset_ahci_after_probe()", 1)[0]
        self.assertIn("active_page_tables_is_ready()", body)
        self.assertIn("PCI_COMMAND_MEMORY_SPACE", body)
        self.assertIn("pci_enable_command_bits", body)
        self.assertIn("PCI_COMMAND_BUS_MASTER", body)
        self.assertIn("command_before", body)
        self.assertIn("command_after", body)
        self.assertNotIn("PCI_COMMAND_MEMORY_SPACE | PCI_COMMAND_BUS_MASTER", body)
        self.assertNotIn("pci_enable_device", body)
        self.assertNotIn("block_device_register_native", body)

    def test_mmio_probe_maps_uc_identity_and_reads_structural_registers(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        for token in (
            "active_page_tables_map_mmio_identity_4k",
            "AHCI_REG_CAP", "AHCI_REG_GHC", "AHCI_REG_PI", "AHCI_REG_VS",
            "NVME_REG_CAP_LO", "NVME_REG_CAP_HI", "NVME_REG_VS", "NVME_REG_CSTS",
            "x86_mmio_read32", "STORAGE_MMIO_READY = true",
            "x86_serial_write_stage_marker('a' as u8)",
        ):
            self.assertIn(token, text)

    def test_no_reset_or_dma_in_mmio_stage(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("fn storage_probe_mmio_after_cutover()", 1)[1]
        body = body.split("fn storage_reset_ahci_after_probe()", 1)[0]
        code = "\n".join(line.split("//", 1)[0] for line in body.splitlines())
        for forbidden in ("dma_alloc", "AHCI_GHC_HR", "block_device_register_native"):
            self.assertNotIn(forbidden, code)

    def test_ahci_reset_is_global_real_masked_and_dma_free(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("fn storage_reset_ahci_after_probe()", 1)[1]
        body = body.split("fn storage_prepare_ahci_dma_after_reset()", 1)[0]
        for token in (
            "STORAGE_CONTROLLER_AHCI", "AHCI_GHC_HR", "AHCI_GHC_IE", "AHCI_GHC_AE",
            "AHCI_RESET_SPIN_LIMIT", "x86_mmio_write32(base + AHCI_REG_GHC",
            "STORAGE_AHCI_RESET_READY = true", "x86_serial_write_stage_marker('b' as u8)",
        ):
            self.assertIn(token, body)
        for forbidden in ("PCI_COMMAND_BUS_MASTER", "dma_alloc", "block_device_register_native"):
            self.assertNotIn(forbidden, body)

    def test_ahci_dma_runtime_uses_real_pmm_dma_and_programs_port_tables(self):
        text = AHCI_RUNTIME.read_text(encoding="utf-8")
        body = text.split("pub fn ahci_runtime_prepare_dma", 1)[1]
        body = body.split("pub fn ahci_runtime_identify_device", 1)[0]
        for token in (
            "dma_alloc(", "dma_share_with_device", "PCI_COMMAND_BUS_MASTER",
            "AHCI_PX_CLB", "AHCI_PX_FB", "AHCI_PX_CMD", "AHCI_PX_CI",
            "AHCI_COMMAND_LIST_PAGE", "AHCI_RECEIVED_FIS_PAGE", "AHCI_COMMAND_TABLE_PAGE",
            "ahci_runtime_write64_pair", "x86_serial_write_stage_marker('c' as u8)",
        ):
            self.assertIn(token, body)
        self.assertIn("*header = 5", body)
        self.assertIn("ctba_low", body)
        self.assertIn("ctba_high", body)

    def test_ahci_dma_gate_keeps_command_engine_stopped_and_submits_no_ata(self):
        text = AHCI_RUNTIME.read_text(encoding="utf-8")
        body = text.split("pub fn ahci_runtime_prepare_dma", 1)[1]
        body = body.split("pub fn ahci_runtime_identify_device", 1)[0]
        code = "\n".join(line.split("//", 1)[0] for line in body.splitlines())
        self.assertIn("AHCI_PXCMD_ST", code)
        self.assertIn("AHCI_PXCMD_FRE", code)
        self.assertIn("AHCI_PXCMD_CR", code)
        self.assertIn("AHCI_PXCMD_FR", code)
        self.assertIn("ci_verify == 0xFFFFFFFF", code)
        self.assertIn("ci_verify != 0", code)
        self.assertNotIn("AHCI_ATA_IDENTIFY_DEVICE", code)
        self.assertNotIn("x86_mmio_write32(port_base + AHCI_PX_CI, 1)", code)

    def test_identify_uses_real_h2d_fis_prdt_and_completion_poll(self):
        text = AHCI_RUNTIME.read_text(encoding="utf-8")
        body = text.split("pub fn ahci_runtime_identify_device", 1)[1]
        for token in (
            "AHCI_ATA_IDENTIFY_DEVICE: u8 = 0xEC",
            "AHCI_FIS_TYPE_REG_H2D: u8 = 0x27",
            "AHCI_IDENTIFY_DATA_PAGE",
            "AHCI_PX_TFD", "AHCI_PX_IS", "AHCI_PX_CI",
            "AHCI_PXIS_TFES", "AHCI_TFD_BSY", "AHCI_TFD_DRQ", "AHCI_TFD_ERR",
            "x86_mmio_write32(port_base + AHCI_PX_CI, 1)",
            "AHCI_IDENTIFY_READY = true",
            "x86_serial_write_stage_marker('d' as u8)",
        ):
            self.assertIn(token, text if token.startswith("AHCI_") and ":" in token else body)
        self.assertIn("(511 as u32) | (1 << 31)", body)
        self.assertIn("if word0 == 0 || word0 == 0xFFFF", body)
        self.assertNotIn("ATA_CMD_WRITE", body)
        self.assertNotIn("block_device_register_native", body)

    def test_runtime_selects_connected_ata_port_not_atapi_cdrom(self):
        text = AHCI_RUNTIME.read_text(encoding="utf-8")
        body = text.split("fn ahci_runtime_first_ata_port", 1)[1]
        body = body.split("fn ahci_runtime_stop_port", 1)[0]
        for token in (
            "AHCI_PX_SSTS", "AHCI_PX_SIG", "AHCI_SIG_ATA",
            "AHCI_SSTS_DET_PRESENT", "AHCI_SSTS_IPM_ACTIVE",
        ):
            self.assertIn(token, body)

    def test_signature_requires_bound_receive_engine_after_reset(self):
        text = AHCI_RUNTIME.read_text(encoding="utf-8")
        body = text.split("fn ahci_runtime_first_ata_port", 1)[1]
        body = body.split("fn ahci_runtime_wait_ata_port", 1)[0]
        self.assertLess(body.index("ahci_runtime_bind_dma_port(port)"),
                        body.index("cmd | AHCI_PXCMD_FRE"))
        self.assertLess(body.index("cmd | AHCI_PXCMD_FRE"),
                        body.index("base + AHCI_PX_SIG"))
        self.assertIn("ahci_runtime_stop_port(base)", body)
        wait = text.split("fn ahci_runtime_wait_ata_port", 1)[1]
        wait = wait.split("fn ahci_runtime_stop_port", 1)[0]
        self.assertNotIn("while", wait)

    def test_shared_arena_stops_previous_port_before_rebinding(self):
        text = AHCI_RUNTIME.read_text(encoding="utf-8")
        body = text.split("fn ahci_runtime_bind_dma_port", 1)[1]
        body = body.split("pub fn ahci_runtime_prepare_dma", 1)[0]
        self.assertLess(body.index("port != AHCI_RUNTIME_PORT"),
                        body.index("ahci_runtime_write64_pair"))
        self.assertLess(body.index("ahci_runtime_stop_port"),
                        body.index("ahci_runtime_write64_pair"))

    def test_identify_capacity_uses_lba48_then_lba28_fallback(self):
        text = AHCI_READ.read_text(encoding="utf-8")
        body = text.split("pub fn ahci_parse_identify_capacity", 1)[1]
        body = body.split("fn ahci_read_prepare_buffer", 1)[0]
        for token in (
            "ahci_identify_data_physical", "AHCI_IDENTIFY_WORD_LBA_SUPPORT",
            "AHCI_IDENTIFY_WORD_LBA28_LO", "AHCI_IDENTIFY_WORD_LBA48_FEATURES",
            "AHCI_IDENTIFY_WORD_LBA48_LO", "word83_valid", "w100", "w101",
            "w102", "w103", "total48", "w60", "w61", "total28",
            "AHCI_TOTAL_SECTORS",
        ):
            self.assertIn(token, body)
        self.assertLess(body.index("total48"), body.index("total28"))

    def test_read_uses_dedicated_shared_dma_buffer_and_preserves_identify(self):
        text = AHCI_READ.read_text(encoding="utf-8")
        prep = text.split("fn ahci_read_prepare_buffer", 1)[1]
        prep = prep.split("fn ahci_read_magic_matches", 1)[0]
        for token in ("dma_alloc(", "dma_buffer_cpu_owned", "dma_share_with_device", "AHCI_READ_BUFFER"):
            self.assertIn(token, prep)
        body = text.split("pub fn ahci_read_probe_sector0", 1)[1]
        self.assertIn("AHCI_READ_BUFFER.physical_address", body)
        self.assertIn("AHCI_READ_BUFFER.virtual_address", body)
        self.assertNotIn("ahci_identify_data_physical", body)

    def test_first_sector_read_is_real_dma_and_validates_fixture_magic(self):
        text = AHCI_READ.read_text(encoding="utf-8")
        body = text.split("pub fn ahci_read_probe_sector0", 1)[1]
        for token in (
            "AHCI_ATA_READ_DMA_EXT: u8 = 0x25",
            "AHCI_ATA_READ_DMA: u8 = 0xC8",
            "AHCI_FIS_TYPE_REG_H2D", "AHCI_PX_TFD", "AHCI_PX_IS", "AHCI_PX_CI",
            "AHCI_PXIS_TFES", "AHCI_TFD_BSY", "AHCI_TFD_DRQ", "AHCI_TFD_ERR",
            "ahci_read_prepare_buffer", "ahci_runtime_command_list_physical",
            "ahci_runtime_command_table_physical", "ahci_block_virtual",
            "x86_mmio_write32(port_base + AHCI_PX_CI, 1)",
            "prdbc != (AHCI_READ_SECTOR_SIZE as u32)",
            "ahci_read_magic_matches", "AHCI_READ_READY = true",
            "x86_serial_write_stage_marker('e' as u8)",
        ):
            self.assertIn(token, text if token.startswith("AHCI_ATA_") else body)
        self.assertIn("(511 as u32) | (1 << 31)", body)
        self.assertIn("*(((table as usize) + 12) as *mut u8) = 1", body)
        self.assertNotIn("block_device_register_native", body)
        self.assertNotIn("AHCI_ATA_WRITE", body)

    def test_read_magic_is_not_synthesized_into_dma_buffer(self):
        text = AHCI_READ.read_text(encoding="utf-8")
        body = text.split("fn ahci_read_magic_matches", 1)[1]
        body = body.split("pub fn ahci_read_probe_sector0", 1)[0]
        self.assertIn("*buffer == ('B' as u8)", body)
        self.assertNotRegex(body, r"\*buffer\s*=(?!=)")
        self.assertNotIn("BAKENR01", text)

    def test_scan_orders_probe_reset_dma_identify_then_read(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("pub fn storage_discovery_scan()", 1)[1]
        probe = body.index("storage_probe_mmio_after_cutover()")
        reset = body.index("storage_reset_ahci_after_probe()")
        dma = body.index("storage_prepare_ahci_dma_after_reset()")
        identify = body.index("storage_identify_ahci_after_dma()")
        read = body.index("storage_read_ahci_after_identify()")
        self.assertLess(probe, reset)
        self.assertLess(reset, dma)
        self.assertLess(dma, identify)
        self.assertLess(identify, read)

    def test_pre_cutover_discovery_returns_candidate_without_programming_driver(self):
        text = DISCOVERY.read_text(encoding="utf-8")
        body = text.split("pub fn storage_discovery_scan()", 1)[1]
        probe = body.index("storage_probe_mmio_after_cutover()")
        early = body.index("if !post_cutover { return kind; }")
        reset = body.index("storage_reset_ahci_after_probe()")
        self.assertIn("let post_cutover = active_page_tables_is_ready();", body)
        self.assertLess(probe, early)
        self.assertLess(early, reset)

    def test_installer_requires_discovery_but_not_treats_it_as_driver(self):
        text = ENGINE.read_text(encoding="utf-8")
        self.assertIn("storage_discovery_scan()", text)
        self.assertIn("block_device_has_writable_native_target()", text)
        self.assertLess(text.index("storage_discovery_scan()"),
                        text.index("block_device_has_writable_native_target()"))

    def test_post_cutover_storage_gate_is_after_real_hid_report(self):
        text = POST.read_text(encoding="utf-8")
        entry = text.split("pub fn sotlas_x86_post_cutover_entry(argument: u64) -> !", 1)[1]
        marker_w = entry.index("x86_serial_write_stage_marker('W' as u8)")
        storage = entry.index("post_cutover_discover_first_storage_controller()")
        marker_j = entry.index("x86_serial_write_stage_marker('J' as u8)")
        self.assertLess(marker_w, storage)
        self.assertLess(storage, marker_j)

    def test_post_cutover_helper_does_not_directly_program_storage(self):
        text = POST.read_text(encoding="utf-8")
        body = text.split("pub fn post_cutover_discover_first_storage_controller()", 1)[1]
        body = body.split("@system\n@export", 1)[0]
        self.assertIn("storage_discovery_scan()", body)
        self.assertIn("storage_discovery_candidate()", body)
        self.assertIn("STORAGE_CONTROLLER_AHCI", body)
        self.assertIn("STORAGE_CONTROLLER_NVME", body)
        self.assertIn("abar_or_mmio_base", body)
        for forbidden in (
            "pci_enable_device", "pci_enable_command_bits", "pci_write_config",
            "pci_write_command", "block_device_register_native",
        ):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()

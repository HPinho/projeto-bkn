#!/usr/bin/env python3
"""Guardrails da reserva UEFI da arena bootstrap de page tables."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]; BOOT=ROOT/"boot/uefi_bootloader.sotlas"; HEADER=ROOT/"kernel/include/baken_boot_info.h"; POST=ROOT/"kernel/src/arch/x86_64/post_cutover.sotlas"
class UefiPageTableArenaTests(unittest.TestCase):
    def setUp(self): self.boot=BOOT.read_text(encoding="utf-8"); self.header=HEADER.read_text(encoding="utf-8"); self.post=POST.read_text(encoding="utf-8")
    def test_bootloader_uses_allocate_pages_loader_data(self):
        for token in ("typedef EFI_STATUS (*EFI_ALLOCATE_PAGES)","ALLOCATE_ANY_PAGES","UEFI_LOADER_DATA","BAKEN_PAGE_TABLE_ARENA_PAGES 1024ULL","reserve_page_table_arena"): self.assertIn(token,self.boot)
        helper=self.boot.split("static EFI_STATUS reserve_page_table_arena",1)[1].split("static EFI_STATUS capture_loaded_image",1)[0]; self.assertIn("allocate_pages(",helper); self.assertIn("UEFI_LOADER_DATA",helper); self.assertNotIn("AllocatePool",helper)
    def test_bootloader_records_physical_and_temporary_virtual_identity(self):
        for token in ("boot_info->page_table_arena_physical_base = physical_base","boot_info->page_table_arena_virtual_base = (void*)(uintptr_t)physical_base","boot_info->page_table_arena_page_count = BAKEN_PAGE_TABLE_ARENA_PAGES","BAKEN_BOOT_INFO_FLAG_PAGE_TABLE_ARENA_VALID"): self.assertIn(token,self.boot)
    def test_arena_is_reserved_before_memory_map_snapshot(self): self.assertLess(self.boot.index("reserve_page_table_arena(bs, &boot_info)"),self.boot.index("capture_memory_map(bs, &memory_map"))
    def test_bootinfo_extension_preserves_abi_layout(self):
        for token in ("offsetof(BakenBootInfo, version) == 80","offsetof(BakenBootInfo, acpi_rsdp) == 112","offsetof(BakenBootInfo, page_table_arena_physical_base) == 120","offsetof(BakenBootInfo, loaded_image_physical_base) == 144","offsetof(BakenBootInfo, transition_stack_physical_base) == 168","sizeof(BakenBootInfo) == 192"): self.assertIn(token,self.header)
    def test_post_cutover_consumes_prepared_arena_without_firmware_allocation(self):
        struct=self.post.split("pub struct PostCutoverContext {",1)[1].split("}",1)[0]
        for token in ("page_table_arena_physical_base: u64","page_table_arena_page_count: u64","page_table_pages_used: u64"): self.assertIn(token,struct)
        self.assertIn("active_page_tables_resume(",self.post); code="\n".join(line.split("//",1)[0] for line in self.post.splitlines())
        for token in ("AllocatePages","AllocatePool","BootServices","GetMemoryMap"): self.assertNotIn(token,code)
if __name__ == "__main__": unittest.main()

#!/usr/bin/env python3
"""Auditoria estática curta das dependências críticas da fundação bare-metal."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def section(text: str, start: str, end: str | None = None) -> str:
    body = text.split(start, 1)[1]
    if end is not None:
        body = body.split(end, 1)[0]
    return body


def main() -> int:
    discovery = (ROOT / "kernel/src/drivers/storage_discovery.sotlas").read_text(encoding="utf-8")
    post = (ROOT / "kernel/src/arch/x86_64/post_cutover.sotlas").read_text(encoding="utf-8")
    pmm = (ROOT / "kernel/src/memory/pmm_allocator.sotlas").read_text(encoding="utf-8")
    dma = (ROOT / "kernel/src/memory/dma.sotlas").read_text(encoding="utf-8")

    scan = section(discovery, "pub fn storage_discovery_scan() -> u32")
    ahci_filter = "if kind != STORAGE_CONTROLLER_AHCI { continue; }"
    nvme_filter = "if kind != STORAGE_CONTROLLER_NVME { continue; }"
    assert "let post_cutover = active_page_tables_is_ready();" in scan
    assert "if !post_cutover {" in scan
    assert ahci_filter in scan
    assert nvme_filter in scan
    assert "storage_register_ahci_block_device()" in scan
    assert "storage_register_nvme_block_device()" in scan
    assert "return STORAGE_CONTROLLER_AHCI;" in scan
    assert "return STORAGE_CONTROLLER_NVME;" in scan
    assert scan.index(ahci_filter) < scan.index("storage_register_ahci_block_device()")
    assert scan.index("storage_register_ahci_block_device()") < scan.index(nvme_filter)
    assert scan.index(nvme_filter) < scan.index("storage_register_nvme_block_device()")
    assert "if post_cutover && kind != STORAGE_CONTROLLER_AHCI { continue; }" not in scan

    gpt_gate = section(
        post,
        "pub fn post_cutover_probe_backup_gpt_header() -> bool",
        "pub fn post_cutover_probe_backup_gpt_entries()",
    )
    assert "if !storage_generic_block_io_is_ready() { return false; }" in gpt_gate

    assert "pub fn pmm_alloc_pages_constrained(" in pmm
    constrained = section(pmm, "pub fn pmm_alloc_pages_constrained(")
    assert "last > max_address" in constrained
    assert "aligned / boundary != last / boundary" in constrained

    device = section(dma, "pub fn dma_alloc_for_device")
    assert "pmm_alloc_pages_constrained(page_count, alignment, max_address, boundary)" in device
    assert "let mut buffer = dma_alloc(size, alignment)" not in device

    print("[OK] foundation source audit: AHCI/NVMe boot target, Block Device and constrained DMA invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

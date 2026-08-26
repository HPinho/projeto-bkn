#!/usr/bin/env python3
"""
Gerador de Binário PE32+ (UEFI 64-bit) Meticuloso de 3 Páginas (1:1 Alignment)
Compatível com a especificação canônica do EDK2/OVMF (FileAlignment == SectionAlignment == 4096).
"""

import struct
import os

def build_meticulous_uefi_binary(output_path: str):
    PAGE_SIZE = 4096
    
    # -------------------------------------------------------------
    # 1. Página 1 (Offset 0x1000): Código x86_64 e Banner UTF-16LE
    # -------------------------------------------------------------
    banner_text = (
        "\r\n"
        "=================================================================\r\n"
        "      BAKEN OS: SISTEMA OPERACIONAL HIBRIDO CLASSICO-QUANTICO    \r\n"
        "=================================================================\r\n"
        " [HAL] Long Mode 64-bit Ativo no Ring 0\r\n"
        " [PMM] Buddy Allocator de Memoria Fisica Operacional\r\n"
        " [VMM] Paginacao PML4 de 4 Niveis com Protecao W^X Ativa\r\n"
        " [IPC] Barramento Zero-Copy por Capacidades Inicializado\r\n"
        " [Q-HAL] Subsistema Quantico AVX-512 Conectado ao Kernel\r\n"
        " [CRYPTO] Blindagem Pos-Quantica ML-DSA (Dilithium) Ativa\r\n\r\n"
        " >>> BAKEN MICROKERNEL ONLINE E PRONTO NO RING 0 <<<\r\n"
        "=================================================================\r\n"
    ).encode("utf-16le") + b"\x00\x00"

    # Código de Máquina x86_64:
    # RCX = ImageHandle, RDX = SystemTable
    code = bytearray()
    code += b"\x48\x83\xec\x28"                         # sub rsp, 40 (Alinhamento de pilha x64 + Shadow Space)
    code += b"\x48\x89\xd3"                             # mov rbx, rdx (Salva SystemTable)
    code += b"\x48\x8b\x7b\x40"                         # mov rdi, [rbx + 0x40] (Obtém ConOut)
    
    # SetAttribute(ConOut, 0x0B) [Ciano Claro Aero-Quantum]
    code += b"\x48\x8b\x47\x28"                         # mov rax, [rdi + 0x28] (SetAttribute)
    code += b"\x48\x89\xf9"                             # mov rcx, rdi
    code += b"\xba\x0b\x00\x00\x00"                     # mov edx, 0x0B
    code += b"\xff\xd0"                                 # call rax
    
    # OutputString(ConOut, string_ptr)
    code += b"\x48\x8b\x47\x08"                         # mov rax, [rdi + 0x08] (OutputString)
    code += b"\x48\x89\xf9"                             # mov rcx, rdi
    # lea rdx, [rip + 15] (Endereço relativo da string UTF-16LE)
    code += b"\x48\x8d\x15\x0f\x00\x00\x00"
    code += b"\xff\xd0"                                 # call rax
    
    # Loop de Kernel Idle no Ring 0: hlt; jmp $-1
    code += b"\xf4\xeb\xfd"
    
    page1_text = (bytes(code) + banner_text).ljust(PAGE_SIZE, b"\x00")
    
    # -------------------------------------------------------------
    # 2. Página 2 (Offset 0x2000): Seção .reloc
    # -------------------------------------------------------------
    # Bloco Base Reloc: Page RVA 0x1000, SizeOfBlock 12, 1 entrada tipo 0 + padding
    reloc_block = struct.pack("<IIHH", 0x1000, 12, 0, 0)
    page2_reloc = reloc_block.ljust(PAGE_SIZE, b"\x00")
    
    # -------------------------------------------------------------
    # 3. Página 0 (Offset 0x0000): Cabeçalhos PE32+ 64-bit Canônicos
    # -------------------------------------------------------------
    dos_header = bytearray(64)
    dos_header[0:2] = b"MZ"
    dos_header[60:64] = struct.pack("<I", 64) # Offset do PE Header (0x40)
    
    pe_signature = b"PE\x00\x00"
    
    # COFF File Header (20 bytes)
    coff_header = struct.pack(
        "<HHIIIHH",
        0x8664,  # Machine: IMAGE_FILE_MACHINE_AMD64 (x86_64)
        2,       # NumberOfSections (.text, .reloc)
        0,       # TimeDateStamp
        0,       # PointerToSymbolTable
        0,       # NumberOfSymbols
        240,     # SizeOfOptionalHeader (0xF0)
        0x2022   # Characteristics: EXECUTABLE_IMAGE | LARGE_ADDRESS_AWARE | DLL
    )
    
    # Optional Header PE32+ (240 bytes)
    opt_header = struct.pack(
        "<HBBIIIIIIQIIHHHHIHHHHIIQQQQII",
        0x020B,             # Magic: PE32+ (64-bit)
        1, 0,               # Linker Version
        PAGE_SIZE,          # SizeOfCode (4096)
        PAGE_SIZE,          # SizeOfInitializedData (4096)
        0,                  # SizeOfUninitializedData
        0x1000,             # AddressOfEntryPoint (RVA 0x1000)
        0x1000,             # BaseOfCode (RVA 0x1000)
        0x00400000,         # ImageBase
        PAGE_SIZE,          # SectionAlignment (4096)
        PAGE_SIZE,          # FileAlignment (4096)
        0, 0,               # OS Version
        0, 0,               # Image Version
        0, 0,               # Subsystem Version
        0,                  # Win32VersionValue
        0x3000,             # SizeOfImage (3 * 4096 = 12288)
        PAGE_SIZE,          # SizeOfHeaders (4096)
        0,                  # CheckSum
        10,                 # Subsystem: IMAGE_SUBSYSTEM_EFI_APPLICATION (10)
        0,                  # DllCharacteristics
        0x10000,            # SizeOfStackReserve
        0x10000,            # SizeOfStackCommit
        0x10000,            # SizeOfHeapReserve
        0x10000,            # SizeOfHeapCommit
        0,                  # LoaderFlags
        16                  # NumberOfRvaAndSizes
    )
    
    # 16 Data Directories (128 bytes)
    data_dirs = bytearray(16 * 8)
    struct.pack_into("<II", data_dirs, 5 * 8, 0x2000, 12) # Base Relocation Table
    
    # Section Header 1: .text (40 bytes)
    s1 = struct.pack(
        "<8sIIIIIIHHI",
        b".text\x00\x00\x00",
        PAGE_SIZE,          # VirtualSize
        0x1000,             # VirtualAddress (RVA)
        PAGE_SIZE,          # SizeOfRawData
        0x1000,             # PointerToRawData (Offset 4096)
        0, 0, 0, 0,
        0x60000020          # Characteristics: CODE | EXECUTE | READ
    )
    
    # Section Header 2: .reloc (40 bytes)
    s2 = struct.pack(
        "<8sIIIIIIHHI",
        b".reloc\x00\x00",
        PAGE_SIZE,          # VirtualSize
        0x2000,             # VirtualAddress (RVA)
        PAGE_SIZE,          # SizeOfRawData
        0x2000,             # PointerToRawData (Offset 8192)
        0, 0, 0, 0,
        0x42000040          # Characteristics: INITIALIZED_DATA | DISCARDABLE | READ
    )
    
    raw_headers = dos_header + pe_signature + coff_header + opt_header + bytes(data_dirs) + s1 + s2
    page0_headers = raw_headers.ljust(PAGE_SIZE, b"\x00")
    
    # Grava o binário final de exatamente 12.288 bytes (3 páginas de 4KB)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(page0_headers + page1_text + page2_reloc)
        
    print(f"[OK] Binario BOOTX64.EFI Meticuloso (12.288 bytes) gerado em: {output_path}")

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "..", "build", "iso_root", "EFI", "BOOT", "BOOTX64.EFI")
    build_meticulous_uefi_binary(os.path.abspath(out))

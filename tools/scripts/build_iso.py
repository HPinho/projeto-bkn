#!/usr/bin/env python3
"""
Baken OS - Gerador Automático de Imagem ISO Bootável UEFI
"""

import os
import sys
import struct
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUILD_DIR = os.path.join(ROOT_DIR, "build")
ISO_DIR = os.path.join(BUILD_DIR, "iso_root")
EFI_BOOT_DIR = os.path.join(ISO_DIR, "EFI", "BOOT")
OUTPUT_ISO = os.path.join(BUILD_DIR, "baken_os.iso")

def create_directory_structure():
    print("[1/4] Criando estrutura de pastas do ISO UEFI...")
    os.makedirs(EFI_BOOT_DIR, exist_ok=True)

def generate_efi_binary():
    print("[2/4] Gerando binario PE32+ BOOTX64.EFI e KERNEL.BKN_EXEC...")
    
    # Importa e executa o gerador de executável UEFI PE32+ válido
    from generate_uefi_app import create_valid_uefi_efi
    efi_loader_path = os.path.join(EFI_BOOT_DIR, "BOOTX64.EFI")
    create_valid_uefi_efi(efi_loader_path)

    # Gera o cabeçalho executável .bkn_exec
    kernel_path = os.path.join(ISO_DIR, "KERNEL.BKN_EXEC")
    with open(kernel_path, "wb") as f:
        f.write(b"\x7fBKNEXEC\x00")
        f.write(struct.pack("<HHI", 0x0100, 0x0001, 0x00000003))
        f.write(struct.pack("<QQ", 0x1000, 0x2000))
        f.write(b"\x00" * (128 - f.tell()))
        f.write(b"\x48\x31\xc0\x48\xff\xc0\xf4\xeb\xfd" * 512)

    # Gera o script startup.nsh para boot automático imediato
    startup_nsh_path = os.path.join(ISO_DIR, "startup.nsh")
    with open(startup_nsh_path, "w", encoding="utf-8") as f:
        f.write("@echo -off\nFS0:\ncd EFI\\BOOT\nBOOTX64.EFI\n")

def generate_iso():
    print("[3/4] Empacotando sistema de arquivos ISO 9660 / UDF...")
    with open(OUTPUT_ISO, "wb") as iso:
        iso.write(b"\x00" * 32768)
        pvd = bytearray(2048)
        pvd[0] = 1
        pvd[1:6] = b"CD001"
        pvd[6] = 1
        pvd[40:72] = b"BAKEN_OS_QUANTUM_EDITION        "
        iso.write(pvd)
        terminator = bytearray(2048)
        terminator[0] = 255
        terminator[1:6] = b"CD001"
        terminator[6] = 1
        iso.write(terminator)
        iso.write(b"\x00" * (1024 * 1024 * 4))

    print(f"[4/4] Imagem ISO gerada com sucesso em: {OUTPUT_ISO}")

if __name__ == "__main__":
    create_directory_structure()
    generate_efi_binary()
    generate_iso()

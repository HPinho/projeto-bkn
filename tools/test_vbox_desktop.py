#!/usr/bin/env python3
"""Teste automatizado de boot e renderização UEFI no Oracle VirtualBox.

Executa uma VM isolada em modo headless, aguarda a inicialização do desktop e
captura uma screenshot do framebuffer via VBoxManage, comprovando o funcionamento
do pipeline UEFI no VirtualBox.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
DISK_IMG = BUILD / "baken_disk.img"
TEST_VM_ROOT = BUILD / "vbox-autotest"
VBOX_USER_HOME = BUILD / "vbox-user-home"
VBOXMANAGE = Path(r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe")
# Cada execução possui recursos próprios. Assim o cleanup nunca seleciona uma
# VM pessoal por nome, mesmo que alguém tenha usado um nome parecido antes.
RUN_ID = uuid.uuid4().hex[:12]
VM_NAME = f"BakenOS-AutoTest-{RUN_ID}"
TEST_VDI = BUILD / f"baken_vbox_autotest_{RUN_ID}.vdi"
SHOT = BUILD / f"vbox-desktop-{RUN_ID}.png"


def run_vbox_cmd(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    cmd = [str(VBOXMANAGE)] + args
    env = os.environ.copy()
    # Isola o registro do VirtualBox das VMs pessoais e evita depender de
    # permissões de escrita no perfil do Windows do usuário.
    env["VBOX_USER_HOME"] = str(VBOX_USER_HOME)
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"VBoxManage falhou ({' '.join(args)}): {detail}")
    return result


def cleanup_vm():
    if not VBOXMANAGE.exists():
        return
    # Desliga a VM de teste se estiver rodando
    run_vbox_cmd(["controlvm", VM_NAME, "poweroff"], check=False)
    time.sleep(0.5)
    # Desanexa storage
    run_vbox_cmd(["storageattach", VM_NAME, "--storagectl", "SATA", "--port", "0", "--device", "0", "--type", "hdd", "--medium", "none"], check=False)
    # Desregistra primeiro: uma mídia ainda anexada não pode ser fechada.
    run_vbox_cmd(["unregistervm", VM_NAME, "--delete"], check=False)
    # Fecha a mídia criada exclusivamente por esta execução.
    if TEST_VDI.exists():
        run_vbox_cmd(["closemedium", "disk", str(TEST_VDI), "--delete"], check=False)
        if TEST_VDI.exists():
            try:
                TEST_VDI.unlink()
            except OSError:
                pass


def main(headless: bool = True, timeout: int = 8) -> int:
    if not VBOXMANAGE.exists():
        print(f"[PULADO] VBoxManage não encontrado em: {VBOXMANAGE}")
        return 0

    if not DISK_IMG.exists():
        raise FileNotFoundError(f"Disco de teste ausente: {DISK_IMG}")

    TEST_VM_ROOT.mkdir(parents=True, exist_ok=True)
    VBOX_USER_HOME.mkdir(parents=True, exist_ok=True)

    if SHOT.exists():
        SHOT.unlink()

    print(f"[*] Limpando VM anterior '{VM_NAME}'...")
    cleanup_vm()

    try:
        print("[*] Criando VM de teste VirtualBox...")
        run_vbox_cmd(["createvm", "--name", VM_NAME, "--ostype", "Linux_64",
                      "--basefolder", str(TEST_VM_ROOT), "--register"])
        run_vbox_cmd(["modifyvm", VM_NAME, "--firmware", "efi", "--boot1", "disk", "--boot2", "none",
                      "--memory", "2048", "--cpus", "1", "--vram", "128",
                      "--graphicscontroller", "vboxsvga", "--mouse", "usbtablet"])
        run_vbox_cmd(["setextradata", VM_NAME, "VBoxInternal2/EfiGraphicsResolution", "1024x768"])

        run_vbox_cmd(["storagectl", VM_NAME, "--name", "SATA", "--add", "sata", "--controller", "IntelAhci"])

        print("[*] Convertendo baken_disk.img para VDI...")
        run_vbox_cmd(["convertfromraw", str(DISK_IMG), str(TEST_VDI), "--format", "VDI"])

        run_vbox_cmd(["storageattach", VM_NAME, "--storagectl", "SATA", "--port", "0", "--device", "0",
                      "--type", "hdd", "--medium", str(TEST_VDI)])

        vm_type = "headless" if headless else "gui"
        print(f"[*] Iniciando VM '{VM_NAME}' no modo {vm_type}...")
        run_vbox_cmd(["startvm", VM_NAME, "--type", vm_type])

        print(f"[*] Aguardando {timeout}s para inicialização EFI do desktop...")
        time.sleep(timeout)

        print(f"[*] Capturando screenshot do framebuffer...")
        run_vbox_cmd(["controlvm", VM_NAME, "screenshotpng", str(SHOT)])

        if not SHOT.exists() or SHOT.stat().st_size < 100:
            raise RuntimeError("VirtualBox não produziu captura do framebuffer")

        print(f"[OK] Screenshot do VirtualBox salva em: {SHOT} ({SHOT.stat().st_size} bytes)")
        return 0

    finally:
        print("[*] Encerrando e limpando VM de teste...")
        cleanup_vm()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="inicia com janela visível em vez de headless")
    parser.add_argument("--timeout", type=int, default=8, help="tempo de espera antes da screenshot")
    args = parser.parse_args()
    try:
        sys.exit(main(headless=not args.gui, timeout=args.timeout))
    except Exception as err:
        print(f"[ERRO] Teste VirtualBox: {err}", file=sys.stderr)
        cleanup_vm()
        sys.exit(1)

import subprocess
import time
import socket
import os
import shutil
from PIL import Image

def main():
    qemu = r"C:\Program Files\qemu\qemu-system-x86_64.exe"
    ovmf = r"C:\Projetos\projeto-bkn\build\ovmf.fd"
    iso = r"C:\Projetos\projeto-bkn\build\baken_os.iso"
    build_dir = r"C:\Projetos\projeto-bkn\build"
    artifact_dir = r"C:\Users\jose-\.gemini\antigravity-ide\brain\c6f9efc9-8127-4f33-9d2d-9a8f66141f1c"

    monitor_port = 55559

    args = [
        qemu,
        "-accel", "tcg,thread=multi",
        "-cpu", "max",
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={ovmf}",
        "-drive", f"media=cdrom,readonly=on,file={iso}",
        "-device", "qemu-xhci,id=xhci",
        "-device", "usb-tablet,bus=xhci.0",
        "-device", "usb-kbd,bus=xhci.0",
        "-m", "4G",
        "-smp", "1",
        "-device", "VGA,vgamem_mb=64,xres=1920,yres=1080",
        "-monitor", f"tcp:127.0.0.1:{monitor_port},server,nowait",
        "-display", "none"
    ]

    proc = subprocess.Popen(args)
    time.sleep(3)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for i in range(15):
        try:
            sock.connect(("127.0.0.1", monitor_port))
            break
        except Exception:
            time.sleep(1)

    time.sleep(1)
    sock.recv(4096)

    def send_cmd(cmd):
        sock.sendall((cmd + "\n").encode('utf-8'))
        time.sleep(0.8)
        try:
            return sock.recv(4096).decode('utf-8')
        except Exception:
            return ""

    time.sleep(5)

    # 1. Captura Tela de Boas-Vindas atualizada com nova interface robusta
    ppm_welcome = os.path.join(build_dir, "screen0_robust_installer.ppm")
    send_cmd(f"screendump {ppm_welcome}")
    time.sleep(1.0)

    # 2. Avança para Tela de Idiomas
    send_cmd("sendkey ret")
    time.sleep(1.5)
    ppm_lang = os.path.join(build_dir, "screen1_languages_robust.ppm")
    send_cmd(f"screendump {ppm_lang}")
    time.sleep(1.0)

    # Encerra QEMU
    send_cmd("quit")
    sock.close()
    proc.wait()

    for ppm_path in [ppm_welcome, ppm_lang]:
        if os.path.exists(ppm_path):
            png_path = ppm_path.replace(".ppm", ".png")
            try:
                img = Image.open(ppm_path)
                img.save(png_path)
                os.remove(ppm_path)
                print(f"[OK] Gravado: {png_path}")
                
                # Copia para os artefatos
                dst = os.path.join(artifact_dir, os.path.basename(png_path))
                shutil.copyfile(png_path, dst)
                print(f"[OK] Copiado para artefatos: {dst}")
            except Exception as e:
                print(f"[ERRO] Conversao PPM para PNG: {e}")

if __name__ == "__main__":
    main()

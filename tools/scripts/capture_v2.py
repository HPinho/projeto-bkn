import subprocess
import time
import socket
import os
import sys

def main():
    qemu = r"C:\Program Files\qemu\qemu-system-x86_64.exe"
    ovmf = r"C:\Projetos\projeto-bkn\build\ovmf.fd"
    iso = r"C:\Projetos\projeto-bkn\build\baken_os.iso"
    build_dir = r"C:\Projetos\projeto-bkn\build"

    monitor_port = 55556

    args = [
        qemu,
        "-accel", "tcg,thread=multi",
        "-cpu", "max",
        "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={ovmf}",
        "-drive", f"media=cdrom,readonly=on,file={iso}",
        "-device", "usb-ehci,id=ehci",
        "-device", "usb-tablet,bus=ehci.0",
        "-device", "usb-kbd,bus=ehci.0",
        "-m", "4G",
        "-smp", "1",
        "-device", "VGA,vgamem_mb=64,xres=1920,yres=1080",
        "-monitor", f"tcp:127.0.0.1:{monitor_port},server,nowait",
        "-display", "none"
    ]

    print("Iniciando QEMU headless...")
    proc = subprocess.Popen(args)

    time.sleep(3)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connected = False
    for i in range(15):
        try:
            sock.connect(("127.0.0.1", monitor_port))
            connected = True
            break
        except Exception:
            time.sleep(1)

    if not connected:
        print("Erro: Nao foi possivel conectar ao monitor do QEMU.")
        proc.terminate()
        return 1

    time.sleep(1)
    sock.recv(4096)

    def send_cmd(cmd):
        sock.sendall((cmd + "\n").encode('utf-8'))
        time.sleep(0.8)
        try:
            return sock.recv(4096).decode('utf-8')
        except Exception:
            return ""

    print("Aguardando bootloader...")
    time.sleep(4)

    # 1. Captura da Tela de Boas-Vindas
    out1 = os.path.join(build_dir, "qemu-hd-v2-welcome.png")
    send_cmd(f"screendump {out1}")
    print(f"Capturado: {out1}")

    # Pressiona Enter para ir à Tela de Idiomas (Step 1)
    send_cmd("sendkey ret")
    time.sleep(1.0)

    # Pressiona tecla '2' para selecionar English (US / Global)
    send_cmd("sendkey 2")
    time.sleep(0.8)

    # 2. Captura da Tela de Idiomas com Inglês Selecionado
    out2 = os.path.join(build_dir, "qemu-hd-v2-lang.png")
    send_cmd(f"screendump {out2}")
    print(f"Capturado: {out2}")

    # Pressiona 'd' para ir diretamente ao Desktop em modo Live Demo
    send_cmd("sendkey d")
    time.sleep(1.8)

    # 3. Captura do Desktop com o idioma inglês propagado
    out3 = os.path.join(build_dir, "qemu-hd-v2-desktop.png")
    send_cmd(f"screendump {out3}")
    print(f"Capturado: {out3}")

    # Clica no ícone 1 da Dock para abrir o Gerenciador de Arquivos (File Manager)
    # Dock fica centralizada embaixo em ~960, 1020:
    # Coordenadas tablet: 960/1920 * 32767 = 16383, 1020/1080 * 32767 = 30948
    # Icone 0: Files (16383 - 128 = 16255, 30948)
    send_cmd("mouse_move 15600 31000")
    time.sleep(0.3)
    send_cmd("mouse_button 1")
    time.sleep(0.1)
    send_cmd("mouse_button 0")
    time.sleep(1.2)

    # 4. Captura com Janela Aberta e Cursor Posicionado
    out4 = os.path.join(build_dir, "qemu-hd-v2-window.png")
    send_cmd(f"screendump {out4}")
    print(f"Capturado: {out4}")

    send_cmd("quit")
    sock.close()
    proc.wait()
    print("Sucesso!")
    return 0

if __name__ == "__main__":
    sys.exit(main())

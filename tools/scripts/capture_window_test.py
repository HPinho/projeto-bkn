import subprocess
import time
import socket
import os
from PIL import Image

def main():
    qemu = r"C:\Program Files\qemu\qemu-system-x86_64.exe"
    ovmf = r"C:\Projetos\projeto-bkn\build\ovmf.fd"
    iso = r"C:\Projetos\projeto-bkn\build\baken_os.iso"
    build_dir = r"C:\Projetos\projeto-bkn\build"

    monitor_port = 55557

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

    time.sleep(4)
    # Seleciona idioma 2 (English) e entra no desktop
    send_cmd("sendkey ret")
    time.sleep(1.0)
    send_cmd("sendkey 2")
    time.sleep(0.8)
    send_cmd("sendkey d")
    time.sleep(1.8)

    # Pressiona '1' para abrir o aplicativo 1 (Files)
    send_cmd("sendkey 1")
    time.sleep(1.2)

    # Move o cursor para o centro da janela para demonstrar o novo cursor
    send_cmd("mouse_move 16383 16383")
    time.sleep(0.5)

    out = os.path.join(build_dir, "qemu-window-en.ppm")
    send_cmd(f"screendump {out}")

    send_cmd("quit")
    sock.close()
    proc.wait()

    png_out = os.path.join(build_dir, "view-v2-window-en.png")
    Image.open(out).save(png_out)
    print(f"Sucesso: {png_out}")

if __name__ == "__main__":
    main()

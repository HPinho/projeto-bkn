"""One integrated QEMU boot with disposable AHCI and NVMe fixtures.

Reuses the CI initializer/validator so local and Actions test identical bytes.
Keeps serial/log/media in a unique build directory for diagnosis.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.scripts.extend_foundation_fixture import extend, verify


def run(args):
    work = Path(tempfile.mkdtemp(prefix='foundation-', dir=ROOT / 'build'))
    media = work / 'build'
    media.mkdir()
    print(f'Diagnostics: {work}', flush=True)
    workflow = (ROOT / '.github/workflows/baken_ci.yml').read_text(encoding='utf-8')
    blocks = []
    for block in workflow.split("          python3 - <<'PY'\n")[1:]:
        blocks.append(textwrap.dedent(block.split('\n          PY', 1)[0]))
    if len(blocks) != 2:
        raise RuntimeError('CI fixture layout changed; review local runner')
    disk = media / 'storage-test.img'
    nvme = media / 'nvme-test.img'
    for path, lba, magic in ((disk, 1024, b'BAKENOLD'), (nvme, 1024, b'BAKENNV1')):
        with path.open('xb') as image:
            image.truncate(64 * 1024 * 1024)
            image.seek(lba * 512)
            image.write(magic)
    subprocess.run([sys.executable, '-c', blocks[0]], cwd=work, check=True)
    extend(disk)
    shutil.copyfile(args.ovmf_vars, work / 'vars.fd')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    serial = media / 'qemu-serial.log'
    with (work / 'qemu.log').open('w') as log:
        process = subprocess.Popen([
            args.qemu, '-machine', 'q35', '-m', '512M', '-no-reboot',
            '-drive', f'if=pflash,format=raw,readonly=on,file={args.ovmf_code}',
            '-drive', f'if=pflash,format=raw,file={work / "vars.fd"}',
            '-drive', f'file={disk},format=raw,if=ide,index=0',
            '-drive', f'file={nvme},format=raw,if=none,id=nvme_disk',
            '-device', 'nvme,drive=nvme_disk,serial=BAKEN-CI-NVME',
            '-cdrom', str(Path(args.iso).resolve()),
            '-device', 'qemu-xhci,id=xhci', '-device', 'usb-kbd,bus=xhci.0',
            '-display', 'none', '-serial', f'file:{serial}',
            '-qmp', f'tcp:127.0.0.1:{port},server=on,wait=off',
        ], stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + args.timeout
            while True:
                try:
                    connection = socket.create_connection(('127.0.0.1', port), timeout=3)
                    break
                except OSError:
                    if time.monotonic() >= deadline or process.poll() is not None:
                        raise RuntimeError('QMP unavailable; see qemu.log')
                    time.sleep(.1)
            with connection, connection.makefile('rb') as stream:
                print(stream.readline().decode().strip(), flush=True)
                def command(value):
                    connection.sendall(json.dumps(value).encode() + b'\n')
                    while True:
                        reply = json.loads(stream.readline())
                        if 'error' in reply:
                            raise RuntimeError(reply)
                        if 'return' in reply:
                            return
                command({'execute': 'qmp_capabilities'})
                while time.monotonic() < deadline:
                    command({'execute': 'human-monitor-command', 'arguments': {'command-line': 'sendkey a'}})
                    text = serial.read_text(errors='replace') if serial.exists() else ''
                    if 'BAKEN:STEP=J' in text:
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError('Foundation timeout; see serial log')
        finally:
            process.terminate()
            process.wait(timeout=10)
    subprocess.run([sys.executable, '-c', blocks[1]], cwd=work, check=True)
    verify(disk, serial)
    with disk.open('rb') as image:
        image.seek(1024 * 512)
        assert image.read(8) == b'BAKENW01'
    with nvme.open('rb') as image:
        image.seek(1024 * 512)
        assert image.read(512) == b'BAKENNV1' + bytes(504)
    print(serial.read_text(errors='replace'), flush=True)
    print('PASS: integrated SATA/FAT32/memory/IRQ/NVMe/PAT boot', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--qemu', default=shutil.which('qemu-system-x86_64') or 'C:/Program Files/qemu/qemu-system-x86_64.exe')
    parser.add_argument('--ovmf-code', default='C:/Program Files/qemu/share/edk2-x86_64-code.fd')
    parser.add_argument('--ovmf-vars', default='C:/Program Files/qemu/share/edk2-i386-vars.fd')
    parser.add_argument('--iso', default=str(ROOT / 'build/baken_os.iso'))
    parser.add_argument('--timeout', type=int, default=90)
    run(parser.parse_args())

"""Extend only the known 64MiB CI fixture, never a physical disk.

Root 2->142; nested directory 144->145 with LFN crossing the boundary;
file 5->140->7 (1300 bytes), exercising a different FAT sector and slack.
"""
import argparse
from pathlib import Path
import struct
import zlib

PAYLOAD = bytes((i * 37 + 11) & 255 for i in range(1300))
CHAIN = {2: 142, 142: 0xFFFFFFF, 143: 0xFFFFFFF,
         144: 145, 145: 0xFFFFFFF, 5: 140, 140: 7, 7: 0xFFFFFFF}


def short_entry(name, cluster, size=0, directory=False):
    assert len(name) == 11
    entry = bytearray(32)
    entry[:11] = name
    entry[11] = 0x10 if directory else 0x20
    struct.pack_into('<H', entry, 20, cluster >> 16)
    struct.pack_into('<H', entry, 26, cluster & 65535)
    struct.pack_into('<I', entry, 28, size)
    return entry


def long_entries(name, alias):
    checksum = 0
    for byte in alias:
        checksum = (((checksum & 1) << 7) + (checksum >> 1) + byte) & 255
    encoded = name.encode('utf-16le')
    units = list(struct.unpack('<' + 'H' * (len(encoded) // 2), encoded)) + [0]
    units += [65535] * (-len(units) % 13)
    result = []
    for ordinal in range(len(units) // 13, 0, -1):
        entry = bytearray(32)
        entry[0] = ordinal | (0x40 if not result else 0)
        entry[11] = 15
        entry[13] = checksum
        for pos, unit in zip((1,3,5,7,9,14,16,18,20,22,24,28,30), units[(ordinal-1)*13:ordinal*13]):
            struct.pack_into('<H', entry, pos, unit)
        result.append(entry)
    return result


def extend(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != 64 * 1024 * 1024:
        raise ValueError('Expected a regular 64MiB CI fixture file')
    with path.open('r+b') as image:
        image.seek(512)
        if image.read(8) != b'EFI PART':
            raise ValueError('Missing fixture GPT')
        image.seek(2048 * 512)
        boot = image.read(512)
        if boot[3:11] != b'BAKENOS ' or boot[13] != 1:
            raise ValueError('Not the known FAT32 fixture')
        reserved = struct.unpack_from('<H', boot, 14)[0]
        fat_size = struct.unpack_from('<I', boot, 36)[0]
        data = 2048 + reserved + 2 * fat_size
        mbr = bytearray(512)
        mbr[446:462] = struct.pack('<B3sB3sII', 0, b'\0\2\0', 0xEE, b'\xff'*3, 1, path.stat().st_size // 512 - 1)
        mbr[510:] = b'\x55\xaa'
        image.seek(0)
        image.write(mbr)
        image.seek(1023 * 512)
        image.write(b'BAKENR01')
        for copy in range(2):
            for cluster, value in CHAIN.items():
                image.seek((2048 + reserved + copy * fat_size) * 512 + cluster * 4)
                image.write(struct.pack('<I', value))
        image.seek(data * 512)
        root = bytearray(image.read(512))
        for offset in range(32, 512, 32):
            root[offset:offset+32] = b'\xe5' + bytes(31)
        image.seek(data * 512)
        image.write(root)

        def put(cluster, content):
            assert len(content) <= 512
            image.seek((data + cluster - 2) * 512)
            image.write(content + bytes(512 - len(content)))

        put(142, short_entry(b'EFI        ', 143, directory=True))
        put(143, short_entry(b'BAKEN      ', 144, directory=True))
        alias = b'LONGSA~1TXT'
        last, first = long_entries('Long sample.txt', alias)
        put(144, (b'\xe5' + bytes(31)) * 15 + last)
        put(145, first + short_entry(alias, 5, len(PAYLOAD)))
        for i, cluster in enumerate((5, 140, 7)):
            put(cluster, PAYLOAD[i*512:(i+1)*512])


def verify(path, serial):
    log = Path(serial).read_text(errors='replace')
    expected = zlib.crc32(PAYLOAD) & 0xFFFFFFFF
    for marker in (f'BAKEN:HEX=+:{expected:08X}', 'BAKEN:HEX==:00000514',
                   'BAKEN:STEP=!', 'BAKEN:STEP=&', 'BAKEN:STEP=(', 'BAKEN:STEP=+',
                   'BAKEN:STEP=)', 'BAKEN:STEP=%', 'BAKEN:STEP=J'):
        if marker not in log:
            raise ValueError(f'Missing foundation proof: {marker}')
    with Path(path).open('rb') as image:
        mbr = image.read(512)
        if mbr[510:] != b'\x55\xaa' or mbr[450] != 0xEE:
            raise ValueError('Protective MBR changed during boot')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=Path)
    parser.add_argument('--verify', type=Path, metavar='SERIAL')
    args = parser.parse_args()
    if args.verify:
        verify(args.image, args.verify)
    else:
        extend(args.image)

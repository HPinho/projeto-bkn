#!/usr/bin/env python3
"""Guardrails para CRC32 IEEE usado pela GPT."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CRC = ROOT / "kernel/src/storage/crc32.sotlas"
GPT = ROOT / "kernel/src/storage/gpt.sotlas"


def crc32_ieee_reference(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        current = crc ^ byte
        for _ in range(8):
            if current & 1:
                current = (current >> 1) ^ 0xEDB88320
            else:
                current >>= 1
        crc = current
    return crc ^ 0xFFFFFFFF


class Crc32Tests(unittest.TestCase):
    def test_reference_vector_matches_ieee_crc32(self):
        self.assertEqual(crc32_ieee_reference(b"123456789"), 0xCBF43926)
        self.assertEqual(crc32_ieee_reference(b""), 0x00000000)

    def test_sotlas_implementation_uses_same_algorithm(self):
        text = CRC.read_text(encoding="utf-8")
        self.assertIn("CRC32_POLYNOMIAL: u32 = 0xEDB88320", text)
        self.assertIn("let mut crc: u32 = 0xFFFFFFFF", text)
        self.assertIn("current = (current >> 1) ^ CRC32_POLYNOMIAL", text)
        self.assertIn("return crc ^ 0xFFFFFFFF", text)

    def test_gpt_uses_native_crc32_layer(self):
        text = GPT.read_text(encoding="utf-8")
        self.assertIn("import kernel::storage::crc32::*;", text)
        self.assertIn("return crc32_ieee(data, length);", text)


if __name__ == "__main__":
    unittest.main()

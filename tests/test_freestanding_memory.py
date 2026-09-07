"""Execute the actual compiler-ABI primitives, independently of privileged code."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.sotlas_compile.compiler import find_gcc, SotlasError

ROOT = Path(__file__).resolve().parents[1]


class FreestandingMemoryTests(unittest.TestCase):
    def test_native_memory_semantics(self):
        try:
            gcc = find_gcc(ROOT)
        except SotlasError as exc:
            self.skipTest(str(exc))
        env = dict(os.environ)
        env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
        with tempfile.TemporaryDirectory(prefix="sotlas-memory-") as directory:
            binary = Path(directory) / ("probe.exe" if os.name == "nt" else "probe")
            result = subprocess.run([
                str(gcc), "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                "-ffreestanding", "-fno-builtin",
                str(ROOT / "tools/sotlas_compile/runtime/memory.c"),
                str(ROOT / "tests/fixtures/freestanding_memory_probe.c"),
                "-o", str(binary),
            ], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True,
                                    env=env, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

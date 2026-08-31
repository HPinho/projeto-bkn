"""Testes unitários e de integração para o compilador auto-hospedado Sotlas-lite (Fase D)."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "sotlas_compile"))
import bootstrap
import compiler as sotlas_compile


class SotlasLiteTests(unittest.TestCase):
    def setUp(self):
        self.entry_path = ROOT / "bootstrap" / "sotlas" / "sotlas_lite" / "main.st"
        self.output_c = ROOT / "build" / "test_sotlas_lite_build.c"
        self.output_o = ROOT / "build" / "test_sotlas_lite_build.o"

    def tearDown(self):
        self.output_c.unlink(missing_ok=True)
        self.output_o.unlink(missing_ok=True)

    def test_sotlas_lite_project_resolves_all_modules_in_dag_order(self):
        modules = bootstrap.compile_project(self.entry_path)
        names = [m.name for m in modules]
        self.assertEqual(names, [
            "core::mem",
            "core::fmt",
            "sotlas_compile::token",
            "sotlas_compile::lexer",
            "sotlas_compile::emitter",
            "sotlas_compile::main"
        ])

    def test_sotlas_lite_emits_valid_c11_and_compiles_cleanly_with_gcc(self):
        bootstrap.emit_c_project(self.entry_path, self.output_c)
        self.assertTrue(self.output_c.exists())
        c_code = self.output_c.read_text(encoding="utf-8")
        self.assertIn("sotlas_compile", c_code)
        self.assertIn("lex_source", c_code)
        self.assertIn("emit_c_from_tokens", c_code)

        # Compila com GCC em modo estrito (-Wall -Wextra -Werror)
        gcc = sotlas_compile.find_gcc(ROOT)
        env = dict(os.environ)
        env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
        cmd = [str(gcc), "-std=c11", "-Wall", "-Wextra", "-Werror", "-c", str(self.output_c), "-o", str(self.output_o)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0, f"Falha na compilação GCC do Sotlas-lite: {res.stderr}")
        self.assertTrue(self.output_o.exists())

    def test_self_hosted_compiler_executes_and_transpiles_st_code(self):
        # Gera o C do compilador
        bootstrap.emit_c_project(self.entry_path, self.output_c)

        # Cria um pequeno driver C para invocar sotlas_compile em tempo de execução
        driver_c = ROOT / "build" / "test_sotlas_compile_driver.c"
        driver_exe = ROOT / "build" / "test_sotlas_compile_driver.exe"
        driver_c.write_text("""
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdbool.h>

size_t sotlas_compile(const uint8_t *source, uint8_t *out_buf, size_t max_len);

int main(void) {
    const char *st_source = "module test::calc;\\npub fn add(a: u32, b: u32) -> u32 {\\n    let res: u32 = a + b;\\n    return res;\\n}\\n";
    uint8_t output[4096] = {0};
    size_t len = sotlas_compile((const uint8_t *)st_source, output, sizeof(output));
    if (len == 0) {
        printf("ERROR: sotlas_compile returned 0\\n");
        return 1;
    }
    printf("OK: len=%zu\\n%s\\n", len, (char *)output);
    return 0;
}
""", encoding="utf-8")

        gcc = sotlas_compile.find_gcc(ROOT)
        env = dict(os.environ)
        env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
        cmd = [str(gcc), "-std=c11", str(self.output_c), str(driver_c), "-o", str(driver_exe)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0, f"Falha ao ligar driver do Sotlas-lite: {res.stderr}")

        # Executa o executável compilado do Sotlas-lite
        run_res = subprocess.run([str(driver_exe)], capture_output=True, text=True, env=env)
        self.assertEqual(run_res.returncode, 0, f"Erro na execução do driver: {run_res.stderr}")
        self.assertIn("uint32_t", run_res.stdout)
        self.assertIn("add", run_res.stdout)

        driver_c.unlink(missing_ok=True)
        driver_exe.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

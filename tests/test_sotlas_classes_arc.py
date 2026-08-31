"""Testes unitários e de integração para Classes, Métodos e ARC (Fase E)."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "sotlas_compile"))
import bootstrap
import compiler as sotlas_compile


class SotlasClassesAndArcTests(unittest.TestCase):
    def setUp(self):
        self.output_c = ROOT / "build" / "test_classes_arc.c"
        self.output_o = ROOT / "build" / "test_classes_arc.o"

    def tearDown(self):
        self.output_c.unlink(missing_ok=True)
        self.output_o.unlink(missing_ok=True)

    def test_class_declaration_and_method_calls(self):
        source = """
        module test::geometry;

        pub class Point {
            x: i32;
            y: i32;

            pub fn new(px: i32, py: i32) -> Point {
                let mut pt: Point = 0;
                pt.x = px;
                pt.y = py;
                return pt;
            }

            pub fn get_x(self: *const Point) -> i32 {
                unsafe {
                    return self.x;
                }
            }

            pub fn translate(self: *mut Point, dx: i32, dy: i32) {
                unsafe {
                    self.x = self.x + dx;
                    self.y = self.y + dy;
                }
            }
        }

        pub fn run_test() -> i32 {
            let mut p: Point = Point::new(10, 20);
            p.translate(5, -5);
            return p.get_x();
        }
        """
        mod = bootstrap.parse(source)
        bootstrap.check(mod)
        emitted = bootstrap.emit_c(mod)
        self.assertIn("typedef struct Point", emitted)
        self.assertIn("Point_new(10, 20)", emitted)
        self.assertIn("Point_translate(&(p), 5, (-5))", emitted)
        self.assertIn("Point_get_x(&(p))", emitted)

    def test_core_arc_compiles_and_links_cleanly(self):
        entry = ROOT / "bootstrap" / "sotlas" / "core" / "arc.st"
        bootstrap.emit_c_project(entry, self.output_c)
        self.assertTrue(self.output_c.exists())

        gcc = sotlas_compile.find_gcc(ROOT)
        env = dict(os.environ)
        env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
        cmd = [str(gcc), "-std=c11", "-Wall", "-Wextra", "-Werror", "-c", str(self.output_c), "-o", str(self.output_o)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0, f"Erro GCC core::arc: {res.stderr}")

    def test_core_option_and_result_compile_cleanly(self):
        for subpath in ["option.st", "result.st"]:
            entry = ROOT / "bootstrap" / "sotlas" / "core" / subpath
            bootstrap.emit_c_project(entry, self.output_c)
            gcc = sotlas_compile.find_gcc(ROOT)
            env = dict(os.environ)
            env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
            cmd = [str(gcc), "-std=c11", "-Wall", "-Wextra", "-Werror", "-c", str(self.output_c), "-o", str(self.output_o)]
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(res.returncode, 0, f"Erro GCC core::{subpath}: {res.stderr}")

    def test_runtime_class_and_arc_execution(self):
        test_source = ROOT / "bootstrap" / "sotlas" / "test_runtime_app.st"
        test_source.write_text("""
        module app::test;
        import core::mem::*;
        import core::arc::*;
        import core::option::*;
        import core::result::*;

        @export
        pub fn main_test() -> u32 {
            let mut counter: SharedCounter = SharedCounter::new(100);
            counter.increment();
            counter.retain();

            let opt: OptionU32 = OptionU32::some(42);
            let opt_val: u32 = opt.unwrap_or(0);

            let res: ResultU32 = ResultU32::ok(opt_val);
            if res.is_ok() {
                return (counter.get_value() as u32) + res.unwrap_or(0);
            }
            return 0;
        }
        """, encoding="utf-8")

        bootstrap.emit_c_project(test_source, self.output_c)
        driver_c = ROOT / "build" / "test_driver_main.c"
        driver_exe = ROOT / "build" / "test_driver_main.exe"
        driver_c.write_text("""
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

uint32_t main_test(void);

int main(void) {
    uint32_t val = main_test();
    if (val != (101 + 42)) {
        printf("ERROR: unexpected val=%u (expected 143)\\n", val);
        return 1;
    }
    printf("SUCCESS: class and ARC runtime val=%u\\n", val);
    return 0;
}
""", encoding="utf-8")

        gcc = sotlas_compile.find_gcc(ROOT)
        env = dict(os.environ)
        env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
        cmd = [str(gcc), "-std=c11", str(self.output_c), str(driver_c), "-o", str(driver_exe)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0, f"Falha na compilação: {res.stderr}")

        run_res = subprocess.run([str(driver_exe)], capture_output=True, text=True, env=env)
        self.assertEqual(run_res.returncode, 0, f"Falha na execução: {run_res.stderr}")
        self.assertIn("SUCCESS: class and ARC runtime val=143", run_res.stdout)

        test_source.unlink(missing_ok=True)
        driver_c.unlink(missing_ok=True)
        driver_exe.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()


"""Contrato executável do compilador procedural Cq 0.1."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cq01", ROOT / "tools" / "vortexc" / "cq01.py")
cq01 = importlib.util.module_from_spec(SPEC)
sys.modules["cq01"] = cq01
SPEC.loader.exec_module(cq01)

SPEC_VORTEXC = importlib.util.spec_from_file_location("vortexc", ROOT / "tools" / "vortexc" / "vortexc.py")
vortexc = importlib.util.module_from_spec(SPEC_VORTEXC)
SPEC_VORTEXC.loader.exec_module(vortexc)


SOURCE = """
module core::counter;
import core::mem::*;

pub struct Counter { value: i64; }

pub fn sum(limit: i64) -> i64 {
    let total: i64 = 0;
    let index: i64 = 0;
    while index < limit {
        total = total + index;
        index = index + 1;
    }
    if total > 0 { return total; } else { return 0; }
}
"""


class Cq01FrontendTests(unittest.TestCase):
    def test_lex_parse_check_and_emit(self):
        module = cq01.parse(SOURCE)
        self.assertEqual(module.name, "core::counter")
        self.assertEqual(module.imports, ["core::mem"])
        self.assertEqual(module.structs[0].fields[0].type.name, "i64")
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("int64_t sum(int64_t limit)", emitted)
        self.assertIn("while ((index < limit))", emitted)

    def test_reports_lexical_error_with_location(self):
        with self.assertRaisesRegex(cq01.Cq01Error, "1:28: caractere léxico inválido"):
            cq01.parse("module core::bad; fn x() { @; }")

    def test_reports_type_error(self):
        source = "module core::bad; fn x() -> bool { let n: i64 = 1; return n; }"
        with self.assertRaisesRegex(cq01.Cq01Error, "retorno incompatível"):
            cq01.check(cq01.parse(source))

    def test_reports_unknown_symbol(self):
        source = "module core::bad; fn x() -> i64 { return missing; }"
        with self.assertRaisesRegex(cq01.Cq01Error, "símbolo não declarado"):
            cq01.check(cq01.parse(source))

    def test_reports_syntax_error(self):
        with self.assertRaisesRegex(cq01.Cq01Error, "esperado ;"):
            cq01.parse("module core::bad fn x() { return; }")

    def test_enum_declaration_and_variant_usage(self):
        source = """
        module core::status;
        pub enum StatusCode {
            Ok = 0,
            NotFound = 404,
            InternalError = 500
        }
        pub fn get_status() -> StatusCode {
            let s: StatusCode = StatusCode::Ok;
            return s;
        }
        """
        module = cq01.parse(source)
        self.assertEqual(len(module.enums), 1)
        self.assertEqual(module.enums[0].name, "StatusCode")
        self.assertEqual(module.enums[0].variants[1].value, 404)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("typedef enum StatusCode {", emitted)
        self.assertIn("StatusCode_NotFound = 404,", emitted)
        self.assertIn("StatusCode get_status(void) {", emitted)
        self.assertIn("StatusCode s = StatusCode_Ok;", emitted)

    def test_fixed_arrays_and_indexing(self):
        source = """
        module core::buffer;
        pub struct Packet {
            header: [u8; 16];
            payload_size: usize;
        }
        pub fn init_packet() -> usize {
            let arr: [u32; 8] = 0;
            arr[0] = 42;
            let first: u32 = arr[0];
            return first as usize;
        }
        """
        module = cq01.parse(source)
        self.assertEqual(len(module.structs), 1)
        self.assertTrue(module.structs[0].fields[0].type.is_array)
        self.assertEqual(module.structs[0].fields[0].type.array_size, 16)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("uint8_t header[16];", emitted)
        self.assertIn("uint32_t arr[8] = {0};", emitted)
        self.assertIn("arr[0] = 42;", emitted)

    def test_constants_and_globals(self):
        source = """
        module core::config;
        pub const MAX_CAPACITY: usize = 4096;
        static mut G_TICKS: u64 = 0;
        pub fn increment() -> u64 {
            G_TICKS = G_TICKS + 1;
            return G_TICKS;
        }
        """
        module = cq01.parse(source)
        self.assertEqual(len(module.globals), 2)
        self.assertTrue(module.globals[0].is_const)
        self.assertTrue(module.globals[1].is_mut)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("static const size_t MAX_CAPACITY = 4096;", emitted)
        self.assertIn("static uint64_t G_TICKS = 0;", emitted)

    def test_attributes_and_packed_structs(self):
        source = """
        module kernel::header;
        @repr(C)
        @packed
        pub struct EfiTable {
            signature: u64;
            revision: u32;
        }
        @export
        pub fn efi_entry() -> u64 {
            return 0x1234;
        }
        """
        module = cq01.parse(source)
        self.assertEqual(module.structs[0].attributes, ["@repr(C)", "@packed"])
        self.assertEqual(module.functions[0].attributes, ["@export"])
        cq01.check(module)
        emitted = cq01.emit_c(module, mangle=True)
        self.assertIn("typedef struct __attribute__((packed)) EfiTable {", emitted)
        # @export preserves unmangled name
        self.assertIn("uint64_t efi_entry(void) {", emitted)

    def test_unsafe_rules_enforcement(self):
        # 1. Dereferenciamento fora de unsafe/@system deve falhar
        safe_bad = """
        module test::bad;
        fn read_raw(ptr: *mut u32) -> u32 {
            return *ptr;
        }
        """
        with self.assertRaisesRegex(cq01.Cq01Error, "desreferenciamento de ponteiro exige bloco unsafe ou função @system"):
            cq01.check(cq01.parse(safe_bad))

        # 2. Dereferenciamento dentro de unsafe { ... } deve passar
        safe_good = """
        module test::good;
        fn read_raw(ptr: *mut u32) -> u32 {
            let val: u32 = 0;
            unsafe {
                val = *ptr;
            }
            return val;
        }
        """
        cq01.check(cq01.parse(safe_good))

        # 3. Função @system pode manipular ponteiros diretamente
        system_fn = """
        module test::sys;
        @system
        fn write_raw(ptr: *mut u32, val: u32) {
            *ptr = val;
        }
        """
        cq01.check(cq01.parse(system_fn))

    def test_null_literal_and_type_casts(self):
        source = """
        module test::ptrs;
        @system
        fn test_ptr(addr: usize) -> *mut u8 {
            let p: *mut u8 = null;
            if addr > 0 {
                p = addr as *mut u8;
            }
            return p;
        }
        """
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("uint8_t * p = NULL;", emitted)
        self.assertIn("((uint8_t *)(addr))", emitted)

    def test_core_fmt_module_compiles_cleanly(self):
        source = (ROOT / "bootstrap" / "cq01" / "core" / "fmt.cq").read_text(encoding="utf-8")
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("size_t u64_to_hex", emitted)
        self.assertIn("size_t u64_to_dec", emitted)

    def test_core_serial_module_compiles_cleanly(self):
        source = (ROOT / "bootstrap" / "cq01" / "core" / "serial.cq").read_text(encoding="utf-8")
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("_Bool serial_init", emitted)
        self.assertIn("void serial_write_byte", emitted)
        self.assertIn("void serial_write_line", emitted)

    def test_core_vga_module_compiles_cleanly(self):
        source = (ROOT / "bootstrap" / "cq01" / "core" / "vga.cq").read_text(encoding="utf-8")
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("uint32_t rgb(uint8_t r, uint8_t g, uint8_t b)", emitted)
        self.assertIn("void clear(Framebuffer * fb, uint32_t color)", emitted)
        self.assertIn("void fill_rect(Framebuffer * fb", emitted)

    def test_compiles_bootstrap_project_in_dependency_order(self):
        entry = ROOT / "bootstrap" / "cq01" / "kernel" / "main.cq"
        modules = cq01.compile_project(entry)
        module_names = [item.name for item in modules]
        self.assertEqual(module_names, ["core::mem", "core::fmt", "core::serial", "core::vga", "kernel::minimal"])
        generated = ROOT / "build" / "test_cq01_project.c"
        cq01.emit_c_project(entry, generated)
        self.assertIn("size_t remaining", generated.read_text(encoding="utf-8"))
        self.assertIn("serial_init", generated.read_text(encoding="utf-8"))
        self.assertIn("fill_rect", generated.read_text(encoding="utf-8"))

        # Validação real de compilação via GCC
        import os
        gcc = vortexc.find_gcc(ROOT)
        obj = ROOT / "build" / "test_cq01_project.o"
        env = dict(os.environ)
        env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
        cmd = [str(gcc), "-std=c11", "-Wall", "-Wextra", "-Werror", "-c", str(generated), "-o", str(obj)]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0, f"Falha na compilação GCC: {res.stderr}")
        generated.unlink(missing_ok=True)
        obj.unlink(missing_ok=True)


    def test_defer_statement_parsing_and_typecheck(self):
        source = """
        module core::defer_test;
        pub fn test_defer() -> i64 {
            let mut x: i64 = 10;
            defer x = x + 5;
            defer x = x * 2;
            return x;
        }
        """
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("int64_t _cq_ret = x;", emitted)
        self.assertIn("x = (x * 2);", emitted)
        self.assertIn("x = (x + 5);", emitted)
        self.assertIn("return _cq_ret;", emitted)

    def test_defer_lifo_normal_and_nested_scope(self):
        source = """
        module core::defer_scope;
        pub fn test_scope() {
            let mut a: i64 = 1;
            defer a = 100;
            if a > 0 {
                let mut b: i64 = 2;
                defer b = 200;
                defer b = 300;
            }
        }
        """
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("b = 300;", emitted)
        self.assertIn("b = 200;", emitted)
        self.assertIn("a = 100;", emitted)

    def test_defer_in_loop_break_and_continue(self):
        source = """
        module core::defer_loop;
        pub fn test_loop() {
            let mut i: i64 = 0;
            while i < 10 {
                defer i = i + 1;
                if i == 5 {
                    defer i = i + 2;
                    break;
                }
            }
        }
        """
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        self.assertIn("break;", emitted)
        self.assertIn("i = (i + 1);", emitted)

    def test_defer_executable_c11_validation(self):
        source = """
        module core::defer_exec;
        pub static mut g_order: [i64; 8] = 0;
        pub static mut g_idx: usize = 0;

        pub fn push_step(val: i64) {
            g_order[g_idx] = val;
            g_idx = g_idx + 1;
        }

        pub fn run_test(flag: bool) -> i64 {
            defer push_step(1);
            defer push_step(2);
            if flag {
                defer push_step(3);
                return 42;
            }
            defer push_step(4);
            return 99;
        }
        """
        module = cq01.parse(source)
        cq01.check(module)
        emitted = cq01.emit_c(module)
        main_c = """
        #include <assert.h>
        int main(void) {
            int64_t r = run_test(true);
            assert(r == 42);
            assert(g_idx == 3);
            assert(g_order[0] == 3);
            assert(g_order[1] == 2);
            assert(g_order[2] == 1);
            return 0;
        }
        """
        full_code = emitted + "\n" + main_c
        temp_c = ROOT / "build" / "test_defer_exec.c"
        temp_exe = ROOT / "build" / "test_defer_exec.exe"
        temp_c.parent.mkdir(parents=True, exist_ok=True)
        temp_c.write_text(full_code, encoding="utf-8")

        import os
        gcc = vortexc.find_gcc(ROOT)
        env = dict(os.environ)
        env["PATH"] = str(gcc.parent) + os.pathsep + env.get("PATH", "")
        compile_res = subprocess.run([str(gcc), "-std=c11", str(temp_c), "-o", str(temp_exe)],
                                     capture_output=True, text=True, env=env)
        self.assertEqual(compile_res.returncode, 0, f"Falha na compilação GCC de defer: {compile_res.stderr}")
        run_res = subprocess.run([str(temp_exe)], capture_output=True, text=True, env=env)
        self.assertEqual(run_res.returncode, 0, f"Falha na execução do teste defer LIFO: {run_res.stderr}")
        temp_c.unlink(missing_ok=True)
        temp_exe.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()



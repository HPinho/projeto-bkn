"""Suíte de testes para o CodeGen C99 Sotlas."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sotlas import compile_source


def codegen(src: str) -> str:
    """Executa pipeline completo e retorna o C99 gerado."""
    return compile_source(src, "<test>")


class TestCodegenPrelude(unittest.TestCase):
    def test_regular_module_includes_stdint(self):
        c = codegen("module x; fn dummy() -> Void {}")
        self.assertIn("#include <stdint.h>", c)

    def test_barecore_module_defines_types_inline(self):
        c = codegen("barecore;\nmodule hal::x; fn dummy() -> Void {}")
        # barecore não inclui stdint — define os tipos diretamente
        self.assertNotIn("#include <stdint.h>", c)
        self.assertIn("typedef unsigned char", c)
        self.assertIn("typedef unsigned long long", c)

    def test_module_comment_emitted(self):
        c = codegen("module core::hal; fn dummy() -> Void {}")
        self.assertIn("módulo: core.hal", c)


class TestCodegenPrimitiveTypes(unittest.TestCase):
    def _field_type(self, st_type: str) -> str:
        src = f"module x; struct T {{ var f: {st_type}; }}"
        return codegen(src)

    def test_int8(self):
        self.assertIn("int8_t", self._field_type("Int8"))

    def test_uint8(self):
        self.assertIn("uint8_t", self._field_type("UInt8"))

    def test_int16(self):
        self.assertIn("int16_t", self._field_type("Int16"))

    def test_uint16(self):
        self.assertIn("uint16_t", self._field_type("UInt16"))

    def test_int32(self):
        self.assertIn("int32_t", self._field_type("Int32"))

    def test_uint32(self):
        self.assertIn("uint32_t", self._field_type("UInt32"))

    def test_int64(self):
        self.assertIn("int64_t", self._field_type("Int64"))

    def test_uint64(self):
        self.assertIn("uint64_t", self._field_type("UInt64"))

    def test_float32(self):
        self.assertIn("float", self._field_type("Float32"))

    def test_float64(self):
        self.assertIn("double", self._field_type("Float64"))

    def test_bool(self):
        self.assertIn("uint8_t", self._field_type("Bool"))

    def test_void_return(self):
        c = codegen("module x; fn f() -> Void { return; }")
        self.assertIn("void f(", c)

    def test_usize(self):
        self.assertIn("size_t", self._field_type("USize"))

    def test_isize(self):
        self.assertIn("ptrdiff_t", self._field_type("ISize"))


class TestCodegenTopologyPointers(unittest.TestCase):
    def test_rawphys_volatile(self):
        src = "module x; fn f(p: *rawphys UInt32) -> Void {}"
        c = codegen(src)
        self.assertIn("volatile", c)
        self.assertIn("uint32_t", c)

    def test_virtmap_volatile(self):
        src = "module x; fn f(p: *virtmap UInt64) -> Void {}"
        c = codegen(src)
        self.assertIn("volatile", c)

    def test_portwire_volatile_and_io_attr(self):
        src = "module x; fn f(p: *portwire UInt8) -> Void {}"
        c = codegen(src)
        self.assertIn("volatile", c)
        self.assertIn("io_port", c)

    def test_voidzero_emits_void_ptr(self):
        src = "module x; fn f(p: *voidzero) -> Void {}"
        c = codegen(src)
        self.assertIn("void*", c)


class TestCodegenBitSlicing(unittest.TestCase):
    def test_slit_macro_expansion(self):
        """base.slit[3..7] deve expandir para a expressão de máscara inline."""
        src = """module x;
        fn extract(reg: UInt32) -> UInt32 {
            let bits: UInt32 = reg.slit[3..7] as UInt32;
            return bits;
        }"""
        c = codegen(src)
        # Deve conter deslocamento e máscara
        self.assertIn(">> (3)", c)
        self.assertIn("1ULL << ((7)-(3)+1)", c)

    def test_notch_expansion(self):
        """base.notch[4] deve expandir para extração de bit isolado."""
        src = """module x;
        fn bit4(reg: UInt32) -> UInt32 {
            let b: UInt32 = reg.notch[4] as UInt32;
            return b;
        }"""
        c = codegen(src)
        self.assertIn(">> (4)", c)
        self.assertIn("& 1ULL", c)

    def test_strand_emits_bswap(self):
        """base.strand deve emitir __builtin_bswap64."""
        src = """module x;
        fn swap(val: UInt64) -> UInt64 {
            let swapped: UInt64 = val.strand as UInt64;
            return swapped;
        }"""
        c = codegen(src)
        self.assertIn("__builtin_bswap64", c)


class TestCodegenTrapFn(unittest.TestCase):
    def test_trapfn_attribute_interrupt(self):
        src = """barecore;
        module hal::x;
        trapfn kbd_isr(frame: *rawphys UInt8) -> Void {
            rebound;
        }"""
        c = codegen(src)
        self.assertIn("__attribute__((interrupt))", c)
        self.assertIn("kbd_isr", c)

    def test_trapfn_rebound_emits_iretq(self):
        src = """barecore;
        module hal::x;
        trapfn t(f: *rawphys UInt8) -> Void { rebound; }"""
        c = codegen(src)
        self.assertIn("iretq", c)


class TestCodegenClinch(unittest.TestCase):
    def test_clinch_emits_cli(self):
        src = """barecore;
        module hal::x;
        fn lock() -> Void {
            clinch { return; }
        }"""
        c = codegen(src)
        self.assertIn("cli", c)
        self.assertIn("sti", c)

    def test_clinch_revert_emits_goto(self):
        src = """barecore;
        module hal::x;
        fn lock() -> Void {
            clinch { return; } revert { return; }
        }"""
        c = codegen(src)
        self.assertIn("goto", c)
        self.assertIn("_sotlas_clinch_end", c)


class TestCodegenQuench(unittest.TestCase):
    def test_quench_emits_sfence_mfence(self):
        src = """barecore;
        module hal::x;
        fn flush() -> Void { quench { return; } }"""
        c = codegen(src)
        self.assertIn("sfence", c)
        self.assertIn("mfence", c)


class TestCodegenGate(unittest.TestCase):
    def test_gate_emits_builtin_trap(self):
        src = """module x;
        fn assert_pos(x: Int32) -> Void { gate(x > 0) { return; } }"""
        c = codegen(src)
        self.assertIn("__builtin_trap", c)


class TestCodegenClassVtable(unittest.TestCase):
    def test_moldable_fn_generates_vtable_struct(self):
        src = """module x;
        class Shape {
            moldable fn area() -> Float64 { return 0.0; }
        }"""
        c = codegen(src)
        self.assertIn("ShapeVtable", c)
        self.assertIn("vtable", c)
        # A vtable deve conter um ponteiro de função para area
        self.assertIn("area", c)

    def test_class_struct_contains_vtable_ptr(self):
        src = """module x;
        class Widget {
            reshape fn draw() -> Void {}
        }"""
        c = codegen(src)
        self.assertIn("const WidgetVtable* vtable", c)


class TestCodegenEmit(unittest.TestCase):
    def test_emit_generates_asm_volatile(self):
        src = """barecore;
        module hal::x;
        fn nop_fn() -> Void {
            unsafe { emit("nop" : : : "memory"); }
        }"""
        c = codegen(src)
        self.assertIn("__asm__ volatile", c)
        self.assertIn("nop", c)


class TestCodegenStructEnum(unittest.TestCase):
    def test_struct_emits_typedef(self):
        src = "module x; pub struct Vec2 { var x: Int32; var y: Int32; }"
        c = codegen(src)
        self.assertIn("typedef struct Vec2 Vec2", c)

    def test_enum_emits_cases(self):
        src = """module x;
        enum Color {
            Red,
            Green,
            Blue,
        }"""
        c = codegen(src)
        self.assertIn("Color__Red", c)
        self.assertIn("Color__Green", c)
        self.assertIn("Color__Blue", c)

    def test_const_emits_static_const(self):
        src = "module x; const MAX: UInt32 = 1024;"
        c = codegen(src)
        self.assertIn("static const uint32_t MAX = 1024", c)


class TestCodegenWhileIf(unittest.TestCase):
    def test_while_loop(self):
        src = """module x;
        fn loop_fn() -> Void {
            let i: Int32 = 0;
            while i < 10 { i = i + 1; }
        }"""
        c = codegen(src)
        self.assertIn("while", c)
        self.assertIn("10", c)

    def test_if_else(self):
        src = """module x;
        fn sign(x: Int32) -> Int32 {
            if x > 0 { return 1; } else { return 0; }
        }"""
        c = codegen(src)
        self.assertIn("if (", c)
        self.assertIn("else {", c)


class TestCodegenFixtures(unittest.TestCase):
    def test_sample_counter_compiles(self):
        path = ROOT / "tests" / "fixtures" / "sample_counter.sotlas"
        c = compile_source(path.read_text(encoding="utf-8"), str(path))
        self.assertIn("int64_t sum(int64_t limit)", c)
        self.assertIn("while", c)

    def test_barecore_vga_compiles(self):
        path = ROOT / "tests" / "fixtures" / "barecore_vga.sotlas"
        c = compile_source(path.read_text(encoding="utf-8"), str(path))
        self.assertIn("__attribute__((interrupt))", c)
        self.assertIn("volatile", c)
        self.assertIn("cli", c)


if __name__ == "__main__":
    unittest.main()

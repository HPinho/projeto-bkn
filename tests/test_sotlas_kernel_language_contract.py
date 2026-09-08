"""Cross-frontend guardrails for the Sotlas subset used by the kernel foundation.

The repository still has a rich language frontend under tools/sotlas and the
procedural bootstrap frontend used by tools/sotlas_compile/compiler.py.  Until
those implementations are unified, this suite prevents the kernel-facing
syntax from silently diverging between them.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
KERNEL_ENTRY = ROOT / "kernel" / "src" / "main.sotlas"

sys.path.insert(0, str(ROOT / "tools"))
from sotlas.lexer import Lexer
from sotlas.parser import Parser
from sotlas.ast_nodes import FnDeclNode, StaticDeclNode


COMPILER_SPEC = importlib.util.spec_from_file_location(
    "sotlas_kernel_contract_compiler",
    ROOT / "tools" / "sotlas_compile" / "compiler.py",
)
assert COMPILER_SPEC is not None and COMPILER_SPEC.loader is not None
compiler = importlib.util.module_from_spec(COMPILER_SPEC)
COMPILER_SPEC.loader.exec_module(compiler)


SYNTAX_PROBE = """
module contract::smp;

static mut CPU_FLAGS: [u32; 4] = [0; 4];

@system
pub fn store_flag(index: usize, value: u32) -> u32 {
    unsafe {
        CPU_FLAGS[index] = value;
    }
    return CPU_FLAGS[index] as u32;
}

@system
pub fn park_cpu() -> ! {
    loop { }
}
"""


class SotlasKernelLanguageContractTests(unittest.TestCase):
    def test_rich_frontend_parses_kernel_smp_syntax(self):
        ast = Parser(Lexer(SYNTAX_PROBE, "<kernel-contract>").tokenize(), "<kernel-contract>").parse()
        statics = [decl for decl in ast.decls if isinstance(decl, StaticDeclNode)]
        functions = [decl for decl in ast.decls if isinstance(decl, FnDeclNode)]

        self.assertEqual(len(statics), 1)
        self.assertTrue(statics[0].is_var)
        self.assertTrue(statics[0].type_ann.is_array)
        self.assertEqual({fn.name for fn in functions}, {"store_flag", "park_cpu"})
        park = next(fn for fn in functions if fn.name == "park_cpu")
        self.assertIsNotNone(park.ret)
        self.assertEqual(park.ret.name, "!")

    def test_bootstrap_frontend_typechecks_and_lowers_same_kernel_syntax(self):
        bootstrap = compiler._bootstrap_backend()
        module = bootstrap.parse(SYNTAX_PROBE, filename="<kernel-contract>")
        bootstrap.check(module)
        emitted = bootstrap.emit_c(module)

        self.assertIn("CPU_FLAGS", emitted)
        self.assertIn("store_flag", emitted)
        self.assertIn("park_cpu", emitted)

    def test_active_kernel_modules_pass_real_bootstrap_semantics_and_lowering(self):
        _, manifest, units, interface_asts = compiler.frontend(KERNEL_ENTRY)
        bootstrap = compiler._bootstrap_backend()
        parsed = {
            module_name: bootstrap.parse(
                units[module_name]["text"],
                filename=str(units[module_name]["path"]),
            )
            for module_name in manifest["compile_order"]
        }

        critical_modules = (
            "kernel::sync::spinlock",
            "kernel::scheduler::core",
            "kernel::interrupts::irq",
            "kernel::arch::x86_64::smp",
        )
        for module_name in critical_modules:
            with self.subTest(module=module_name):
                self.assertIn(module_name, parsed)
                dependencies = [parsed[name] for name in interface_asts[module_name].imports]
                emitted = bootstrap.compile_module(
                    parsed[module_name],
                    imported_modules=dependencies,
                    include_import_headers=False,
                )
                self.assertTrue(emitted.strip())

    def test_compiler_lowering_is_owned_by_bootstrap_not_regex_body_synthesis(self):
        source = (ROOT / "tools" / "sotlas_compile" / "compiler.py").read_text(encoding="utf-8")
        emit_body = source.split("def emit_c_module", 1)[1].split("def frontend", 1)[0]
        self.assertIn("bootstrap.parse", emit_body)
        self.assertIn("bootstrap.compile_module", emit_body)
        self.assertNotIn("gfx_", emit_body)
        self.assertNotIn("draw_", emit_body)


if __name__ == "__main__":
    unittest.main()

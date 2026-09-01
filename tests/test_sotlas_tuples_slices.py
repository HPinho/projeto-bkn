#!/usr/bin/env python3
"""Testes de tuplas, slices, operador de erro (?) e defer na linguagem Sotlas."""

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from sotlas import compile_source
from sotlas.lexer import Lexer
from sotlas.parser import Parser
from sotlas.sema import Sema
from sotlas.codegen_c import CodegenC
from sotlas.token_types import TK


class SotlasTuplesAndSlicesTests(unittest.TestCase):
    def parse_src(self, code: str):
        tokens = Lexer(code, "<test>").tokenize()
        return Parser(tokens, "<test>").parse()

    def check_src(self, code: str):
        ast = self.parse_src(code)
        Sema(ast, "<test>").check()
        return ast

    def compile_src(self, code: str) -> str:
        ast = self.check_src(code)
        return CodegenC(ast).emit()

    def test_tuple_type_and_literal(self):
        code = """
        module test::tuples;

        pub fn get_pair() -> (u32, bool) {
            let p: (u32, bool) = (100, true);
            return p;
        }
        """
        c_code = self.compile_src(code)
        self.assertIn("struct { uint32_t _0; uint8_t _1; }", c_code)
        self.assertIn("{ ._0 = 100, ._1 = 1 }", c_code)

    def test_tuple_index_access(self):
        code = """
        module test::tuple_access;

        pub fn sum_pair(pair: (u32, u32)) -> u32 {
            let first: u32 = pair.0;
            let second: u32 = pair.1;
            return first + second;
        }
        """
        c_code = self.compile_src(code)
        self.assertIn("pair._0", c_code)
        self.assertIn("pair._1", c_code)

    def test_slice_type_and_subslice(self):
        code = """
        module test::slices;

        pub fn process_slice(buf: [u8]) -> usize {
            let sub: [u8] = buf[2 .. 8];
            return 6;
        }
        """
        c_code = self.compile_src(code)
        self.assertIn("struct { uint8_t* data; size_t len; }", c_code)
        self.assertIn(".data = _b + (2)", c_code)
        self.assertIn(".len = (size_t)((8) - (2))", c_code)

    def test_try_operator_propagation(self):
        code = """
        module test::try_op;

        pub struct ResultVal {
            pub status: u32;
            pub value: u32;
        }

        pub fn get_val() -> ResultVal {
            return ResultVal { status: 0, value: 42 };
        }

        pub fn compute() -> ResultVal {
            let v: u32 = get_val()?.value;
            return ResultVal { status: 0, value: v * 2 };
        }
        """
        c_code = self.compile_src(code)
        self.assertIn("if (_res.status != 0) return _res;", c_code)

    def test_defer_with_early_return(self):
        code = """
        module test::defer_early;

        static mut CLEANED: bool = false;

        pub fn cleanup() -> void {
            unsafe { CLEANED = true; }
        }

        pub fn run_with_defer(should_exit: bool) -> u32 {
            defer cleanup();
            if should_exit {
                return 10;
            }
            return 20;
        }
        """
        c_code = self.compile_src(code)
        self.assertIn("cleanup();", c_code)


if __name__ == "__main__":
    unittest.main()

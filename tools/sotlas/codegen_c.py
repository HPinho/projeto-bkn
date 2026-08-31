"""Sotlas CodeGen C99 — Emissor freestanding a partir da AST Sotlas."""
from __future__ import annotations
from io import StringIO
from typing import List, Optional
from .token_types import TK, PRIMITIVE_C_MAP
from .ast_nodes import *

# Preâmbulo C99 freestanding padrão
_PRELUDE = """\
/* Gerado automaticamente pelo compilador Sotlas Bootstrap v0.1.0 */
/* NÃO EDITE — arquivo gerado a partir de código-fonte .st          */
#include <stdint.h>
#include <stddef.h>
"""

_BARECORE_PRELUDE = """\
/* Gerado automaticamente pelo compilador Sotlas Bootstrap v0.1.0 */
/* Módulo BARECORE — freestanding sem libc                          */
typedef unsigned char      uint8_t;
typedef unsigned short     uint16_t;
typedef unsigned int       uint32_t;
typedef unsigned long long uint64_t;
typedef signed char        int8_t;
typedef signed short       int16_t;
typedef signed int         int32_t;
typedef signed long long   int64_t;
typedef uint64_t           uintptr_t;
typedef int64_t            intptr_t;
typedef uint64_t           size_t;
typedef int64_t            ptrdiff_t;
"""

# Mapeamento de operadores binários
_BIN_OP_MAP = {
    TK.EQ: "==", TK.NEQ: "!=", TK.AND: "&&", TK.OR: "||",
    TK.LAND: "&", TK.LOR: "|", TK.XOR: "^",
    TK.SHL: "<<", TK.SHR: ">>",
    TK.LT: "<", TK.LTE: "<=", TK.GT: ">", TK.GTE: ">=",
    TK.PLUS: "+", TK.MINUS: "-", TK.STAR: "*",
    TK.SLASH: "/", TK.PERCENT: "%",
    TK.NIL_COAL: "/* ?? */",
}

_UNARY_OP_MAP = {
    TK.NOT: "!", TK.MINUS: "-", TK.TILDE: "~",
    TK.STAR: "*", TK.LAND: "&",
}

_ASSIGN_OP_MAP = {
    TK.ASSIGN: "=", TK.PLUS_EQ: "+=", TK.MINUS_EQ: "-=",
    TK.STAR_EQ: "*=", TK.SLASH_EQ: "/=", TK.PCT_EQ: "%=",
    TK.AND_EQ: "&=", TK.OR_EQ: "|=", TK.XOR_EQ: "^=",
    TK.SHL_EQ: "<<=", TK.SHR_EQ: ">>=",
}


class CodegenC:
    """Emite código C99 freestanding a partir de um SourceFileNode Sotlas."""

    def __init__(self, ast: SourceFileNode) -> None:
        self._ast = ast
        self._out = StringIO()
        self._indent = 0
        self._vtables: List[str] = []   # vtables de métodos moldable

    def emit(self) -> str:
        a = self._ast
        if a.is_barecore:
            self._w(_BARECORE_PRELUDE)
        else:
            self._w(_PRELUDE)
        self._w(f"\n/* módulo: {'.'.join(a.module.path)} */\n\n")

        # Declarações antecipadas (forward declarations)
        for decl in a.decls:
            if isinstance(decl, StructDeclNode):
                self._w(f"typedef struct {decl.name} {decl.name};\n")
            elif isinstance(decl, ClassDeclNode):
                self._w(f"typedef struct {decl.name} {decl.name};\n")
                self._w(f"typedef struct {decl.name}Vtable {decl.name}Vtable;\n")
            elif isinstance(decl, MeshDeclNode):
                self._w(f"typedef struct {decl.name} {decl.name};\n")
            elif isinstance(decl, EnumDeclNode):
                self._w(f"typedef enum {decl.name} {decl.name};\n")
        self._w("\n")

        # Declarações completas
        for decl in a.decls:
            self._emit_top_decl(decl)

        # Vtables acumuladas
        if self._vtables:
            self._w("\n/* --- Vtables Geradas --- */\n")
            for vt in self._vtables:
                self._w(vt)

        return self._out.getvalue()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _w(self, s: str) -> None:
        self._out.write(s)

    def _line(self, s: str = "") -> None:
        self._out.write("    " * self._indent + s + "\n")

    def _indent_inc(self) -> None:
        self._indent += 1

    def _indent_dec(self) -> None:
        self._indent = max(0, self._indent - 1)

    # ------------------------------------------------------------------
    # Tipos
    # ------------------------------------------------------------------

    def _emit_type(self, t: TypeNode, name: str = "") -> str:
        """Retorna a representação C do tipo, com nome de variável opcional."""
        if t.is_array:
            inner = self._emit_type(TypeNode(
                t.span, None, None, False, t.primitive, t.name,
                False, False, None, None, None, t.generic_args
            ))
            if t.array_size:
                sz = self._emit_expr(t.array_size)
                return f"{inner} {name}[{sz}]" if name else f"{inner}[]"
            return f"{inner}*"

        if t.is_topology_ptr:
            inner = self._emit_bare_type(t)
            mod = ""
            if t.topology_mut:
                mod = ""
            else:
                mod = " const"
            topo = {
                TK.KW_RAWPHYS: f"volatile {inner}*{mod}",
                TK.KW_VIRTMAP: f"volatile {inner}*{mod}",
                TK.KW_PORTWIRE: f"volatile {inner}*{mod} __attribute__((io_port))",
                TK.KW_DMAZONE: f"{inner}* __attribute__((aligned(64)))",
                TK.KW_VOIDZERO: "void*",
                TK.KW_MUT: f"{inner}*",
                TK.KW_CONST_MOD: f"const {inner}*",
            }
            return topo.get(t.topology_ptr, f"{inner}*")

        return self._emit_bare_type(t)

    def _emit_bare_type(self, t: TypeNode) -> str:
        if t.primitive is not None:
            if t.is_bounded:
                # Bounded type → tipo primitivo C com comentário de range
                c_type = PRIMITIVE_C_MAP.get(t.primitive, "int")
                lo = self._emit_expr(t.bounded_lo) if t.bounded_lo else "?"
                hi = self._emit_expr(t.bounded_hi) if t.bounded_hi else "?"
                return f"{c_type} /* bound[{lo}..{hi}] */"
            return PRIMITIVE_C_MAP.get(t.primitive, "int")
        if t.name:
            return t.name
        return "void"

    # ------------------------------------------------------------------
    # Declarações de Topo
    # ------------------------------------------------------------------

    def _emit_top_decl(self, decl) -> None:
        if isinstance(decl, StructDeclNode):
            self._emit_struct(decl)
        elif isinstance(decl, ClassDeclNode):
            self._emit_class(decl)
        elif isinstance(decl, MeshDeclNode):
            self._emit_mesh(decl)
        elif isinstance(decl, EnumDeclNode):
            self._emit_enum(decl)
        elif isinstance(decl, ConstDeclNode):
            self._emit_const(decl)
        elif isinstance(decl, StaticDeclNode):
            self._emit_static(decl)
        elif isinstance(decl, FnDeclNode):
            self._emit_fn(decl)
        elif isinstance(decl, TrapFnDeclNode):
            self._emit_trapfn(decl)
        elif isinstance(decl, TypeAliasDeclNode):
            self._emit_typealias(decl)
        elif isinstance(decl, MouldBlockNode):
            self._w("\n/* mould block */\n")
            for stmt in decl.body:
                self._emit_stmt(stmt)

    def _emit_struct(self, decl: StructDeclNode) -> None:
        self._w(f"struct {decl.name} {{\n")
        self._indent_inc()
        for m in decl.members:
            if isinstance(m, FieldDeclNode):
                self._emit_field(m)
        self._indent_dec()
        self._w("};\n\n")
        # Funções membro
        for m in decl.members:
            if isinstance(m, FnDeclNode):
                m2 = FnDeclNode(m.span, m.directives, m.is_pub, m.is_irqfree,
                                m.is_async, m.is_moldable, m.is_reshape,
                                f"{decl.name}__{m.name}", m.generics, m.params, m.ret, m.body)
                self._emit_fn(m2)

    def _emit_class(self, decl: ClassDeclNode) -> None:
        # Emitir vtable se houver métodos moldable
        moldable_fns = [m for m in decl.members
                        if isinstance(m, FnDeclNode) and (m.is_moldable or m.is_reshape)]
        if moldable_fns:
            vt = StringIO()
            vt.write(f"struct {decl.name}Vtable {{\n")
            for m in moldable_fns:
                ret = self._emit_type(m.ret) if m.ret else "void"
                params = ", ".join(self._emit_type(p.type_ann) for p in m.params)
                vt.write(f"    {ret} (*{m.name})({decl.name}* self{(', ' + params) if params else ''});\n")
            vt.write("};\n\n")
            self._vtables.append(vt.getvalue())

        self._w(f"struct {decl.name} {{\n")
        self._indent_inc()
        if moldable_fns:
            self._line(f"const {decl.name}Vtable* vtable;")
        for m in decl.members:
            if isinstance(m, FieldDeclNode):
                self._emit_field(m)
        self._indent_dec()
        self._w("};\n\n")
        for m in decl.members:
            if isinstance(m, FnDeclNode):
                m2 = FnDeclNode(m.span, m.directives, m.is_pub, m.is_irqfree,
                                m.is_async, m.is_moldable, m.is_reshape,
                                f"{decl.name}__{m.name}", m.generics, m.params, m.ret, m.body)
                self._emit_fn(m2)

    def _emit_mesh(self, decl: MeshDeclNode) -> None:
        self._w(f"struct {decl.name} {{\n")
        self._indent_inc()
        for m in decl.members:
            c_type = self._emit_type(m.type_ann)
            if m.align:
                align = self._emit_expr(m.align)
                self._line(f"{c_type} {m.name} __attribute__((aligned({align})));")
            else:
                self._line(f"{c_type} {m.name};")
        self._indent_dec()
        self._w("};\n\n")

    def _emit_enum(self, decl: EnumDeclNode) -> None:
        backing = self._emit_type(decl.backing_type) if decl.backing_type else "int"
        self._w(f"enum {decl.name} /* : {backing} */ {{\n")
        for v in decl.variants:
            if v.value:
                self._w(f"    {decl.name}__{v.name} = {self._emit_expr(v.value)},\n")
            else:
                self._w(f"    {decl.name}__{v.name},\n")
        self._w("};\n\n")

    def _emit_const(self, decl: ConstDeclNode) -> None:
        c_type = self._emit_type(decl.type_ann)
        val = self._emit_expr(decl.value)
        self._w(f"static const {c_type} {decl.name} = {val};\n\n")

    def _emit_static(self, decl: StaticDeclNode) -> None:
        attrs = ""
        if decl.modifier == TK.KW_SHIELDED:
            attrs = " volatile"
        elif decl.modifier == TK.KW_NVKEEP:
            attrs = " __attribute__((section(\".nvdata\")))"
        elif decl.modifier == TK.KW_SEAL:
            attrs = " __attribute__((section(\".rodata\")))"
        prefix = "" if decl.is_var else "const "
        c_type = self._emit_type(decl.type_ann)
        val = self._emit_expr(decl.value)
        self._w(f"static {prefix}{c_type}{attrs} {decl.name} = {val};\n\n")

    def _emit_typealias(self, decl: TypeAliasDeclNode) -> None:
        c_type = self._emit_type(decl.alias)
        self._w(f"typedef {c_type} {decl.name};\n\n")

    def _emit_field(self, f: FieldDeclNode) -> None:
        attrs = ""
        if f.is_shielded:
            attrs += " volatile"
        if f.is_nvkeep:
            attrs += " __attribute__((section(\".nvdata\")))"
        if f.is_seal:
            attrs += " __attribute__((section(\".rodata\")))"
        prefix = "" if f.is_var else "const "
        # Array field: precisa de tratamento especial
        if f.type_ann.is_array and f.type_ann.array_size:
            inner_t = TypeNode(
                f.type_ann.span, f.type_ann.ownership, f.type_ann.topology_ptr,
                f.type_ann.topology_mut, f.type_ann.primitive, f.type_ann.name,
                False, False, None, None, None
            )
            c_type = self._emit_type(inner_t)
            sz = self._emit_expr(f.type_ann.array_size)
            self._line(f"{prefix}{c_type}{attrs} {f.name}[{sz}];")
        else:
            c_type = self._emit_type(f.type_ann)
            self._line(f"{prefix}{c_type}{attrs} {f.name};")

    def _emit_fn(self, decl: FnDeclNode) -> None:
        if decl.body is None:
            return
        attrs = ""
        if decl.is_irqfree:
            attrs += " __attribute__((no_caller_saved_registers))"
        ret = self._emit_type(decl.ret) if decl.ret else "void"
        params = ", ".join(
            f"{self._emit_type(p.type_ann)} {p.name}" for p in decl.params
        ) or "void"
        self._w(f"{ret}{attrs} {decl.name}({params}) {{\n")
        self._indent_inc()
        for stmt in decl.body:
            self._emit_stmt(stmt)
        self._indent_dec()
        self._w("}\n\n")

    def _emit_trapfn(self, decl: TrapFnDeclNode) -> None:
        ret = self._emit_type(decl.ret) if decl.ret else "void"
        params = ", ".join(
            f"{self._emit_type(p.type_ann)} {p.name}" for p in decl.params
        ) or "void"
        self._w(f"__attribute__((interrupt)) {ret} {decl.name}({params}) {{\n")
        self._indent_inc()
        for stmt in decl.body:
            self._emit_stmt(stmt)
        self._indent_dec()
        self._w("}\n\n")

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _emit_stmt(self, stmt: StmtNode) -> None:
        if isinstance(stmt, LocalVarDeclNode):
            self._emit_local_var(stmt)
        elif isinstance(stmt, AssignmentNode):
            op = _ASSIGN_OP_MAP.get(stmt.op, "=")
            self._line(f"{self._emit_expr(stmt.target)} {op} {self._emit_expr(stmt.value)};")
        elif isinstance(stmt, HandoverNode):
            # Transfere posse — no C99 emite comentário de anotação SRG
            self._line(f"/* handover */ (void)({self._emit_expr(stmt.expr)});")
        elif isinstance(stmt, QuarantineNode):
            self._line(f"/* quarantine */ (void)({self._emit_expr(stmt.expr)});")
        elif isinstance(stmt, ClinchNode):
            self._emit_clinch(stmt)
        elif isinstance(stmt, QuenchNode):
            self._line("__asm__ volatile(\"sfence\" ::: \"memory\");")
            self._line("__asm__ volatile(\"mfence\" ::: \"memory\");")
            for st in stmt.body:
                self._emit_stmt(st)
        elif isinstance(stmt, GateNode):
            cond = self._emit_expr(stmt.condition)
            self._line(f"if (!({cond})) {{ __builtin_trap(); }}")
            for st in stmt.body:
                self._emit_stmt(st)
        elif isinstance(stmt, EmitNode):
            self._emit_emit(stmt)
        elif isinstance(stmt, GuardNode):
            cond = self._emit_expr(stmt.condition)
            self._line(f"if (!({cond})) {{")
            self._indent_inc()
            for st in stmt.else_body:
                self._emit_stmt(st)
            self._indent_dec()
            self._line("}")
        elif isinstance(stmt, IfNode):
            self._emit_if(stmt)
        elif isinstance(stmt, MatchNode):
            self._emit_match(stmt)
        elif isinstance(stmt, WhileNode):
            self._line(f"while ({self._emit_expr(stmt.condition)}) {{")
            self._indent_inc()
            for st in stmt.body:
                self._emit_stmt(st)
            self._indent_dec()
            self._line("}")
        elif isinstance(stmt, ForNode):
            it = self._emit_expr(stmt.iterable)
            self._line(f"/* for {stmt.var} in {it} */")
            self._line(f"for (size_t _sotlas_i = 0; _sotlas_i < sizeof({it})/sizeof(*{it}); ++_sotlas_i) {{")
            self._indent_inc()
            self._line(f"__typeof__(*{it}) {stmt.var} = {it}[_sotlas_i];")
            for st in stmt.body:
                self._emit_stmt(st)
            self._indent_dec()
            self._line("}")
        elif isinstance(stmt, UnsafeBlockNode):
            self._line("/* unsafe */")
            for st in stmt.body:
                self._emit_stmt(st)
        elif isinstance(stmt, ReturnNode):
            if stmt.value:
                self._line(f"return {self._emit_expr(stmt.value)};")
            else:
                self._line("return;")
        elif isinstance(stmt, ReboundNode):
            # rebound → iret / eret dependendo da arquitetura
            self._line("/* rebound */ __asm__ volatile(\"iretq\");")
        elif isinstance(stmt, BreakNode):
            self._line("break;")
        elif isinstance(stmt, ContinueNode):
            self._line("continue;")
        elif isinstance(stmt, ExprStmtNode):
            self._line(f"{self._emit_expr(stmt.expr)};")

    def _emit_local_var(self, stmt: LocalVarDeclNode) -> None:
        attrs = ""
        if stmt.is_shielded:
            attrs += " volatile"
        if stmt.is_nvkeep:
            attrs += " __attribute__((section(\".nvdata\")))"
        if stmt.is_seal:
            attrs += "__attribute__((section(\".rodata\")))"
        prefix = "" if stmt.is_var else "const "
        c_type = "auto" if stmt.type_ann is None else self._emit_type(stmt.type_ann)
        if c_type == "auto":
            # Inferência simples: emite sem tipo explícito (usando __typeof__ seria mais correto)
            c_type = "/* auto */"
        val = self._emit_expr(stmt.init)
        self._line(f"{prefix}{c_type}{attrs} {stmt.name} = {val};")

    def _emit_clinch(self, stmt: ClinchNode) -> None:
        """clinch { body } revert { cleanup } → cli/sti com goto de limpeza."""
        self._line("{")
        self._indent_inc()
        self._line("__asm__ volatile(\"cli\" ::: \"memory\"); /* clinch: início de seção crítica */")
        for st in stmt.body:
            self._emit_stmt(st)
        if stmt.revert:
            self._line("__asm__ volatile(\"sti\" ::: \"memory\"); /* clinch: fim normal */")
            self._line("goto _sotlas_clinch_end;")
            self._line("/* revert: restauração de contexto */")
            for st in stmt.revert:
                self._emit_stmt(st)
            self._line("_sotlas_clinch_end:;")
        else:
            self._line("__asm__ volatile(\"sti\" ::: \"memory\"); /* clinch: fim */")
        self._indent_dec()
        self._line("}")

    def _emit_emit(self, stmt: EmitNode) -> None:
        outputs = ", ".join(f'"{self._emit_expr(e)}"' for e in stmt.outputs)
        inputs = ", ".join(f'"{self._emit_expr(e)}"' for e in stmt.inputs)
        clobbers = ", ".join(f'"{c}"' for c in stmt.clobbers)
        parts = [f'"{stmt.template}"']
        if outputs or inputs or clobbers:
            parts.append(f": {outputs}")
        if inputs or clobbers:
            parts.append(f": {inputs}")
        if clobbers:
            parts.append(f": {clobbers}")
        self._line(f'__asm__ volatile({" ".join(parts)});')

    def _emit_if(self, stmt: IfNode) -> None:
        cond = self._emit_expr(stmt.condition)
        self._line(f"if ({cond}) {{")
        self._indent_inc()
        for st in stmt.then_body:
            self._emit_stmt(st)
        self._indent_dec()
        if stmt.else_body:
            if isinstance(stmt.else_body, IfNode):
                self._line("} else ")
                self._emit_if(stmt.else_body)
                return
            else:
                self._line("} else {")
                self._indent_inc()
                for st in stmt.else_body:
                    self._emit_stmt(st)
                self._indent_dec()
        self._line("}")

    def _emit_match(self, stmt: MatchNode) -> None:
        subj = self._emit_expr(stmt.subject)
        self._line(f"switch ({subj}) {{")
        self._indent_inc()
        for arm in stmt.arms:
            pat = arm.pattern
            if pat.kind == "wildcard":
                self._line("default:")
            elif pat.kind == "literal":
                val = self._emit_expr(pat.value) if isinstance(pat.value, LiteralNode) else str(pat.value)
                self._line(f"case {val}:")
            elif pat.kind in ("ident", "enum_variant"):
                self._line(f"case {pat.value}:")
            self._indent_inc()
            if isinstance(arm.body, list):
                for st in arm.body:
                    self._emit_stmt(st)
            self._line("break;")
            self._indent_dec()
        self._indent_dec()
        self._line("}")

    # ------------------------------------------------------------------
    # Expressões
    # ------------------------------------------------------------------

    def _emit_expr(self, expr: ExprNode) -> str:
        if expr is None:
            return "0"
        if isinstance(expr, LiteralNode):
            return self._emit_literal(expr)
        if isinstance(expr, IdentNode):
            parts = expr.path + [expr.name]
            return "__".join(parts)
        if isinstance(expr, BinaryExprNode):
            op = _BIN_OP_MAP.get(expr.op, "?")
            return f"({self._emit_expr(expr.left)} {op} {self._emit_expr(expr.right)})"
        if isinstance(expr, UnaryExprNode):
            if expr.op == TK.KW_AWAIT:
                return f"/* await */ {self._emit_expr(expr.operand)}"
            op = _UNARY_OP_MAP.get(expr.op, "")
            return f"({op}{self._emit_expr(expr.operand)})"
        if isinstance(expr, CallExprNode):
            callee = self._emit_expr(expr.callee)
            args = ", ".join(self._emit_expr(a.value) for a in expr.args)
            return f"{callee}({args})"
        if isinstance(expr, IndexExprNode):
            return f"{self._emit_expr(expr.base)}[{self._emit_expr(expr.index)}]"
        if isinstance(expr, FieldExprNode):
            return f"{self._emit_expr(expr.base)}.{expr.field}"
        if isinstance(expr, BitSliceExprNode):
            # base.slit[lo..hi] → (((base) >> (lo)) & ((1ULL << ((hi)-(lo)+1)) - 1))
            b = self._emit_expr(expr.base)
            lo = self._emit_expr(expr.lo)
            hi = self._emit_expr(expr.hi)
            return f"((({b}) >> ({lo})) & ((1ULL << (({hi})-({lo})+1)) - 1))"
        if isinstance(expr, BitNotchExprNode):
            # base.notch[n] → (((base) >> (n)) & 1ULL)
            b = self._emit_expr(expr.base)
            n = self._emit_expr(expr.bit)
            return f"((({b}) >> ({n})) & 1ULL)"
        if isinstance(expr, BitStrandExprNode):
            # base.strand → __builtin_bswap64(base)  (endianness flip)
            b = self._emit_expr(expr.base)
            return f"__builtin_bswap64({b})"
        if isinstance(expr, CastExprNode):
            c_type = self._emit_type(expr.target_type)
            return f"(({c_type})({self._emit_expr(expr.expr)}))"
        if isinstance(expr, (OptionalChainExprNode, ForceUnwrapExprNode)):
            return self._emit_expr(expr.expr)
        if isinstance(expr, ArrayLitExprNode):
            elems = ", ".join(self._emit_expr(e) for e in expr.elements)
            return f"{{{elems}}}"
        if isinstance(expr, ClosureExprNode):
            return "/* closure */(void*)0"
        if isinstance(expr, ArgNode):
            return self._emit_expr(expr.value)
        return "/* unknown_expr */"

    def _emit_literal(self, lit: LiteralNode) -> str:
        if lit.kind == TK.KW_TRUE:
            return "1"
        if lit.kind == TK.KW_FALSE:
            return "0"
        if lit.kind == TK.KW_NIL:
            return "((void*)0)"
        if lit.kind == TK.STR_LIT:
            return f'"{lit.value}"'
        if lit.kind == TK.CHAR_LIT:
            return f"'{lit.value}'"
        # INT_LIT e FLOAT_LIT: emite diretamente
        return lit.value

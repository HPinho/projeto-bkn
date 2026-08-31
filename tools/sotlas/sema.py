"""Sotlas Sema — Analisador Semântico e Verificador de Tipos (duas passagens)."""
from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
from .token_types import TK, PRIMITIVE_TOKENS
from .ast_nodes import *


class SotlasSemaError(Exception):
    def __init__(self, msg: str, span: Span) -> None:
        super().__init__(f"{span}: {msg}")
        self.span = span


# ---------------------------------------------------------------------------
# Tabela de Símbolos
# ---------------------------------------------------------------------------

class Symbol:
    __slots__ = ("name", "kind", "type_node", "span", "is_island")

    def __init__(self, name: str, kind: str, type_node: Optional[TypeNode],
                 span: Span, is_island: bool = False) -> None:
        self.name = name
        self.kind = kind          # "var" | "let" | "fn" | "type" | "param"
        self.type_node = type_node
        self.span = span
        self.is_island = is_island


class Scope:
    def __init__(self, parent: Optional["Scope"] = None) -> None:
        self._parent = parent
        self._syms: Dict[str, Symbol] = {}

    def define(self, sym: Symbol) -> None:
        self._syms[sym.name] = sym

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self._syms:
            return self._syms[name]
        if self._parent:
            return self._parent.lookup(name)
        return None

    def child(self) -> "Scope":
        return Scope(self)


# ---------------------------------------------------------------------------
# Sema Principal
# ---------------------------------------------------------------------------

class Sema:
    """Verificador semântico de duas passagens.

    Passagem 1: coleta todas as declarações de topo (structs, classes, fns...).
    Passagem 2: verifica corpos de funções, tipos, SRG e regras barecore.
    """

    def __init__(self, ast: SourceFileNode, filename: str = "<stdin>") -> None:
        self._ast = ast
        self._fn = filename
        self._global = Scope()
        self._is_barecore = ast.is_barecore
        # Rastreamento SRG: nomes de variáveis 'island' atualmente activas
        self._island_vars: Set[str] = set()
        self._errors: List[SotlasSemaError] = []
        # Quando True, identificadores não resolvidos são aceitos (campo de self implícito)
        self._in_method: bool = False

    def check(self) -> None:
        self._pass1_collect()
        self._pass2_verify()
        if self._errors:
            raise self._errors[0]

    def _err(self, msg: str, span: Span) -> None:
        self._errors.append(SotlasSemaError(msg, span))

    # ------------------------------------------------------------------
    # Passagem 1: Coleta de Símbolos Globais
    # ------------------------------------------------------------------

    def _pass1_collect(self) -> None:
        for decl in self._ast.decls:
            if isinstance(decl, (StructDeclNode, ClassDeclNode, MeshDeclNode,
                                 SpecDeclNode, EnumDeclNode)):
                sym = Symbol(decl.name, "type", None, decl.span)
                self._global.define(sym)
            elif isinstance(decl, FnDeclNode):
                sym = Symbol(decl.name, "fn", None, decl.span)
                self._global.define(sym)
            elif isinstance(decl, TrapFnDeclNode):
                sym = Symbol(decl.name, "fn", None, decl.span)
                self._global.define(sym)
            elif isinstance(decl, ConstDeclNode):
                sym = Symbol(decl.name, "let", decl.type_ann, decl.span)
                self._global.define(sym)
            elif isinstance(decl, StaticDeclNode):
                sym = Symbol(decl.name, "var" if decl.is_var else "let",
                             decl.type_ann, decl.span)
                self._global.define(sym)
            elif isinstance(decl, TypeAliasDeclNode):
                sym = Symbol(decl.name, "type", decl.alias, decl.span)
                self._global.define(sym)

    # ------------------------------------------------------------------
    # Passagem 2: Verificação
    # ------------------------------------------------------------------

    def _pass2_verify(self) -> None:
        for decl in self._ast.decls:
            if isinstance(decl, FnDeclNode):
                self._check_fn(decl, self._global)
            elif isinstance(decl, TrapFnDeclNode):
                self._check_trapfn(decl)
            elif isinstance(decl, StructDeclNode):
                self._check_struct(decl)
            elif isinstance(decl, ClassDeclNode):
                self._check_class(decl)
            elif isinstance(decl, StaticDeclNode):
                self._check_static(decl)
            elif isinstance(decl, ConstDeclNode):
                self._check_expr(decl.value, self._global)
            elif isinstance(decl, MouldBlockNode):
                scope = self._global.child()
                for stmt in decl.body:
                    self._check_stmt(stmt, scope)

    # ------------------------------------------------------------------
    # Declarações
    # ------------------------------------------------------------------

    def _check_struct(self, decl: StructDeclNode) -> None:
        scope = self._global.child()
        prev_in_method = self._in_method
        for member in decl.members:
            if isinstance(member, FieldDeclNode):
                self._check_type(member.type_ann, member.span)
                if self._is_barecore:
                    self._assert_no_dynamic_alloc(member.type_ann, member.span)
                if member.default:
                    self._check_expr(member.default, scope)
            elif isinstance(member, FnDeclNode):
                self._in_method = True
                self._check_fn(member, scope)
                self._in_method = prev_in_method
            elif isinstance(member, InitDeclNode):
                self._in_method = True
                self._check_init(member, scope)
                self._in_method = prev_in_method

    def _check_class(self, decl: ClassDeclNode) -> None:
        # Verificar herança
        if decl.base and not self._global.lookup(decl.base):
            self._err(f"classe base '{decl.base}' não declarada", decl.span)
        # Verificar specs adotados
        for spec_name in decl.adopts:
            if not self._global.lookup(spec_name):
                self._err(f"spec '{spec_name}' não declarado", decl.span)
        if self._is_barecore:
            self._err(
                "classes com herança dinâmica não são permitidas em módulos barecore",
                decl.span
            )
        scope = self._global.child()
        prev_in_method = self._in_method
        for member in decl.members:
            if isinstance(member, FieldDeclNode):
                self._check_type(member.type_ann, member.span)
                if member.default:
                    self._check_expr(member.default, scope)
            elif isinstance(member, FnDeclNode):
                self._in_method = True
                self._check_fn(member, scope)
                self._in_method = prev_in_method
            elif isinstance(member, InitDeclNode):
                self._in_method = True
                self._check_init(member, scope)
                self._in_method = prev_in_method
            elif isinstance(member, DeinitDeclNode):
                self._in_method = True
                s = scope.child()
                for stmt in member.body:
                    self._check_stmt(stmt, s)
                self._in_method = prev_in_method

    def _check_fn(self, decl: FnDeclNode, outer: Scope) -> None:
        if decl.body is None:
            return
        scope = outer.child()
        for param in decl.params:
            self._check_type(param.type_ann, param.span)
            if self._is_barecore:
                self._assert_no_dynamic_alloc(param.type_ann, param.span)
            sym = Symbol(param.name, "param", param.type_ann, param.span,
                         is_island=self._type_is_island(param.type_ann))
            scope.define(sym)
            if sym.is_island:
                self._island_vars.add(param.name)
        if decl.ret:
            self._check_type(decl.ret, decl.span)
            if self._is_barecore:
                self._assert_no_dynamic_alloc(decl.ret, decl.span)
        for stmt in decl.body:
            self._check_stmt(stmt, scope)
        # Limpar variáveis island do escopo ao sair
        for param in decl.params:
            self._island_vars.discard(param.name)

    def _check_trapfn(self, decl: TrapFnDeclNode) -> None:
        scope = self._global.child()
        for param in decl.params:
            self._check_type(param.type_ann, param.span)
            scope.define(Symbol(param.name, "param", param.type_ann, param.span))
        for stmt in decl.body:
            self._check_stmt(stmt, scope)

    def _check_init(self, decl: InitDeclNode, outer: Scope) -> None:
        scope = outer.child()
        for param in decl.params:
            scope.define(Symbol(param.name, "param", param.type_ann, param.span))
        for stmt in decl.body:
            self._check_stmt(stmt, scope)

    def _check_static(self, decl: StaticDeclNode) -> None:
        self._check_type(decl.type_ann, decl.span)
        if self._is_barecore:
            self._assert_no_dynamic_alloc(decl.type_ann, decl.span)
        self._check_expr(decl.value, self._global)

    # ------------------------------------------------------------------
    # Verificação de Tipos
    # ------------------------------------------------------------------

    def _check_type(self, t: TypeNode, span: Span) -> None:
        if t.is_topology_ptr:
            self._check_topology_ptr(t, span)
        if t.name and not t.is_primitive:
            if not self._global.lookup(t.name):
                self._err(f"tipo '{t.name}' não declarado", span)

    def _check_topology_ptr(self, t: TypeNode, span: Span) -> None:
        """Verifica regras de segurança de ponteiros de topologia."""
        # rawphys e virtmap não podem ser atribuídos implicitamente entre si (verificado no sema de assign)
        pass  # A verificação concreta é feita em _check_assignment_topology

    def _assert_no_dynamic_alloc(self, t: TypeNode, span: Span) -> None:
        """Em módulos barecore, tipos que implicam alocação dinâmica são proibidos."""
        if t.name in ("String", "Vec", "Box", "Rc", "Arc"):
            self._err(
                f"tipo '{t.name}' implica alocação dinâmica e não é permitido em barecore",
                span
            )
        if t.ownership in (TK.KW_CO_OWNED,):
            self._err(
                "modificador 'co-owned' usa ARC e não é permitido em barecore — use 'sole' ou 'direct'",
                span
            )

    def _type_is_island(self, t: TypeNode) -> bool:
        return t.ownership == TK.KW_ISLAND

    # ------------------------------------------------------------------
    # Verificação de Statements
    # ------------------------------------------------------------------

    def _check_stmt(self, stmt: StmtNode, scope: Scope) -> None:
        if isinstance(stmt, LocalVarDeclNode):
            self._check_local_var(stmt, scope)
        elif isinstance(stmt, AssignmentNode):
            self._check_assignment(stmt, scope)
        elif isinstance(stmt, HandoverNode):
            self._check_handover(stmt, scope)
        elif isinstance(stmt, QuarantineNode):
            self._check_quarantine(stmt, scope)
        elif isinstance(stmt, ClinchNode):
            self._check_clinch(stmt, scope)
        elif isinstance(stmt, QuenchNode):
            s = scope.child()
            for st in stmt.body:
                self._check_stmt(st, s)
        elif isinstance(stmt, GateNode):
            self._check_expr(stmt.condition, scope)
            s = scope.child()
            for st in stmt.body:
                self._check_stmt(st, s)
        elif isinstance(stmt, EmitNode):
            for e in stmt.outputs + stmt.inputs:
                self._check_expr(e, scope)
        elif isinstance(stmt, GuardNode):
            self._check_expr(stmt.condition, scope)
            s = scope.child()
            for st in stmt.else_body:
                self._check_stmt(st, s)
        elif isinstance(stmt, IfNode):
            self._check_if(stmt, scope)
        elif isinstance(stmt, MatchNode):
            self._check_expr(stmt.subject, scope)
            for arm in stmt.arms:
                s = scope.child()
                if isinstance(arm.body, list):
                    for st in arm.body:
                        self._check_stmt(st, s)
        elif isinstance(stmt, WhileNode):
            self._check_expr(stmt.condition, scope)
            s = scope.child()
            for st in stmt.body:
                self._check_stmt(st, s)
        elif isinstance(stmt, ForNode):
            self._check_expr(stmt.iterable, scope)
            s = scope.child()
            s.define(Symbol(stmt.var, "let", None, stmt.span))
            for st in stmt.body:
                self._check_stmt(st, s)
        elif isinstance(stmt, UnsafeBlockNode):
            s = scope.child()
            for st in stmt.body:
                self._check_stmt(st, s)
        elif isinstance(stmt, ReturnNode):
            if stmt.value:
                self._check_expr(stmt.value, scope)
        elif isinstance(stmt, ExprStmtNode):
            self._check_expr(stmt.expr, scope)

    def _check_local_var(self, stmt: LocalVarDeclNode, scope: Scope) -> None:
        if stmt.type_ann:
            self._check_type(stmt.type_ann, stmt.span)
            if self._is_barecore:
                self._assert_no_dynamic_alloc(stmt.type_ann, stmt.span)
        self._check_expr(stmt.init, scope)
        is_island = stmt.type_ann is not None and self._type_is_island(stmt.type_ann)
        sym = Symbol(stmt.name, "var" if stmt.is_var else "let",
                     stmt.type_ann, stmt.span, is_island=is_island)
        scope.define(sym)
        if is_island:
            self._island_vars.add(stmt.name)

    def _check_assignment(self, stmt: AssignmentNode, scope: Scope) -> None:
        self._check_expr(stmt.target, scope)
        self._check_expr(stmt.value, scope)
        # Regra de segurança: rawphys ↔ virtmap não podem ser misturados
        if isinstance(stmt.target, IdentNode):
            sym = scope.lookup(stmt.target.name)
            if sym and sym.type_node and stmt.value:
                self._check_assignment_topology(sym.type_node, stmt.span)

    def _check_assignment_topology(self, dest_type: TypeNode, span: Span) -> None:
        """Bloqueia atribuição implícita entre *rawphys e *virtmap."""
        # Esta verificação é simplificada no MVP; a versão completa rastrearia
        # o tipo da expressão-fonte.
        pass

    def _check_handover(self, stmt: HandoverNode, scope: Scope) -> None:
        """Verifica que handover é aplicado a uma variável 'sole'."""
        self._check_expr(stmt.expr, scope)
        if isinstance(stmt.expr, IdentNode):
            sym = scope.lookup(stmt.expr.name)
            if sym and sym.type_node:
                if sym.type_node.ownership not in (TK.KW_SOLE, None):
                    self._err(
                        f"'handover' só pode ser aplicado a variáveis 'sole', "
                        f"mas '{stmt.expr.name}' é '{sym.type_node.ownership}'",
                        stmt.span
                    )

    def _check_quarantine(self, stmt: QuarantineNode, scope: Scope) -> None:
        """Marca o recurso como island após quarantine."""
        self._check_expr(stmt.expr, scope)
        if isinstance(stmt.expr, IdentNode):
            sym = scope.lookup(stmt.expr.name)
            if sym:
                self._island_vars.add(stmt.expr.name)

    def _check_clinch(self, stmt: ClinchNode, scope: Scope) -> None:
        """Bloco clínico (seção crítica de hardware) — corpo e revert."""
        s = scope.child()
        for st in stmt.body:
            self._check_stmt(st, s)
        if stmt.revert:
            r = scope.child()
            for st in stmt.revert:
                self._check_stmt(st, r)

    def _check_if(self, stmt: IfNode, scope: Scope) -> None:
        self._check_expr(stmt.condition, scope)
        s = scope.child()
        if stmt.let_bind:
            s.define(Symbol(stmt.let_bind, "let", None, stmt.span))
        for st in stmt.then_body:
            self._check_stmt(st, s)
        if stmt.else_body:
            if isinstance(stmt.else_body, IfNode):
                self._check_if(stmt.else_body, scope)
            elif isinstance(stmt.else_body, list):
                es = scope.child()
                for st in stmt.else_body:
                    self._check_stmt(st, es)

    # ------------------------------------------------------------------
    # Verificação de Expressões
    # ------------------------------------------------------------------

    def _check_expr(self, expr: ExprNode, scope: Scope) -> None:
        if isinstance(expr, IdentNode):
            if expr.name in self._island_vars:
                pass  # Acesso a island é válido dentro do escopo
            elif not expr.path and not scope.lookup(expr.name):
                if not self._in_method:
                    # Fora de métodos de struct/classe: erro de símbolo não declarado
                    self._err(f"símbolo não declarado: '{expr.name}'", expr.span)
                # Dentro de método: provavelmente campo de self implícito — aceitar no MVP
        elif isinstance(expr, BinaryExprNode):
            self._check_expr(expr.left, scope)
            self._check_expr(expr.right, scope)
        elif isinstance(expr, UnaryExprNode):
            self._check_expr(expr.operand, scope)
        elif isinstance(expr, CallExprNode):
            self._check_expr(expr.callee, scope)
            for arg in expr.args:
                self._check_expr(arg.value, scope)
        elif isinstance(expr, (IndexExprNode,)):
            self._check_expr(expr.base, scope)
            self._check_expr(expr.index, scope)
        elif isinstance(expr, FieldExprNode):
            self._check_expr(expr.base, scope)
        elif isinstance(expr, BitSliceExprNode):
            self._check_expr(expr.base, scope)
            self._check_expr(expr.lo, scope)
            self._check_expr(expr.hi, scope)
        elif isinstance(expr, BitNotchExprNode):
            self._check_expr(expr.base, scope)
            self._check_expr(expr.bit, scope)
        elif isinstance(expr, BitStrandExprNode):
            self._check_expr(expr.base, scope)
        elif isinstance(expr, CastExprNode):
            self._check_expr(expr.expr, scope)
            self._check_type(expr.target_type, expr.span)
        elif isinstance(expr, (OptionalChainExprNode, ForceUnwrapExprNode)):
            self._check_expr(expr.expr, scope)
        elif isinstance(expr, ArrayLitExprNode):
            for el in expr.elements:
                self._check_expr(el, scope)
        elif isinstance(expr, ClosureExprNode):
            s = scope.child()
            for p in expr.params:
                s.define(Symbol(p, "param", None, Span(self._fn, 0, 0)))
            for st in expr.body:
                self._check_stmt(st, s)

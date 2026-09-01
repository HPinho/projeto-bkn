"""Sotlas Parser — Descida Recursiva determinística baseada na gramática Unified EBNF."""
from __future__ import annotations
from typing import List, Optional, Union
from .token_types import TK, PRIMITIVE_TOKENS, OWNERSHIP_MODS, TOPOLOGY_MODS
from .lexer import Token
from .ast_nodes import *


class SotlasParseError(Exception):
    def __init__(self, msg: str, filename: str, line: int, col: int) -> None:
        super().__init__(f"{filename}:{line}:{col}: {msg}")
        self.filename = filename
        self.line = line
        self.col = col


ASSIGN_OPS = {
    TK.ASSIGN, TK.PLUS_EQ, TK.MINUS_EQ, TK.STAR_EQ, TK.SLASH_EQ,
    TK.PCT_EQ, TK.AND_EQ, TK.OR_EQ, TK.XOR_EQ, TK.SHL_EQ, TK.SHR_EQ,
}

VISIBILITY_TOKENS = {TK.KW_PUB, TK.KW_CAPSULE, TK.KW_LINEAGE, TK.KW_PRIV}
FIELD_MOD_TOKENS = {TK.KW_SHIELDED, TK.KW_NVKEEP, TK.KW_SEAL}


class Parser:
    def __init__(self, tokens: List[Token], filename: str = "<stdin>") -> None:
        self._toks = tokens
        self._fn = filename
        self._pos = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cur(self) -> Token:
        return self._toks[self._pos]

    def _peek(self, offset: int = 1) -> Token:
        i = self._pos + offset
        return self._toks[i] if i < len(self._toks) else self._toks[-1]

    def _span(self) -> Span:
        t = self._cur()
        return Span(self._fn, t.line, t.col)

    def _advance(self) -> Token:
        tok = self._cur()
        if tok.kind != TK.EOF:
            self._pos += 1
        return tok

    def _expect(self, kind: TK, hint: str = "") -> Token:
        tok = self._cur()
        if tok.kind != kind:
            msg = f"esperado {kind.name}{(' (' + hint + ')') if hint else ''}, encontrado {tok.kind.name} ({tok.value!r})"
            raise SotlasParseError(msg, self._fn, tok.line, tok.col)
        return self._advance()

    def _match(self, *kinds: TK) -> bool:
        return self._cur().kind in kinds

    def _consume(self, kind: TK) -> bool:
        if self._cur().kind == kind:
            self._advance()
            return True
        return False

    # ------------------------------------------------------------------
    # Ponto de Entrada
    # ------------------------------------------------------------------

    def parse(self) -> SourceFileNode:
        span = self._span()
        is_barecore = False
        if self._match(TK.KW_BARECORE):
            self._advance()
            self._expect(TK.SEMICOLON)
            is_barecore = True

        module = self._parse_module_decl()
        imports: List[ImportDeclNode] = []
        while self._match(TK.KW_IMPORT, TK.KW_PUB):
            if self._cur().kind == TK.KW_PUB and self._peek().kind != TK.KW_IMPORT:
                break
            imports.append(self._parse_import_decl())

        decls = []
        while not self._match(TK.EOF):
            decls.append(self._parse_top_level_decl())

        return SourceFileNode(span, self._fn, is_barecore, module, imports, decls)

    # ------------------------------------------------------------------
    # Módulo e Imports
    # ------------------------------------------------------------------

    def _parse_module_decl(self) -> ModuleDeclNode:
        span = self._span()
        self._expect(TK.KW_MODULE)
        path = self._parse_qualified_ident()
        self._expect(TK.SEMICOLON)
        return ModuleDeclNode(span, path)

    def _parse_import_decl(self) -> ImportDeclNode:
        span = self._span()
        is_pub = self._consume(TK.KW_PUB)
        self._expect(TK.KW_IMPORT)
        path = self._parse_qualified_ident()
        items: Optional[List[str]] = None
        if self._consume(TK.DCOLON):
            if self._consume(TK.STAR):
                items = None  # wildcard *
            elif self._match(TK.LBRACE):
                self._advance()
                items = [self._expect(TK.IDENT).value]
                while self._consume(TK.COMMA):
                    if self._match(TK.RBRACE):
                        break
                    items.append(self._expect(TK.IDENT).value)
                self._expect(TK.RBRACE)
        self._expect(TK.SEMICOLON)
        return ImportDeclNode(span, is_pub, path, items)

    def _parse_qualified_ident(self) -> List[str]:
        parts = [self._expect(TK.IDENT).value]
        while self._match(TK.DCOLON) and self._peek().kind == TK.IDENT:
            self._advance()
            parts.append(self._expect(TK.IDENT).value)
        return parts

    # ------------------------------------------------------------------
    # Declarações de Topo
    # ------------------------------------------------------------------

    def _parse_top_level_decl(self):
        span = self._span()
        directives = self._parse_directives()
        is_pub = self._consume(TK.KW_PUB)

        cur = self._cur().kind
        if cur == TK.KW_STRUCT:
            return self._parse_struct_decl(span, directives, is_pub)
        if cur == TK.KW_CLASS:
            return self._parse_class_decl(span, directives, is_pub)
        if cur == TK.KW_MESH:
            return self._parse_mesh_decl(span, directives, is_pub)
        if cur == TK.KW_SPEC:
            return self._parse_spec_decl(span, directives, is_pub)
        if cur == TK.KW_ENUM:
            return self._parse_enum_decl(span, directives, is_pub)
        if cur == TK.KW_CONST_MOD:
            return self._parse_const_decl(span, directives, is_pub)
        if cur == TK.KW_STATIC:
            return self._parse_static_decl(span, directives, is_pub)
        if cur in (TK.KW_FN, TK.KW_IRQFREE, TK.KW_ASYNC):
            return self._parse_fn_decl(span, directives, is_pub, moldable=False, reshape=False)
        if cur == TK.KW_TRAPFN:
            return self._parse_trapfn_decl(span, directives, is_pub)
        if cur == TK.KW_TYPEALIAS:
            return self._parse_typealias_decl(span, is_pub)
        if cur == TK.KW_MOULD:
            return self._parse_mould_block(span, is_pub)

        tok = self._cur()
        raise SotlasParseError(
            f"declaração de topo inesperada: {tok.value!r}",
            self._fn, tok.line, tok.col
        )

    def _parse_directives(self) -> List[DirectiveNode]:
        directives = []
        while self._match(TK.AT):
            span = self._span()
            self._advance()
            name = self._expect(TK.IDENT).value
            args = []
            if self._consume(TK.LPAREN):
                while not self._match(TK.RPAREN, TK.EOF):
                    key = self._expect(TK.IDENT).value
                    val = None
                    if self._consume(TK.COLON):
                        val = self._cur().value
                        self._advance()
                    args.append((key, val))
                    self._consume(TK.COMMA)
                self._expect(TK.RPAREN)
            directives.append(DirectiveNode(span, name, args))
        return directives

    def _parse_struct_decl(self, span, directives, is_pub) -> StructDeclNode:
        self._expect(TK.KW_STRUCT)
        name = self._expect(TK.IDENT).value
        generics = self._parse_generic_params()
        adopts = self._parse_adopts()
        self._expect(TK.LBRACE)
        members = []
        while not self._match(TK.RBRACE, TK.EOF):
            members.append(self._parse_struct_member())
        self._expect(TK.RBRACE)
        return StructDeclNode(span, directives, is_pub, name, generics, adopts, members)

    def _parse_class_decl(self, span, directives, is_pub) -> ClassDeclNode:
        self._expect(TK.KW_CLASS)
        name = self._expect(TK.IDENT).value
        generics = self._parse_generic_params()
        base = None
        if self._consume(TK.COLON):
            base = self._expect(TK.IDENT).value
        elif self._match(TK.IDENT) and self._cur().value == "extends":
            self._advance()
            base = self._expect(TK.IDENT).value
        adopts = self._parse_adopts()
        self._expect(TK.LBRACE)
        members = []
        while not self._match(TK.RBRACE, TK.EOF):
            members.append(self._parse_class_member())
        self._expect(TK.RBRACE)
        return ClassDeclNode(span, directives, is_pub, name, generics, base, adopts, members)

    def _parse_mesh_decl(self, span, directives, is_pub) -> MeshDeclNode:
        self._expect(TK.KW_MESH)
        name = self._expect(TK.IDENT).value
        self._expect(TK.LBRACE)
        members = []
        while not self._match(TK.RBRACE, TK.EOF):
            ms = self._span()
            mname = self._expect(TK.IDENT).value
            self._expect(TK.COLON)
            mtype = self._parse_type()
            align_expr = None
            if self._consume(TK.KW_ALIGN):
                self._expect(TK.LPAREN)
                align_expr = self._parse_expr()
                self._expect(TK.RPAREN)
            self._expect(TK.SEMICOLON)
            members.append(MeshMemberNode(ms, mname, mtype, align_expr))
        self._expect(TK.RBRACE)
        return MeshDeclNode(span, directives, is_pub, name, members)

    def _parse_spec_decl(self, span, directives, is_pub) -> SpecDeclNode:
        self._expect(TK.KW_SPEC)
        name = self._expect(TK.IDENT).value
        generics = self._parse_generic_params()
        self._expect(TK.LBRACE)
        members = []
        while not self._match(TK.RBRACE, TK.EOF):
            ms = self._span()
            irqfree = self._consume(TK.KW_IRQFREE)
            async_ = self._consume(TK.KW_ASYNC)
            fn_decl = self._parse_fn_decl(ms, [], False, moldable=False, reshape=False, signature_only=True)
            members.append(SpecMemberNode(ms, irqfree, async_, fn_decl))
        self._expect(TK.RBRACE)
        return SpecDeclNode(span, directives, is_pub, name, generics, members)

    def _parse_enum_decl(self, span, directives, is_pub) -> EnumDeclNode:
        self._expect(TK.KW_ENUM)
        name = self._expect(TK.IDENT).value
        backing = None
        if self._consume(TK.COLON):
            backing = self._parse_type()
        self._expect(TK.LBRACE)
        variants = []
        while not self._match(TK.RBRACE, TK.EOF):
            vs = self._span()
            vname = self._expect(TK.IDENT).value
            params = []
            if self._consume(TK.LPAREN):
                params = self._parse_param_list()
                self._expect(TK.RPAREN)
            discriminant = None
            if self._consume(TK.ASSIGN):
                discriminant = self._parse_expr()
            self._consume(TK.COMMA)
            variants.append(EnumVariantNode(vs, vname, params, discriminant))
        self._expect(TK.RBRACE)
        return EnumDeclNode(span, directives, is_pub, name, backing, variants)

    def _parse_const_decl(self, span, directives, is_pub) -> ConstDeclNode:
        self._expect(TK.KW_CONST_MOD)
        name = self._expect(TK.IDENT).value
        self._expect(TK.COLON)
        typ = self._parse_type()
        self._expect(TK.ASSIGN)
        val = self._parse_expr()
        self._expect(TK.SEMICOLON)
        return ConstDeclNode(span, directives, is_pub, name, typ, val)

    def _parse_static_decl(self, span, directives, is_pub) -> StaticDeclNode:
        self._expect(TK.KW_STATIC)
        shielded = nvkeep = seal = False
        if self._match(*FIELD_MOD_TOKENS):
            m = self._advance().kind
            shielded = m == TK.KW_SHIELDED
            nvkeep = m == TK.KW_NVKEEP
            seal = m == TK.KW_SEAL
        is_var = self._cur().kind in (TK.KW_VAR, TK.KW_MUT)
        if self._match(TK.KW_VAR, TK.KW_LET, TK.KW_MUT, TK.KW_CONST_MOD):
            self._advance()
        name = self._expect(TK.IDENT).value
        self._expect(TK.COLON)
        typ = self._parse_type()
        self._expect(TK.ASSIGN)
        val = self._parse_expr()
        self._expect(TK.SEMICOLON)
        return StaticDeclNode(span, directives, is_pub, None, is_var, name, typ, val)

    def _parse_fn_decl(self, span, directives, is_pub,
                       moldable=False, reshape=False, signature_only=False) -> FnDeclNode:
        irqfree = self._consume(TK.KW_IRQFREE)
        async_ = self._consume(TK.KW_ASYNC)
        self._expect(TK.KW_FN)
        name = self._expect(TK.IDENT).value
        generics = self._parse_generic_params()
        self._expect(TK.LPAREN)
        params = self._parse_param_list()
        self._expect(TK.RPAREN)
        ret = None
        if self._consume(TK.ARROW):
            ret = self._parse_type()
        if signature_only:
            self._expect(TK.SEMICOLON)
            return FnDeclNode(span, directives, is_pub, irqfree, async_, moldable, reshape, name, generics, params, ret, None)
        body = self._parse_block()
        return FnDeclNode(span, directives, is_pub, irqfree, async_, moldable, reshape, name, generics, params, ret, body)

    def _parse_trapfn_decl(self, span, directives, is_pub) -> TrapFnDeclNode:
        self._expect(TK.KW_TRAPFN)
        name = self._expect(TK.IDENT).value
        self._expect(TK.LPAREN)
        params = self._parse_param_list()
        self._expect(TK.RPAREN)
        ret = None
        if self._consume(TK.ARROW):
            ret = self._parse_type()
        body = self._parse_block()
        return TrapFnDeclNode(span, directives, is_pub, name, params, ret, body)

    def _parse_typealias_decl(self, span, is_pub) -> TypeAliasDeclNode:
        self._expect(TK.KW_TYPEALIAS)
        name = self._expect(TK.IDENT).value
        generics = self._parse_generic_params()
        self._expect(TK.ASSIGN)
        alias = self._parse_type()
        self._expect(TK.SEMICOLON)
        return TypeAliasDeclNode(span, is_pub, name, generics, alias)

    def _parse_mould_block(self, span, is_pub) -> MouldBlockNode:
        self._expect(TK.KW_MOULD)
        body = self._parse_block()
        return MouldBlockNode(span, is_pub, body)

    # ------------------------------------------------------------------
    # Membros de Struct e Classe
    # ------------------------------------------------------------------

    def _parse_struct_member(self):
        span = self._span()
        directives = self._parse_directives()
        vis = None
        if self._match(*VISIBILITY_TOKENS):
            vis = self._advance().kind
        if self._match(TK.KW_INIT):
            return self._parse_init_decl(span, vis)
        if self._match(TK.KW_FN, TK.KW_IRQFREE, TK.KW_ASYNC):
            return self._parse_fn_decl(span, directives, vis == TK.KW_PUB)
        return self._parse_field_decl(span, directives, vis)

    def _parse_class_member(self):
        span = self._span()
        directives = self._parse_directives()
        vis = None
        if self._match(*VISIBILITY_TOKENS):
            vis = self._advance().kind
        if self._match(TK.KW_DEINIT):
            self._advance()
            body = self._parse_block()
            return DeinitDeclNode(span, body)
        if self._match(TK.KW_INIT):
            return self._parse_init_decl(span, vis)
        moldable = self._consume(TK.KW_MOLDABLE)
        reshape = self._consume(TK.KW_RESHAPE)
        if not reshape and self._match(TK.IDENT) and self._cur().value == "override":
            self._advance()
            reshape = True
        if self._match(TK.KW_FN, TK.KW_IRQFREE, TK.KW_ASYNC):
            return self._parse_fn_decl(span, directives, vis == TK.KW_PUB,
                                       moldable=moldable, reshape=reshape)
        return self._parse_field_decl(span, directives, vis)

    def _parse_field_decl(self, span, directives, vis) -> FieldDeclNode:
        shielded = nvkeep = seal = False
        if self._match(*FIELD_MOD_TOKENS):
            m = self._advance().kind
            shielded = m == TK.KW_SHIELDED
            nvkeep = m == TK.KW_NVKEEP
            seal = m == TK.KW_SEAL
        is_var = False
        if self._match(TK.KW_VAR, TK.KW_LET, TK.KW_MUT):
            is_var = self._cur().kind in (TK.KW_VAR, TK.KW_MUT)
            self._advance()
        name = self._expect(TK.IDENT).value
        self._expect(TK.COLON)
        typ = self._parse_type()
        default = None
        if self._consume(TK.ASSIGN):
            default = self._parse_expr()
        self._expect(TK.SEMICOLON)
        return FieldDeclNode(span, directives, vis, is_var, shielded, nvkeep, seal, name, typ, default)

    def _parse_init_decl(self, span, vis) -> InitDeclNode:
        self._expect(TK.KW_INIT)
        self._expect(TK.LPAREN)
        params = self._parse_param_list()
        self._expect(TK.RPAREN)
        body = self._parse_block()
        return InitDeclNode(span, vis, params, body)

    def _parse_param_list(self) -> List[ParamNode]:
        params = []
        if self._match(TK.RPAREN, TK.RBRACE, TK.EOF):
            return params
        params.append(self._parse_param())
        while self._consume(TK.COMMA):
            if self._match(TK.RPAREN, TK.RBRACE, TK.EOF):
                break
            params.append(self._parse_param())
        return params

    def _parse_param(self) -> ParamNode:
        span = self._span()
        # label name: Type  OR  name: Type
        label = None
        name = self._expect(TK.IDENT).value
        if self._match(TK.IDENT):
            label = name
            name = self._advance().value
        self._expect(TK.COLON)
        typ = self._parse_type()
        default = None
        if self._consume(TK.ASSIGN):
            default = self._parse_expr()
        return ParamNode(span, label, name, typ, default)

    def _parse_generic_params(self) -> List[str]:
        if not self._match(TK.LT):
            return []
        self._advance()
        names = [self._expect(TK.IDENT).value]
        while self._consume(TK.COMMA):
            if self._match(TK.GT):
                break
            names.append(self._expect(TK.IDENT).value)
        self._expect(TK.GT)
        return names

    def _parse_adopts(self) -> List[str]:
        if not self._consume(TK.KW_ADOPTS):
            return []
        names = [self._expect(TK.IDENT).value]
        while self._consume(TK.COMMA):
            names.append(self._expect(TK.IDENT).value)
        return names

    # ------------------------------------------------------------------
    # Tipos
    # ------------------------------------------------------------------

    def _parse_type(self) -> TypeNode:
        span = self._span()
        ownership = None
        if self._cur().kind in OWNERSHIP_MODS:
            ownership = self._advance().kind

        topology_ptr = None
        topology_mut = False
        if self._match(TK.STAR):
            self._advance()
            if self._cur().kind in TOPOLOGY_MODS:
                topology_ptr = self._advance().kind
                if self._consume(TK.KW_MUT):
                    topology_mut = True
                # voidzero e alguns qualifiers podem não ter tipo subsequente
                if topology_ptr == TK.KW_VOIDZERO:
                    is_optional = self._consume(TK.QMARK)
                    return TypeNode(span, ownership, topology_ptr, topology_mut,
                                    None, None, is_optional, False, None, None, None)
            else:
                # *mut T — ponteiro mutável simples
                topology_ptr = TK.KW_MUT
        elif self._match(TK.LAND):
            self._advance()
            topology_mut = self._consume(TK.KW_MUT)
            topology_ptr = TK.KW_MUT if topology_mut else TK.KW_CONST_MOD

        # Tuple type (T1, T2, ...) ou ()
        if self._match(TK.LPAREN):
            self._advance()
            elements = []
            if not self._match(TK.RPAREN):
                elements.append(self._parse_type())
                while self._consume(TK.COMMA):
                    if self._match(TK.RPAREN):
                        break
                    elements.append(self._parse_type())
            self._expect(TK.RPAREN)
            if len(elements) == 0:
                return TypeNode(span, ownership, topology_ptr, topology_mut,
                                TK.KW_VOID, "()", False, False, None, None, None, [],
                                is_slice=False, inner_type=None, tuple_elements=[])
            if len(elements) == 1:
                elem = elements[0]
                elem.ownership = ownership or elem.ownership
                elem.topology_ptr = topology_ptr or elem.topology_ptr
                elem.topology_mut = topology_mut or elem.topology_mut
                return elem
            return TypeNode(span, ownership, topology_ptr, topology_mut,
                            None, None, False, False, None, None, None, [],
                            is_slice=False, inner_type=None, tuple_elements=elements)

        # Array type [T; N] ou Slice type [T]
        if self._match(TK.LBRACKET):
            self._advance()
            inner = self._parse_type()
            size_expr = None
            is_array = False
            is_slice = False
            if self._consume(TK.SEMICOLON):
                size_expr = self._parse_expr()
                is_array = True
            else:
                is_slice = True
            self._expect(TK.RBRACKET)
            return TypeNode(span, ownership, topology_ptr, topology_mut,
                            None, None, False, is_array, size_expr, None, None, [],
                            is_slice=is_slice, inner_type=inner)

        # Tipo primitivo ou identificador
        primitive = None
        name = None
        generic_args: List[TypeNode] = []
        bounded_lo = bounded_hi = None

        if self._cur().kind in PRIMITIVE_TOKENS:
            primitive = self._advance().kind
            if self._consume(TK.DOT):
                self._expect(TK.KW_BOUND)
                self._expect(TK.LBRACKET)
                bounded_lo = self._parse_expr()
                self._expect(TK.DOTDOT)
                bounded_hi = self._parse_expr()
                self._expect(TK.RBRACKET)
        elif self._match(TK.NOT):
            self._advance()
            name = "!"
            primitive = TK.KW_VOID
        elif self._match(TK.IDENT):
            name = self._advance().value
            if self._match(TK.LT):
                self._advance()
                generic_args.append(self._parse_type())
                while self._consume(TK.COMMA):
                    generic_args.append(self._parse_type())
                self._expect(TK.GT)
        else:
            tok = self._cur()
            raise SotlasParseError(
                f"tipo esperado, encontrado {tok.kind.name} ({tok.value!r})",
                self._fn, tok.line, tok.col
            )

        is_optional = self._consume(TK.QMARK)
        return TypeNode(span, ownership, topology_ptr, topology_mut,
                        primitive, name, is_optional, False, None,
                        bounded_lo, bounded_hi, generic_args)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _parse_block(self) -> List[StmtNode]:
        self._expect(TK.LBRACE)
        stmts = []
        while not self._match(TK.RBRACE, TK.EOF):
            stmts.append(self._parse_stmt())
        self._expect(TK.RBRACE)
        return stmts

    def _parse_stmt(self) -> StmtNode:
        span = self._span()
        cur = self._cur().kind

        if cur in FIELD_MOD_TOKENS or cur in (TK.KW_LET, TK.KW_VAR, TK.KW_CONST_MOD, TK.KW_STATIC):
            return self._parse_local_var_decl(span)
        if cur == TK.KW_HANDOVER:
            self._advance()
            expr = self._parse_expr()
            self._expect(TK.SEMICOLON)
            return HandoverNode(span, expr)
        if cur == TK.KW_QUARANTINE:
            self._advance()
            expr = self._parse_expr()
            self._expect(TK.SEMICOLON)
            return QuarantineNode(span, expr)
        if cur == TK.KW_CLINCH:
            return self._parse_clinch(span)
        if cur == TK.KW_QUENCH:
            self._advance()
            body = self._parse_block()
            return QuenchNode(span, body)
        if cur == TK.KW_GATE:
            return self._parse_gate(span)
        if cur == TK.KW_EMIT:
            return self._parse_emit(span)
        if cur == TK.KW_GUARD:
            return self._parse_guard(span)
        if cur == TK.KW_IF:
            return self._parse_if(span)
        if cur == TK.KW_MATCH:
            return self._parse_match(span)
        if cur == TK.KW_WHILE:
            return self._parse_while(span)
        if cur == TK.KW_LOOP:
            self._advance()
            return WhileNode(span, LiteralNode(span, TK.KW_TRUE, "true"), self._parse_block())
        if cur == TK.KW_FOR:
            return self._parse_for(span)
        if cur == TK.KW_UNSAFE:
            self._advance()
            return UnsafeBlockNode(span, self._parse_block())
        if cur == TK.KW_RETURN:
            self._advance()
            val = None
            if not self._match(TK.SEMICOLON):
                val = self._parse_expr()
            self._expect(TK.SEMICOLON)
            return ReturnNode(span, val)
        if cur == TK.KW_REBOUND:
            self._advance()
            self._expect(TK.SEMICOLON)
            return ReboundNode(span)
        if cur == TK.KW_BREAK:
            self._advance()
            self._expect(TK.SEMICOLON)
            return BreakNode(span)
        if cur == TK.KW_CONTINUE:
            self._advance()
            self._expect(TK.SEMICOLON)
            return ContinueNode(span)
        if cur == TK.KW_DEFER:
            self._advance()
            if self._match(TK.LBRACE):
                body = self._parse_block()
                return DeferNode(span, None, body)
            expr = self._parse_expr()
            self._expect(TK.SEMICOLON)
            return DeferNode(span, expr, None)

        # Assignment ou ExprStmt
        return self._parse_assignment_or_expr_stmt(span)

    def _parse_local_var_decl(self, span) -> LocalVarDeclNode:
        if self._consume(TK.KW_STATIC):
            pass
        if self._consume(TK.KW_CONST_MOD):
            pass
        shielded = nvkeep = seal = False
        if self._match(*FIELD_MOD_TOKENS):
            m = self._advance().kind
            shielded = m == TK.KW_SHIELDED
            nvkeep = m == TK.KW_NVKEEP
            seal = m == TK.KW_SEAL
        is_var = False
        if self._match(TK.KW_VAR, TK.KW_MUT):
            is_var = True
            self._advance()
        elif self._consume(TK.KW_LET):
            if self._consume(TK.KW_MUT):
                is_var = True
        elif self._consume(TK.KW_CONST_MOD):
            is_var = False
        name = self._expect(TK.IDENT).value
        typ = None
        if self._consume(TK.COLON):
            typ = self._parse_type()
        self._expect(TK.ASSIGN)
        init = self._parse_expr()
        self._expect(TK.SEMICOLON)
        return LocalVarDeclNode(span, is_var, shielded, nvkeep, seal, name, typ, init)

    def _parse_clinch(self, span) -> ClinchNode:
        self._advance()  # consume 'clinch'
        body = self._parse_block()
        revert = []
        if self._consume(TK.KW_REVERT):
            revert = self._parse_block()
        return ClinchNode(span, body, revert)

    def _parse_gate(self, span) -> GateNode:
        self._advance()  # consume 'gate'
        self._expect(TK.LPAREN)
        cond = self._parse_expr()
        self._expect(TK.RPAREN)
        body = self._parse_block()
        return GateNode(span, cond, body)

    def _parse_emit(self, span) -> EmitNode:
        self._advance()  # consume 'emit'
        self._expect(TK.LPAREN)
        tmpl = self._expect(TK.STR_LIT).value
        outputs, inputs, clobbers = [], [], []
        if self._consume(TK.COLON):
            while not self._match(TK.COLON, TK.RPAREN, TK.EOF):
                outputs.append(self._parse_expr())
                if not self._consume(TK.COMMA):
                    break
            if self._consume(TK.COLON):
                while not self._match(TK.COLON, TK.RPAREN, TK.EOF):
                    inputs.append(self._parse_expr())
                    if not self._consume(TK.COMMA):
                        break
                if self._consume(TK.COLON):
                    while not self._match(TK.RPAREN, TK.EOF):
                        clobbers.append(self._expect(TK.STR_LIT).value)
                        if not self._consume(TK.COMMA):
                            break
        self._expect(TK.RPAREN)
        self._expect(TK.SEMICOLON)
        return EmitNode(span, tmpl, outputs, inputs, clobbers)

    def _parse_guard(self, span) -> GuardNode:
        self._advance()  # consume 'guard'
        cond = self._parse_expr()
        self._expect(TK.KW_ELSE)
        body = self._parse_block()
        return GuardNode(span, cond, body)

    def _parse_if(self, span) -> IfNode:
        self._advance()  # consume 'if'
        let_bind = None
        if self._match(TK.KW_LET):
            self._advance()
            let_bind = self._expect(TK.IDENT).value
            self._expect(TK.ASSIGN)
        cond = self._parse_expr()
        then_body = self._parse_block()
        else_body = None
        if self._consume(TK.KW_ELSE):
            if self._match(TK.KW_IF):
                else_body = self._parse_if(self._span())
            else:
                else_body = self._parse_block()
        return IfNode(span, let_bind, cond, then_body, else_body)

    def _parse_match(self, span) -> MatchNode:
        self._advance()
        subject = self._parse_expr()
        self._expect(TK.LBRACE)
        arms = []
        while not self._match(TK.RBRACE, TK.EOF):
            as_ = self._span()
            pat = self._parse_match_pattern()
            self._expect(TK.FAT_ARROW)
            if self._match(TK.LBRACE):
                body = self._parse_block()
            else:
                body = [self._parse_stmt()]
            arms.append(MatchArmNode(as_, pat, body))
        self._expect(TK.RBRACE)
        return MatchNode(span, subject, arms)

    def _parse_match_pattern(self) -> MatchPatternNode:
        span = self._span()
        cur = self._cur()
        if cur.kind in (TK.INT_LIT, TK.FLOAT_LIT, TK.STR_LIT, TK.CHAR_LIT,
                        TK.KW_TRUE, TK.KW_FALSE, TK.KW_NIL):
            tok = self._advance()
            return MatchPatternNode(span, "literal", LiteralNode(span, tok.kind, tok.value))
        if self._match(TK.IDENT) and self._cur().value == "_":
            self._advance()
            return MatchPatternNode(span, "wildcard", "_")
        if self._match(TK.DOT):
            self._advance()
            name = self._expect(TK.IDENT).value
            subs = []
            if self._consume(TK.LPAREN):
                subs.append(self._parse_match_pattern())
                while self._consume(TK.COMMA):
                    if self._match(TK.RPAREN):
                        break
                    subs.append(self._parse_match_pattern())
                self._expect(TK.RPAREN)
            return MatchPatternNode(span, "enum_variant", name, subs)
        name = self._expect(TK.IDENT).value
        return MatchPatternNode(span, "ident", name)

    def _parse_while(self, span) -> WhileNode:
        self._advance()
        cond = self._parse_expr()
        body = self._parse_block()
        return WhileNode(span, cond, body)

    def _parse_for(self, span) -> ForNode:
        self._advance()
        if self._match(TK.KW_MUT, TK.KW_VAR, TK.KW_LET):
            self._advance()
        var = self._expect(TK.IDENT).value
        self._expect(TK.KW_IN)
        start = self._parse_expr()
        if self._consume(TK.DOTDOT):
            end = self._parse_expr()
            iterable = BinaryExprNode(span, TK.DOTDOT, start, end)
        else:
            iterable = start
        body = self._parse_block()
        return ForNode(span, var, iterable, body)

    def _parse_assignment_or_expr_stmt(self, span) -> StmtNode:
        expr = self._parse_expr()
        if self._cur().kind in ASSIGN_OPS:
            op = self._advance().kind
            rhs = self._parse_expr()
            self._expect(TK.SEMICOLON)
            return AssignmentNode(span, expr, op, rhs)
        self._expect(TK.SEMICOLON)
        return ExprStmtNode(span, expr)

    # ------------------------------------------------------------------
    # Expressões (Precedência via Cascata)
    # ------------------------------------------------------------------

    def _parse_expr(self) -> ExprNode:
        return self._parse_binary()

    def _parse_binary(self) -> ExprNode:
        """Trata todos os operadores binários (sem associatividade explícita —
        Pratt simplificado com nível único, adequado para MVP)."""
        left = self._parse_unary()
        while self._cur().kind in {
            TK.EQ, TK.NEQ, TK.AND, TK.OR, TK.LAND, TK.LOR, TK.XOR,
            TK.SHL, TK.SHR, TK.LT, TK.LTE, TK.GT, TK.GTE,
            TK.PLUS, TK.MINUS, TK.STAR, TK.SLASH, TK.PERCENT, TK.NIL_COAL,
        }:
            span = self._span()
            op = self._advance().kind
            right = self._parse_unary()
            left = BinaryExprNode(span, op, left, right)
        return left

    def _parse_unary(self) -> ExprNode:
        span = self._span()
        cur = self._cur().kind
        if cur in (TK.NOT, TK.MINUS, TK.TILDE, TK.STAR, TK.LAND, TK.KW_AWAIT):
            op = self._advance().kind
            if op == TK.LAND and self._consume(TK.KW_MUT):
                pass
            return UnaryExprNode(span, op, self._parse_unary())
        return self._parse_postfix()

    def _parse_postfix(self) -> ExprNode:
        expr = self._parse_primary()
        while True:
            span = self._span()
            if self._match(TK.DOT):
                self._advance()
                if self._match(TK.KW_SLIT):
                    self._advance()
                    self._expect(TK.LBRACKET)
                    lo = self._parse_expr()
                    self._expect(TK.DOTDOT)
                    hi = self._parse_expr()
                    self._expect(TK.RBRACKET)
                    expr = BitSliceExprNode(span, expr, lo, hi)
                elif self._match(TK.KW_NOTCH):
                    self._advance()
                    self._expect(TK.LBRACKET)
                    bit = self._parse_expr()
                    self._expect(TK.RBRACKET)
                    expr = BitNotchExprNode(span, expr, bit)
                elif self._match(TK.KW_STRAND):
                    self._advance()
                    expr = BitStrandExprNode(span, expr)
                elif self._match(TK.INT_LIT):
                    idx_val = int(self._advance().value)
                    expr = TupleIndexExprNode(span, expr, idx_val)
                else:
                    name = self._expect(TK.IDENT).value
                    if self._match(TK.LPAREN):
                        self._advance()
                        args = self._parse_arg_list()
                        self._expect(TK.RPAREN)
                        expr = CallExprNode(span, FieldExprNode(span, expr, name), args)
                    else:
                        expr = FieldExprNode(span, expr, name)
            elif self._match(TK.LBRACKET):
                self._advance()
                if self._match(TK.DOTDOT):
                    self._advance()
                    hi = self._parse_expr() if not self._match(TK.RBRACKET) else None
                    self._expect(TK.RBRACKET)
                    expr = SliceExprNode(span, expr, None, hi)
                else:
                    lo = self._parse_expr()
                    if self._consume(TK.DOTDOT):
                        hi = self._parse_expr() if not self._match(TK.RBRACKET) else None
                        self._expect(TK.RBRACKET)
                        expr = SliceExprNode(span, expr, lo, hi)
                    else:
                        self._expect(TK.RBRACKET)
                        expr = IndexExprNode(span, expr, lo)
            elif self._match(TK.LPAREN):
                self._advance()
                args = self._parse_arg_list()
                self._expect(TK.RPAREN)
                expr = CallExprNode(span, expr, args)
            elif self._match(TK.KW_AS):
                self._advance()
                typ = self._parse_type()
                expr = CastExprNode(span, expr, typ)
            elif self._match(TK.QMARK):
                self._advance()
                expr = OptionalChainExprNode(span, expr)
            elif self._match(TK.NOT):
                self._advance()
                expr = ForceUnwrapExprNode(span, expr)
            else:
                break
        return expr

    def _parse_primary(self) -> ExprNode:
        span = self._span()
        cur = self._cur()

        if cur.kind in (TK.INT_LIT, TK.FLOAT_LIT, TK.STR_LIT, TK.CHAR_LIT,
                        TK.KW_TRUE, TK.KW_FALSE, TK.KW_NIL):
            self._advance()
            return LiteralNode(span, cur.kind, cur.value)

        if cur.kind in (TK.KW_SELF, TK.KW_SUPER):
            self._advance()
            return IdentNode(span, cur.value)

        if cur.kind == TK.IDENT:
            path = [self._advance().value]
            while self._match(TK.DCOLON) and self._peek().kind == TK.IDENT:
                self._advance()
                path.append(self._advance().value)
            name = path[-1]
            prefix = path[:-1]
            if self._match(TK.LBRACE):
                p1 = self._peek(1)
                p2 = self._peek(2)
                if p1.kind == TK.RBRACE or (p1.kind == TK.IDENT and p2.kind == TK.COLON):
                    self._advance()  # consume {
                    fields = []
                    while not self._match(TK.RBRACE, TK.EOF):
                        fs = self._span()
                        fname = self._expect(TK.IDENT).value
                        self._expect(TK.COLON)
                        fval = self._parse_expr()
                        self._consume(TK.COMMA)
                        fields.append(StructLitFieldNode(fs, fname, fval))
                    self._expect(TK.RBRACE)
                    return StructLitExprNode(span, name, prefix, fields)
            return IdentNode(span, name, prefix)

        if cur.kind == TK.LPAREN:
            self._advance()
            if self._match(TK.RPAREN):
                self._advance()
                return TupleLitExprNode(span, [])  # unit ()
            first = self._parse_expr()
            if self._consume(TK.COMMA):
                elements = [first]
                while not self._match(TK.RPAREN, TK.EOF):
                    elements.append(self._parse_expr())
                    if not self._consume(TK.COMMA):
                        break
                self._expect(TK.RPAREN)
                return TupleLitExprNode(span, elements)
            self._expect(TK.RPAREN)
            return first

        if cur.kind == TK.LBRACKET:
            self._advance()
            elements = []
            if not self._match(TK.RBRACKET):
                first = self._parse_expr()
                if self._consume(TK.SEMICOLON):
                    count_expr = self._parse_expr()
                    self._expect(TK.RBRACKET)
                    if isinstance(count_expr, LiteralNode) and count_expr.kind == TK.INT_LIT:
                        n = int(count_expr.value)
                        elements = [first] * n
                    else:
                        elements = [first]
                    return ArrayLitExprNode(span, elements)
                elements.append(first)
                while self._consume(TK.COMMA):
                    if self._match(TK.RBRACKET):
                        break
                    elements.append(self._parse_expr())
            self._expect(TK.RBRACKET)
            return ArrayLitExprNode(span, elements)

        if cur.kind == TK.KW_IF:
            self._advance()
            cond = self._parse_expr()
            self._expect(TK.LBRACE)
            then_expr = self._parse_expr()
            self._expect(TK.RBRACE)
            self._expect(TK.KW_ELSE)
            if self._match(TK.KW_IF):
                else_expr = self._parse_primary()
            else:
                self._expect(TK.LBRACE)
                else_expr = self._parse_expr()
                self._expect(TK.RBRACE)
            return IfExprNode(span, cond, then_expr, else_expr)

        if cur.kind == TK.LBRACE:
            self._advance()
            params = []
            if self._match(TK.IDENT) and self._peek().kind == TK.ARROW:
                while self._match(TK.IDENT):
                    params.append(self._advance().value)
                    if not self._consume(TK.COMMA):
                        break
                self._expect(TK.ARROW)
            body = []
            while not self._match(TK.RBRACE, TK.EOF):
                body.append(self._parse_stmt())
            self._expect(TK.RBRACE)
            return ClosureExprNode(span, params, body)

        # Struct/class literal: TypeName { field: value, ... }
        # Detectado como Ident seguido de '{' — só quando o ident é um tipo (maiúscula)
        # A detecção é feita no contexto de expressão; não cria conflito com blocos de fn.
        # NOTA: No MVP não parsamos struct literals para evitar ambiguidade com closures;
        # em vez disso, a fixture srg_scope.st deve usar construtores explícitos.

        raise SotlasParseError(
            f"expressão inesperada: {cur.kind.name} ({cur.value!r})",
            self._fn, cur.line, cur.col
        )

    def _parse_arg_list(self) -> List[ArgNode]:
        args = []
        if self._match(TK.RPAREN):
            return args
        args.append(self._parse_arg())
        while self._consume(TK.COMMA):
            if self._match(TK.RPAREN):
                break
            args.append(self._parse_arg())
        return args

    def _parse_arg(self) -> ArgNode:
        span = self._span()
        label = None
        if self._match(TK.IDENT) and self._peek().kind == TK.COLON:
            label = self._advance().value
            self._advance()  # consume ':'
        val = self._parse_expr()
        return ArgNode(span, label, val)

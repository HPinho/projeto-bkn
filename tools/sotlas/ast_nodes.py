"""Sotlas AST Nodes — Hierarquia completa de nós da Árvore Sintática Abstrata."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Union
from .token_types import TK, PRIMITIVE_TOKENS, OWNERSHIP_MODS, TOPOLOGY_MODS


# ---------------------------------------------------------------------------
# Localização (para mensagens de erro semântico)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Span:
    file: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------


@dataclass
class TypeNode:
    """Representa um tipo completo com modificadores opcionais de posse e topologia."""
    span: Span
    ownership: Optional[TK]           # co-owned | sole | island | whisper | direct
    topology_ptr: Optional[TK]        # rawphys | virtmap | portwire | dmazone | voidzero
    topology_mut: bool                # *mut T
    primitive: Optional[TK]          # tipo primitivo (KW_INT8 … KW_VOID)
    name: Optional[str]              # identificador de tipo definido pelo usuário
    is_optional: bool                 # sufixo '?'
    is_array: bool                    # [T; N]
    array_size: Optional["ExprNode"]  # expressão do tamanho
    bounded_lo: Optional["ExprNode"]  # PrimitiveType.bound[lo..hi]
    bounded_hi: Optional["ExprNode"]
    generic_args: List["TypeNode"] = field(default_factory=list)

    @property
    def is_topology_ptr(self) -> bool:
        return self.topology_ptr is not None

    @property
    def is_primitive(self) -> bool:
        return self.primitive is not None

    @property
    def is_bounded(self) -> bool:
        return self.bounded_lo is not None


@dataclass
class FunctionTypeNode:
    span: Span
    params: List[TypeNode]
    ret: TypeNode
    is_async: bool = False


@dataclass
class TupleTypeNode:
    span: Span
    elements: List[TypeNode]


# ---------------------------------------------------------------------------
# Expressões
# ---------------------------------------------------------------------------

@dataclass
class LiteralNode:
    span: Span
    kind: TK       # INT_LIT | FLOAT_LIT | STR_LIT | CHAR_LIT | KW_TRUE | KW_FALSE | KW_NIL
    value: str


@dataclass
class IdentNode:
    span: Span
    name: str
    path: List[str] = field(default_factory=list)  # a::b::c → path=["a","b"], name="c"


@dataclass
class BinaryExprNode:
    span: Span
    op: TK
    left: "ExprNode"
    right: "ExprNode"


@dataclass
class UnaryExprNode:
    span: Span
    op: TK     # NOT | MINUS | TILDE | STAR | LAND | KW_AWAIT
    operand: "ExprNode"


@dataclass
class CallExprNode:
    span: Span
    callee: "ExprNode"
    args: List["ArgNode"]


@dataclass
class ArgNode:
    span: Span
    label: Optional[str]   # argumento rotulado: label: expr
    value: "ExprNode"


@dataclass
class IndexExprNode:
    span: Span
    base: "ExprNode"
    index: "ExprNode"


@dataclass
class FieldExprNode:
    span: Span
    base: "ExprNode"
    field: str


@dataclass
class BitSliceExprNode:
    """base.slit[lo..hi] — extrai campo de bits."""
    span: Span
    base: "ExprNode"
    lo: "ExprNode"
    hi: "ExprNode"


@dataclass
class BitNotchExprNode:
    """base.notch[n] — extrai bit isolado."""
    span: Span
    base: "ExprNode"
    bit: "ExprNode"


@dataclass
class BitStrandExprNode:
    """base.strand — inverte endianness dos bytes."""
    span: Span
    base: "ExprNode"


@dataclass
class CastExprNode:
    """expr as Type."""
    span: Span
    expr: "ExprNode"
    target_type: TypeNode


@dataclass
class OptionalChainExprNode:
    """expr? — encadeia opcional."""
    span: Span
    expr: "ExprNode"


@dataclass
class ForceUnwrapExprNode:
    """expr! — desempacotamento forçado."""
    span: Span
    expr: "ExprNode"


@dataclass
class ArrayLitExprNode:
    span: Span
    elements: List["ExprNode"]


@dataclass
class ClosureExprNode:
    span: Span
    params: List[str]
    body: List["StmtNode"]


# Union type para todas as expressões
ExprNode = Union[
    LiteralNode, IdentNode, BinaryExprNode, UnaryExprNode, CallExprNode,
    IndexExprNode, FieldExprNode, BitSliceExprNode, BitNotchExprNode,
    BitStrandExprNode, CastExprNode, OptionalChainExprNode, ForceUnwrapExprNode,
    ArrayLitExprNode, ClosureExprNode, ArgNode,
]


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class LocalVarDeclNode:
    span: Span
    is_var: bool           # var → mutável; let → imutável
    is_shielded: bool      # shielded (não reordenável pelo compilador)
    is_nvkeep: bool        # nvkeep (persistência em memória não-volátil)
    is_seal: bool          # seal (constante em tempo de link)
    name: str
    type_ann: Optional[TypeNode]
    init: ExprNode


@dataclass
class AssignmentNode:
    span: Span
    target: ExprNode
    op: TK                 # ASSIGN | PLUS_EQ | MINUS_EQ | …
    value: ExprNode


@dataclass
class HandoverNode:
    span: Span
    expr: ExprNode         # transfere posse para o chamador


@dataclass
class QuarantineNode:
    span: Span
    expr: ExprNode         # isola recurso em região island


@dataclass
class ClinchNode:
    span: Span
    body: List["StmtNode"]
    revert: List["StmtNode"]   # bloco revert (restauração)


@dataclass
class QuenchNode:
    span: Span
    body: List["StmtNode"]     # barreira de memória persistente


@dataclass
class GateNode:
    span: Span
    condition: ExprNode
    body: List["StmtNode"]


@dataclass
class EmitNode:
    span: Span
    template: str              # string de assembly
    outputs: List[ExprNode]
    inputs: List[ExprNode]
    clobbers: List[str]


@dataclass
class GuardNode:
    span: Span
    condition: ExprNode
    else_body: List["StmtNode"]


@dataclass
class IfNode:
    span: Span
    let_bind: Optional[str]    # if let x = expr
    condition: ExprNode
    then_body: List["StmtNode"]
    else_body: Optional[Union[List["StmtNode"], "IfNode"]]


@dataclass
class MatchArmNode:
    span: Span
    pattern: "MatchPatternNode"
    body: Union[List["StmtNode"], ExprNode]


@dataclass
class MatchPatternNode:
    span: Span
    kind: str          # "literal" | "wildcard" | "enum_variant" | "ident"
    value: Optional[Union[str, LiteralNode]]
    sub_patterns: List["MatchPatternNode"] = field(default_factory=list)


@dataclass
class MatchNode:
    span: Span
    subject: ExprNode
    arms: List[MatchArmNode]


@dataclass
class WhileNode:
    span: Span
    condition: ExprNode
    body: List["StmtNode"]


@dataclass
class ForNode:
    span: Span
    var: str
    iterable: ExprNode
    body: List["StmtNode"]


@dataclass
class UnsafeBlockNode:
    span: Span
    body: List["StmtNode"]


@dataclass
class ReturnNode:
    span: Span
    value: Optional[ExprNode]


@dataclass
class ReboundNode:
    span: Span     # encadeia retorno de interrupção (iret / eret)


@dataclass
class BreakNode:
    span: Span


@dataclass
class ContinueNode:
    span: Span


@dataclass
class ExprStmtNode:
    span: Span
    expr: ExprNode


StmtNode = Union[
    LocalVarDeclNode, AssignmentNode, HandoverNode, QuarantineNode,
    ClinchNode, QuenchNode, GateNode, EmitNode, GuardNode,
    IfNode, MatchNode, WhileNode, ForNode, UnsafeBlockNode,
    ReturnNode, ReboundNode, BreakNode, ContinueNode, ExprStmtNode,
]


# ---------------------------------------------------------------------------
# Declarações
# ---------------------------------------------------------------------------

@dataclass
class DirectiveNode:
    span: Span
    name: str
    args: List[tuple]   # [(key, value_str), …]


@dataclass
class FieldDeclNode:
    span: Span
    directives: List[DirectiveNode]
    visibility: Optional[TK]      # KW_PUB | KW_CAPSULE | KW_LINEAGE
    is_var: bool
    is_shielded: bool
    is_nvkeep: bool
    is_seal: bool
    name: str
    type_ann: TypeNode
    default: Optional[ExprNode]


@dataclass
class ParamNode:
    span: Span
    label: Optional[str]       # rótulo externo (Objective-C style)
    name: str
    type_ann: TypeNode
    default: Optional[ExprNode]


@dataclass
class FnDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    is_irqfree: bool
    is_async: bool
    is_moldable: bool
    is_reshape: bool
    name: str
    generics: List[str]
    params: List[ParamNode]
    ret: Optional[TypeNode]
    body: Optional[List[StmtNode]]   # None → declaração em spec


@dataclass
class TrapFnDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    name: str
    params: List[ParamNode]
    ret: Optional[TypeNode]
    body: List[StmtNode]


@dataclass
class InitDeclNode:
    span: Span
    visibility: Optional[TK]
    params: List[ParamNode]
    body: List[StmtNode]


@dataclass
class DeinitDeclNode:
    span: Span
    body: List[StmtNode]


@dataclass
class StructDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    name: str
    generics: List[str]
    adopts: List[str]             # nomes de specs adotados
    members: List[Union[FieldDeclNode, FnDeclNode, InitDeclNode]]


@dataclass
class ClassDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    name: str
    generics: List[str]
    base: Optional[str]           # herança simples
    adopts: List[str]             # specs adotados
    members: List[Union[FieldDeclNode, FnDeclNode, InitDeclNode, DeinitDeclNode]]


@dataclass
class MeshMemberNode:
    span: Span
    name: str
    type_ann: TypeNode
    align: Optional[ExprNode]


@dataclass
class MeshDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    name: str
    members: List[MeshMemberNode]


@dataclass
class SpecMemberNode:
    span: Span
    is_irqfree: bool
    is_async: bool
    fn_decl: FnDeclNode


@dataclass
class SpecDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    name: str
    generics: List[str]
    members: List[SpecMemberNode]


@dataclass
class EnumVariantNode:
    span: Span
    name: str
    params: List[ParamNode]
    value: Optional[ExprNode]


@dataclass
class EnumDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    name: str
    backing_type: Optional[TypeNode]
    variants: List[EnumVariantNode]


@dataclass
class ConstDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    name: str
    type_ann: TypeNode
    value: ExprNode


@dataclass
class StaticDeclNode:
    span: Span
    directives: List[DirectiveNode]
    is_pub: bool
    modifier: Optional[TK]     # KW_SHIELDED | KW_NVKEEP | KW_SEAL
    is_var: bool
    name: str
    type_ann: TypeNode
    value: ExprNode


@dataclass
class TypeAliasDeclNode:
    span: Span
    is_pub: bool
    name: str
    generics: List[str]
    alias: TypeNode


@dataclass
class MouldBlockNode:
    span: Span
    is_pub: bool
    body: List[StmtNode]


@dataclass
class ImportDeclNode:
    span: Span
    is_pub: bool
    path: List[str]
    items: Optional[List[str]]   # None → wildcard *


@dataclass
class ModuleDeclNode:
    span: Span
    path: List[str]


@dataclass
class SourceFileNode:
    span: Span
    filename: str
    is_barecore: bool
    module: ModuleDeclNode
    imports: List[ImportDeclNode]
    decls: List[Union[
        StructDeclNode, ClassDeclNode, MeshDeclNode, SpecDeclNode,
        EnumDeclNode, ConstDeclNode, StaticDeclNode, FnDeclNode,
        TrapFnDeclNode, TypeAliasDeclNode, MouldBlockNode,
    ]]

"""Sotlas Token Types — Enumeração completa de todos os tokens da linguagem."""
from enum import Enum, auto


class TK(Enum):
    # -------------------------------------------------------------------------
    # Literais
    # -------------------------------------------------------------------------
    INT_LIT    = auto()   # 42, 0xFF, 0b1010
    FLOAT_LIT  = auto()   # 3.14
    STR_LIT    = auto()   # "hello"
    CHAR_LIT   = auto()   # 'x'
    IDENT      = auto()   # identificadores

    # -------------------------------------------------------------------------
    # Palavras-chave — Estrutura do Módulo
    # -------------------------------------------------------------------------
    KW_BARECORE  = auto()   # barecore
    KW_MODULE    = auto()   # module
    KW_IMPORT    = auto()   # import
    KW_PUB       = auto()   # pub
    KW_AS        = auto()   # as

    # -------------------------------------------------------------------------
    # Palavras-chave — Declarações de Topo
    # -------------------------------------------------------------------------
    KW_STRUCT    = auto()   # struct
    KW_CLASS     = auto()   # class
    KW_MESH      = auto()   # mesh
    KW_SPEC      = auto()   # spec
    KW_ENUM      = auto()   # enum
    KW_CONST     = auto()   # const
    KW_STATIC    = auto()   # static
    KW_FN        = auto()   # fn
    KW_TRAPFN    = auto()   # trapfn
    KW_TYPEALIAS = auto()   # typealias
    KW_MOULD     = auto()   # mould

    # -------------------------------------------------------------------------
    # Palavras-chave — Membros de Classes e Structs
    # -------------------------------------------------------------------------
    KW_ADOPTS    = auto()   # adopts
    KW_INIT      = auto()   # init
    KW_DEINIT    = auto()   # deinit
    KW_MOLDABLE  = auto()   # moldable
    KW_RESHAPE   = auto()   # reshape
    KW_ALIGN     = auto()   # align

    # -------------------------------------------------------------------------
    # Palavras-chave — Visibilidade
    # -------------------------------------------------------------------------
    KW_CAPSULE   = auto()   # capsule
    KW_LINEAGE   = auto()   # lineage
    KW_PRIV      = auto()   # priv  (alias de capsule para compatibilidade)

    # -------------------------------------------------------------------------
    # Palavras-chave — Modificadores de Campo / Variáveis
    # -------------------------------------------------------------------------
    KW_LET       = auto()   # let
    KW_VAR       = auto()   # var
    KW_MUT       = auto()   # mut
    KW_SHIELDED  = auto()   # shielded
    KW_NVKEEP    = auto()   # nvkeep
    KW_SEAL      = auto()   # seal

    # -------------------------------------------------------------------------
    # Palavras-chave — Modificadores de Função
    # -------------------------------------------------------------------------
    KW_IRQFREE   = auto()   # irqfree
    KW_ASYNC     = auto()   # async
    KW_AWAIT     = auto()   # await

    # -------------------------------------------------------------------------
    # Palavras-chave — SRG (Scoped Reference Graph) — Ownership
    # -------------------------------------------------------------------------
    KW_CO_OWNED  = auto()   # co-owned
    KW_SOLE      = auto()   # sole
    KW_ISLAND    = auto()   # island
    KW_WHISPER   = auto()   # whisper
    KW_DIRECT    = auto()   # direct

    # -------------------------------------------------------------------------
    # Palavras-chave — SRG — Transferência e Isolamento
    # -------------------------------------------------------------------------
    KW_HANDOVER    = auto()   # handover
    KW_QUARANTINE  = auto()   # quarantine

    # -------------------------------------------------------------------------
    # Palavras-chave — Hardware / Seção Crítica
    # -------------------------------------------------------------------------
    KW_CLINCH    = auto()   # clinch
    KW_REVERT    = auto()   # revert
    KW_QUENCH    = auto()   # quench
    KW_GATE      = auto()   # gate
    KW_EMIT      = auto()   # emit
    KW_UNSAFE    = auto()   # unsafe
    KW_REBOUND   = auto()   # rebound

    # -------------------------------------------------------------------------
    # Palavras-chave — Tipos Primitivos
    # -------------------------------------------------------------------------
    KW_INT       = auto()   # Int
    KW_INT8      = auto()   # Int8
    KW_INT16     = auto()   # Int16
    KW_INT32     = auto()   # Int32
    KW_INT64     = auto()   # Int64
    KW_UINT      = auto()   # UInt
    KW_UINT8     = auto()   # UInt8
    KW_UINT16    = auto()   # UInt16
    KW_UINT32    = auto()   # UInt32
    KW_UINT64    = auto()   # UInt64
    KW_FLOAT32   = auto()   # Float32
    KW_FLOAT64   = auto()   # Float64
    KW_USIZE     = auto()   # USize
    KW_ISIZE     = auto()   # ISize
    KW_BOOL      = auto()   # Bool
    KW_CHAR      = auto()   # Char
    KW_STRING    = auto()   # String
    KW_VOID      = auto()   # Void

    # -------------------------------------------------------------------------
    # Palavras-chave — Topology Pointer Qualifiers
    # -------------------------------------------------------------------------
    KW_RAWPHYS   = auto()   # rawphys
    KW_VIRTMAP   = auto()   # virtmap
    KW_PORTWIRE  = auto()   # portwire
    KW_DMAZONE   = auto()   # dmazone
    KW_VOIDZERO  = auto()   # voidzero

    # -------------------------------------------------------------------------
    # Palavras-chave — Controle de Fluxo
    # -------------------------------------------------------------------------
    KW_IF        = auto()   # if
    KW_ELSE      = auto()   # else
    KW_WHILE     = auto()   # while
    KW_FOR       = auto()   # for
    KW_IN        = auto()   # in
    KW_MATCH     = auto()   # match
    KW_RETURN    = auto()   # return
    KW_BREAK     = auto()   # break
    KW_CONTINUE  = auto()   # continue
    KW_GUARD     = auto()   # guard

    # -------------------------------------------------------------------------
    # Palavras-chave — Valores Literais
    # -------------------------------------------------------------------------
    KW_TRUE      = auto()   # true
    KW_FALSE     = auto()   # false
    KW_NIL       = auto()   # nil
    KW_SELF      = auto()   # self
    KW_SUPER     = auto()   # super

    # -------------------------------------------------------------------------
    # Acessores de Bits (postfix .slit, .notch, .strand)
    # -------------------------------------------------------------------------
    KW_SLIT      = auto()   # slit
    KW_NOTCH     = auto()   # notch
    KW_STRAND    = auto()   # strand

    # -------------------------------------------------------------------------
    # Herança e Adoção
    # -------------------------------------------------------------------------
    KW_BOUND     = auto()   # bound  (usado em PrimitiveType.bound[lo..hi])
    KW_CONST_MOD = auto()   # const  (modificador de ponteiro)

    # -------------------------------------------------------------------------
    # Operadores
    # -------------------------------------------------------------------------
    EQ       = auto()   # ==
    NEQ      = auto()   # !=
    AND      = auto()   # &&
    OR       = auto()   # ||
    LAND     = auto()   # &
    LOR      = auto()   # |
    XOR      = auto()   # ^
    NOT      = auto()   # !
    TILDE    = auto()   # ~
    SHL      = auto()   # <<
    SHR      = auto()   # >>
    LT       = auto()   # <
    LTE      = auto()   # <=
    GT       = auto()   # >
    GTE      = auto()   # >=
    PLUS     = auto()   # +
    MINUS    = auto()   # -
    STAR     = auto()   # *
    SLASH    = auto()   # /
    PERCENT  = auto()   # %
    NIL_COAL = auto()   # ??
    ASSIGN   = auto()   # =
    PLUS_EQ  = auto()   # +=
    MINUS_EQ = auto()   # -=
    STAR_EQ  = auto()   # *=
    SLASH_EQ = auto()   # /=
    PCT_EQ   = auto()   # %=
    AND_EQ   = auto()   # &=
    OR_EQ    = auto()   # |=
    XOR_EQ   = auto()   # ^=
    SHL_EQ   = auto()   # <<=
    SHR_EQ   = auto()   # >>=
    ARROW    = auto()   # ->
    FAT_ARROW = auto()  # =>
    DOTDOT   = auto()   # ..
    AMP      = auto()   # & (unary address-of, alias de LAND quando unário)
    QMARK    = auto()   # ?
    BANG     = auto()   # ! (postfix unwrap, alias de NOT quando postfix)

    # -------------------------------------------------------------------------
    # Delimitadores e Pontuação
    # -------------------------------------------------------------------------
    LBRACE   = auto()   # {
    RBRACE   = auto()   # }
    LPAREN   = auto()   # (
    RPAREN   = auto()   # )
    LBRACKET = auto()   # [
    RBRACKET = auto()   # ]
    SEMICOLON = auto()  # ;
    COLON    = auto()   # :
    COMMA    = auto()   # ,
    DOT      = auto()   # .
    DCOLON   = auto()   # ::
    AT       = auto()   # @

    # -------------------------------------------------------------------------
    # Especial
    # -------------------------------------------------------------------------
    EOF      = auto()   # fim de arquivo


# Tabela de palavras-chave: texto → TK
KEYWORDS: dict[str, TK] = {
    "barecore":   TK.KW_BARECORE,
    "module":     TK.KW_MODULE,
    "import":     TK.KW_IMPORT,
    "pub":        TK.KW_PUB,
    "as":         TK.KW_AS,
    "struct":     TK.KW_STRUCT,
    "class":      TK.KW_CLASS,
    "mesh":       TK.KW_MESH,
    "spec":       TK.KW_SPEC,
    "enum":       TK.KW_ENUM,
    "const":      TK.KW_CONST_MOD,
    "static":     TK.KW_STATIC,
    "fn":         TK.KW_FN,
    "trapfn":     TK.KW_TRAPFN,
    "typealias":  TK.KW_TYPEALIAS,
    "mould":      TK.KW_MOULD,
    "adopts":     TK.KW_ADOPTS,
    "init":       TK.KW_INIT,
    "deinit":     TK.KW_DEINIT,
    "moldable":   TK.KW_MOLDABLE,
    "reshape":    TK.KW_RESHAPE,
    "align":      TK.KW_ALIGN,
    "capsule":    TK.KW_CAPSULE,
    "lineage":    TK.KW_LINEAGE,
    "priv":       TK.KW_PRIV,
    "let":        TK.KW_LET,
    "var":        TK.KW_VAR,
    "mut":        TK.KW_MUT,
    "shielded":   TK.KW_SHIELDED,
    "nvkeep":     TK.KW_NVKEEP,
    "seal":       TK.KW_SEAL,
    "irqfree":    TK.KW_IRQFREE,
    "async":      TK.KW_ASYNC,
    "await":      TK.KW_AWAIT,
    "sole":       TK.KW_SOLE,
    "island":     TK.KW_ISLAND,
    "whisper":    TK.KW_WHISPER,
    "direct":     TK.KW_DIRECT,
    "handover":   TK.KW_HANDOVER,
    "quarantine": TK.KW_QUARANTINE,
    "clinch":     TK.KW_CLINCH,
    "revert":     TK.KW_REVERT,
    "quench":     TK.KW_QUENCH,
    "gate":       TK.KW_GATE,
    "emit":       TK.KW_EMIT,
    "unsafe":     TK.KW_UNSAFE,
    "rebound":    TK.KW_REBOUND,
    "Int":        TK.KW_INT,
    "Int8":       TK.KW_INT8,
    "Int16":      TK.KW_INT16,
    "Int32":      TK.KW_INT32,
    "Int64":      TK.KW_INT64,
    "UInt":       TK.KW_UINT,
    "UInt8":      TK.KW_UINT8,
    "UInt16":     TK.KW_UINT16,
    "UInt32":     TK.KW_UINT32,
    "UInt64":     TK.KW_UINT64,
    "Float32":    TK.KW_FLOAT32,
    "Float64":    TK.KW_FLOAT64,
    "USize":      TK.KW_USIZE,
    "ISize":      TK.KW_ISIZE,
    "Bool":       TK.KW_BOOL,
    "Char":       TK.KW_CHAR,
    "String":     TK.KW_STRING,
    "Void":       TK.KW_VOID,
    "rawphys":    TK.KW_RAWPHYS,
    "virtmap":    TK.KW_VIRTMAP,
    "portwire":   TK.KW_PORTWIRE,
    "dmazone":    TK.KW_DMAZONE,
    "voidzero":   TK.KW_VOIDZERO,
    "if":         TK.KW_IF,
    "else":       TK.KW_ELSE,
    "while":      TK.KW_WHILE,
    "for":        TK.KW_FOR,
    "in":         TK.KW_IN,
    "match":      TK.KW_MATCH,
    "return":     TK.KW_RETURN,
    "break":      TK.KW_BREAK,
    "continue":   TK.KW_CONTINUE,
    "guard":      TK.KW_GUARD,
    "true":       TK.KW_TRUE,
    "false":      TK.KW_FALSE,
    "nil":        TK.KW_NIL,
    "self":       TK.KW_SELF,
    "super":      TK.KW_SUPER,
    "slit":       TK.KW_SLIT,
    "notch":      TK.KW_NOTCH,
    "strand":     TK.KW_STRAND,
    "bound":      TK.KW_BOUND,
}

# co-owned usa hífen — tratado separadamente no lexer (IDENT "co" seguido de MINUS "owned"
# é detectado na fase de pós-processamento de tokens)
COMPOUND_KEYWORDS: dict[str, TK] = {
    "co-owned": TK.KW_CO_OWNED,
}


# Tipos primitivos que mapeiam diretamente para C99
PRIMITIVE_C_MAP: dict[TK, str] = {
    TK.KW_INT:     "intptr_t",
    TK.KW_INT8:    "int8_t",
    TK.KW_INT16:   "int16_t",
    TK.KW_INT32:   "int32_t",
    TK.KW_INT64:   "int64_t",
    TK.KW_UINT:    "uintptr_t",
    TK.KW_UINT8:   "uint8_t",
    TK.KW_UINT16:  "uint16_t",
    TK.KW_UINT32:  "uint32_t",
    TK.KW_UINT64:  "uint64_t",
    TK.KW_FLOAT32: "float",
    TK.KW_FLOAT64: "double",
    TK.KW_USIZE:   "size_t",
    TK.KW_ISIZE:   "ptrdiff_t",
    TK.KW_BOOL:    "uint8_t",
    TK.KW_CHAR:    "char",
    TK.KW_STRING:  "const char*",
    TK.KW_VOID:    "void",
}

PRIMITIVE_TOKENS = set(PRIMITIVE_C_MAP.keys())

# Conjunto de modificadores de posse SRG
OWNERSHIP_MODS: set["TK"] = {
    TK.KW_CO_OWNED, TK.KW_SOLE, TK.KW_ISLAND, TK.KW_WHISPER, TK.KW_DIRECT,
}

# Conjunto de qualificadores de ponteiro de topologia
TOPOLOGY_MODS: set["TK"] = {
    TK.KW_RAWPHYS, TK.KW_VIRTMAP, TK.KW_PORTWIRE, TK.KW_DMAZONE, TK.KW_VOIDZERO,
    TK.KW_MUT, TK.KW_CONST_MOD,
}

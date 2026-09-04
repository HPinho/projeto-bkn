"""Extensão de backend x86-64 para o frontend Sotlas Bootstrap.

Mantém instruções privilegiadas fora do compilador de alto nível. O módulo
registra assinaturas Sotlas e injeta apenas wrappers C freestanding mínimos,
que o GCC reduz para as instruções reais da CPU.
"""

from __future__ import annotations


_MARKER = "/* SOTLAS_X86_64_PRIVILEGED_INTRINSICS */"

_C_INTRINSICS = r'''

/* SOTLAS_X86_64_PRIVILEGED_INTRINSICS */
static inline void __lgdt(uint64_t address) {
    __asm__ __volatile__("lgdt (%0)" : : "r"((uintptr_t)address) : "memory");
}

static inline void __lidt(uint64_t address) {
    __asm__ __volatile__("lidt (%0)" : : "r"((uintptr_t)address) : "memory");
}

static inline void __ltr(uint16_t selector) {
    __asm__ __volatile__("ltr %w0" : : "r"(selector) : "memory");
}

static inline uint64_t __read_cr2(void) {
    uint64_t value;
    __asm__ __volatile__("mov %%cr2, %0" : "=r"(value) : : "memory");
    return value;
}

static inline void __invlpg(uint64_t address) {
    __asm__ __volatile__("invlpg (%0)" : : "r"((uintptr_t)address) : "memory");
}
'''


def install(bootstrap) -> None:
    """Registra os intrínsecos no módulo ``bootstrap`` de forma idempotente."""
    Type = bootstrap.Type
    Function = bootstrap.Function

    builtins = {
        "__lgdt": Function(
            "__lgdt", [("address", Type("u64"))], Type("void"), [],
            public=True, attributes=["@system"],
        ),
        "__lidt": Function(
            "__lidt", [("address", Type("u64"))], Type("void"), [],
            public=True, attributes=["@system"],
        ),
        "__ltr": Function(
            "__ltr", [("selector", Type("u16"))], Type("void"), [],
            public=True, attributes=["@system"],
        ),
        "__read_cr2": Function(
            "__read_cr2", [], Type("u64"), [],
            public=True, attributes=["@system"],
        ),
        "__invlpg": Function(
            "__invlpg", [("address", Type("u64"))], Type("void"), [],
            public=True, attributes=["@system"],
        ),
    }
    bootstrap.BUILTIN_FUNCTIONS.update(builtins)

    if _MARKER not in bootstrap.PREAMBLE:
        bootstrap.PREAMBLE = bootstrap.PREAMBLE.rstrip() + _C_INTRINSICS + "\n"

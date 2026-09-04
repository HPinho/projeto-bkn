"""Extensão de backend x86-64 para o frontend Sotlas Bootstrap.

Mantém instruções privilegiadas e entry stubs fora do compilador de alto nível.
O módulo registra assinaturas Sotlas e injeta somente wrappers C/assembly
freestanding mínimos, que o GCC reduz para instruções reais da CPU.
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

/*
 * Exception entry ABI (fase inicial, terminal):
 *
 *   rsp + 0  = vector
 *   rsp + 8  = error code (real ou zero sintetico)
 *   rsp + 16 = RIP empilhado pela CPU
 *   rsp + 24 = CS
 *   rsp + 32 = RFLAGS
 *
 * Em mudança de CPL a CPU ainda acrescenta RSP/SS depois desses campos.
 * O dispatcher inicial não retorna; por isso ainda não há restauração/IRETQ.
 */
extern void baken_exception_dispatch(uint64_t frame_address);

__attribute__((naked, used)) static void __baken_exception_common(void) {
    __asm__ __volatile__(
        "movq %rsp, %rcx\n\t"
        "andq $-16, %rsp\n\t"
        "subq $32, %rsp\n\t"
        "call baken_exception_dispatch\n\t"
        "cli\n\t"
        "1: hlt\n\t"
        "jmp 1b\n\t"
    );
}

#define BAKEN_ISR_NOERR(n) \
    __attribute__((naked, used)) static void __baken_isr_##n(void) { \
        __asm__ __volatile__("pushq $0\n\tpushq $" #n "\n\tjmp __baken_exception_common"); \
    }

#define BAKEN_ISR_ERR(n) \
    __attribute__((naked, used)) static void __baken_isr_##n(void) { \
        __asm__ __volatile__("pushq $" #n "\n\tjmp __baken_exception_common"); \
    }

BAKEN_ISR_NOERR(0)
BAKEN_ISR_NOERR(1)
BAKEN_ISR_NOERR(2)
BAKEN_ISR_NOERR(3)
BAKEN_ISR_NOERR(4)
BAKEN_ISR_NOERR(5)
BAKEN_ISR_NOERR(6)
BAKEN_ISR_NOERR(7)
BAKEN_ISR_ERR(8)
BAKEN_ISR_NOERR(9)
BAKEN_ISR_ERR(10)
BAKEN_ISR_ERR(11)
BAKEN_ISR_ERR(12)
BAKEN_ISR_ERR(13)
BAKEN_ISR_ERR(14)
BAKEN_ISR_NOERR(15)
BAKEN_ISR_NOERR(16)
BAKEN_ISR_ERR(17)
BAKEN_ISR_NOERR(18)
BAKEN_ISR_NOERR(19)
BAKEN_ISR_NOERR(20)
BAKEN_ISR_ERR(21)
BAKEN_ISR_NOERR(22)
BAKEN_ISR_NOERR(23)
BAKEN_ISR_NOERR(24)
BAKEN_ISR_NOERR(25)
BAKEN_ISR_NOERR(26)
BAKEN_ISR_NOERR(27)
BAKEN_ISR_NOERR(28)
BAKEN_ISR_ERR(29)
BAKEN_ISR_ERR(30)
BAKEN_ISR_NOERR(31)

#undef BAKEN_ISR_NOERR
#undef BAKEN_ISR_ERR

/* Preparado para a etapa que conectará os stubs aos gates da IDT. */
static inline uint64_t __baken_exception_stub_address(uint16_t vector) {
    switch (vector) {
        case 0: return (uint64_t)(uintptr_t)&__baken_isr_0;
        case 1: return (uint64_t)(uintptr_t)&__baken_isr_1;
        case 2: return (uint64_t)(uintptr_t)&__baken_isr_2;
        case 3: return (uint64_t)(uintptr_t)&__baken_isr_3;
        case 4: return (uint64_t)(uintptr_t)&__baken_isr_4;
        case 5: return (uint64_t)(uintptr_t)&__baken_isr_5;
        case 6: return (uint64_t)(uintptr_t)&__baken_isr_6;
        case 7: return (uint64_t)(uintptr_t)&__baken_isr_7;
        case 8: return (uint64_t)(uintptr_t)&__baken_isr_8;
        case 9: return (uint64_t)(uintptr_t)&__baken_isr_9;
        case 10: return (uint64_t)(uintptr_t)&__baken_isr_10;
        case 11: return (uint64_t)(uintptr_t)&__baken_isr_11;
        case 12: return (uint64_t)(uintptr_t)&__baken_isr_12;
        case 13: return (uint64_t)(uintptr_t)&__baken_isr_13;
        case 14: return (uint64_t)(uintptr_t)&__baken_isr_14;
        case 15: return (uint64_t)(uintptr_t)&__baken_isr_15;
        case 16: return (uint64_t)(uintptr_t)&__baken_isr_16;
        case 17: return (uint64_t)(uintptr_t)&__baken_isr_17;
        case 18: return (uint64_t)(uintptr_t)&__baken_isr_18;
        case 19: return (uint64_t)(uintptr_t)&__baken_isr_19;
        case 20: return (uint64_t)(uintptr_t)&__baken_isr_20;
        case 21: return (uint64_t)(uintptr_t)&__baken_isr_21;
        case 22: return (uint64_t)(uintptr_t)&__baken_isr_22;
        case 23: return (uint64_t)(uintptr_t)&__baken_isr_23;
        case 24: return (uint64_t)(uintptr_t)&__baken_isr_24;
        case 25: return (uint64_t)(uintptr_t)&__baken_isr_25;
        case 26: return (uint64_t)(uintptr_t)&__baken_isr_26;
        case 27: return (uint64_t)(uintptr_t)&__baken_isr_27;
        case 28: return (uint64_t)(uintptr_t)&__baken_isr_28;
        case 29: return (uint64_t)(uintptr_t)&__baken_isr_29;
        case 30: return (uint64_t)(uintptr_t)&__baken_isr_30;
        case 31: return (uint64_t)(uintptr_t)&__baken_isr_31;
        default: return 0;
    }
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

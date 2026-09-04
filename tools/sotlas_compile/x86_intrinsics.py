"""Extensão de backend x86-64 para o frontend Sotlas Bootstrap.

Mantém instruções privilegiadas e entry stubs fora do compilador de alto nível.
O módulo registra assinaturas Sotlas e injeta somente wrappers C/assembly
freestanding mínimos, que o GCC reduz para instruções reais da CPU.
"""

from __future__ import annotations


_MARKER = "/* SOTLAS_X86_64_PRIVILEGED_INTRINSICS */"

_C_INTRINSICS = r'''

/* SOTLAS_X86_64_PRIVILEGED_INTRINSICS */
typedef struct __attribute__((packed)) {
    uint16_t limit;
    uint64_t base;
} __sotlas_x86_dt_ptr;

static inline void __lgdt(uint64_t address) {
    __asm__ __volatile__("lgdt (%0)" : : "r"((uintptr_t)address) : "memory");
}

static inline void __lidt(uint64_t address) {
    __asm__ __volatile__("lidt (%0)" : : "r"((uintptr_t)address) : "memory");
}

/*
 * Ativa GDT e recarrega os seletores que possuem estado visível em long mode.
 * CS exige transferência far; apenas executar LGDT não troca o CS corrente.
 * A sequência push(selector)+push(rip)+lretq mantém o RSP líquido inalterado.
 */
static inline void __gdt_activate_segments(uint64_t base,
                                           uint16_t limit,
                                           uint16_t code_selector,
                                           uint16_t data_selector) {
    __sotlas_x86_dt_ptr gdtr = { limit, base };
    __asm__ __volatile__(
        "lgdt %0\n\t"
        "movw %w2, %%ax\n\t"
        "movw %%ax, %%ds\n\t"
        "movw %%ax, %%es\n\t"
        "movw %%ax, %%ss\n\t"
        "leaq 1f(%%rip), %%rax\n\t"
        "pushq %1\n\t"
        "pushq %%rax\n\t"
        "lretq\n\t"
        "1:\n\t"
        :
        : "m"(gdtr), "r"((uint64_t)code_selector), "r"(data_selector)
        : "rax", "memory"
    );
}

static inline void __lidt_table(uint64_t base, uint16_t limit) {
    __sotlas_x86_dt_ptr idtr = { limit, base };
    __asm__ __volatile__("lidt %0" : : "m"(idtr) : "memory");
}

static inline void __ltr(uint16_t selector) {
    __asm__ __volatile__("ltr %w0" : : "r"(selector) : "memory");
}

static inline uint64_t __read_cr2(void) {
    uint64_t value;
    __asm__ __volatile__("mov %%cr2, %0" : "=r"(value) : : "memory");
    return value;
}

static inline uint64_t __read_cr3(void) {
    uint64_t value;
    __asm__ __volatile__("mov %%cr3, %0" : "=r"(value) : : "memory");
    return value;
}

static inline void __write_cr3(uint64_t value) {
    __asm__ __volatile__("mov %0, %%cr3" : : "r"(value) : "memory");
}

static inline void __invlpg(uint64_t address) {
    __asm__ __volatile__("invlpg (%0)" : : "r"((uintptr_t)address) : "memory");
}

static inline uint64_t __rdtsc(void) {
    uint32_t low, high;
    __asm__ __volatile__("rdtsc" : "=a"(low), "=d"(high));
    return ((uint64_t)high << 32) | low;
}

static inline void __cpu_pause(void) {
    __asm__ __volatile__("pause");
}

/*
 * ABI terminal de troca de stack pós-cutover (Windows x64 / PE32+):
 *   RCX = novo topo da stack
 *   RDX = argumento entregue em RCX à continuação Sotlas
 *
 * O trampoline descarta a stack antiga, realinha RSP, reserva os 32 bytes de
 * shadow space exigidos pelo ABI e chama um callback genérico do frontend.
 * A continuação não deve retornar; se retornar, a CPU entra em HLT terminal.
 */
extern void sotlas_x86_post_cutover_entry(uint64_t argument);
__attribute__((naked, noreturn, unused)) static void
__stack_switch_to_post_cutover(uint64_t stack_top, uint64_t argument) {
    __asm__(
        "movq %rcx, %rsp\n\t"
        "andq $-16, %rsp\n\t"
        "movq %rdx, %rcx\n\t"
        "subq $32, %rsp\n\t"
        "call sotlas_x86_post_cutover_entry\n\t"
        "cli\n\t"
        "1: hlt\n\t"
        "jmp 1b\n\t"
    );
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
 * Em mudança de CPL/uso de IST a CPU pode acrescentar RSP/SS depois desses
 * campos. O dispatcher inicial não retorna; não há restauração/IRETQ ainda.
 *
 * O nome do callback pertence à ABI x86 do frontend, não ao Baken OS. Isso
 * evita acoplar o backend da linguagem a uma identidade de sistema operacional.
 */
extern void sotlas_x86_exception_dispatch(uint64_t frame_address);

__attribute__((naked, used)) static void __sotlas_x86_exception_common(void) {
    __asm__(
        "movq %rsp, %rcx\n\t"
        "andq $-16, %rsp\n\t"
        "subq $32, %rsp\n\t"
        "call sotlas_x86_exception_dispatch\n\t"
        "cli\n\t"
        "1: hlt\n\t"
        "jmp 1b\n\t"
    );
}

#define SOTLAS_X86_ISR_NOERR(n) \
    __attribute__((naked, unused)) static void __sotlas_x86_isr_##n(void) { \
        __asm__("pushq $0\n\tpushq $" #n "\n\tjmp __sotlas_x86_exception_common"); \
    }

#define SOTLAS_X86_ISR_ERR(n) \
    __attribute__((naked, unused)) static void __sotlas_x86_isr_##n(void) { \
        __asm__("pushq $" #n "\n\tjmp __sotlas_x86_exception_common"); \
    }

SOTLAS_X86_ISR_NOERR(0)
SOTLAS_X86_ISR_NOERR(1)
SOTLAS_X86_ISR_NOERR(2)
SOTLAS_X86_ISR_NOERR(3)
SOTLAS_X86_ISR_NOERR(4)
SOTLAS_X86_ISR_NOERR(5)
SOTLAS_X86_ISR_NOERR(6)
SOTLAS_X86_ISR_NOERR(7)
SOTLAS_X86_ISR_ERR(8)
SOTLAS_X86_ISR_NOERR(9)
SOTLAS_X86_ISR_ERR(10)
SOTLAS_X86_ISR_ERR(11)
SOTLAS_X86_ISR_ERR(12)
SOTLAS_X86_ISR_ERR(13)
SOTLAS_X86_ISR_ERR(14)
SOTLAS_X86_ISR_NOERR(15)
SOTLAS_X86_ISR_NOERR(16)
SOTLAS_X86_ISR_ERR(17)
SOTLAS_X86_ISR_NOERR(18)
SOTLAS_X86_ISR_NOERR(19)
SOTLAS_X86_ISR_NOERR(20)
SOTLAS_X86_ISR_ERR(21)
SOTLAS_X86_ISR_NOERR(22)
SOTLAS_X86_ISR_NOERR(23)
SOTLAS_X86_ISR_NOERR(24)
SOTLAS_X86_ISR_NOERR(25)
SOTLAS_X86_ISR_NOERR(26)
SOTLAS_X86_ISR_NOERR(27)
SOTLAS_X86_ISR_NOERR(28)
SOTLAS_X86_ISR_ERR(29)
SOTLAS_X86_ISR_ERR(30)
SOTLAS_X86_ISR_NOERR(31)

#undef SOTLAS_X86_ISR_NOERR
#undef SOTLAS_X86_ISR_ERR

static inline uint64_t __exception_stub_address(uint16_t vector) {
    switch (vector) {
        case 0: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_0;
        case 1: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_1;
        case 2: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_2;
        case 3: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_3;
        case 4: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_4;
        case 5: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_5;
        case 6: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_6;
        case 7: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_7;
        case 8: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_8;
        case 9: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_9;
        case 10: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_10;
        case 11: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_11;
        case 12: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_12;
        case 13: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_13;
        case 14: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_14;
        case 15: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_15;
        case 16: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_16;
        case 17: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_17;
        case 18: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_18;
        case 19: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_19;
        case 20: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_20;
        case 21: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_21;
        case 22: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_22;
        case 23: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_23;
        case 24: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_24;
        case 25: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_25;
        case 26: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_26;
        case 27: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_27;
        case 28: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_28;
        case 29: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_29;
        case 30: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_30;
        case 31: return (uint64_t)(uintptr_t)&__sotlas_x86_isr_31;
        default: return 0;
    }
}
'''


def install(bootstrap) -> None:
    """Registra os intrínsecos no módulo ``bootstrap`` de forma idempotente."""
    Type = bootstrap.Type
    Function = bootstrap.Function

    builtins = {
        "__lgdt": Function("__lgdt", [("address", Type("u64"))], Type("void"), [], public=True, attributes=["@system"]),
        "__lidt": Function("__lidt", [("address", Type("u64"))], Type("void"), [], public=True, attributes=["@system"]),
        "__gdt_activate_segments": Function(
            "__gdt_activate_segments",
            [("base", Type("u64")), ("limit", Type("u16")), ("code_selector", Type("u16")), ("data_selector", Type("u16"))],
            Type("void"), [], public=True, attributes=["@system"],
        ),
        "__lidt_table": Function(
            "__lidt_table", [("base", Type("u64")), ("limit", Type("u16"))], Type("void"), [],
            public=True, attributes=["@system"],
        ),
        "__ltr": Function("__ltr", [("selector", Type("u16"))], Type("void"), [], public=True, attributes=["@system"]),
        "__read_cr2": Function("__read_cr2", [], Type("u64"), [], public=True, attributes=["@system"]),
        "__read_cr3": Function("__read_cr3", [], Type("u64"), [], public=True, attributes=["@system"]),
        "__write_cr3": Function("__write_cr3", [("value", Type("u64"))], Type("void"), [], public=True, attributes=["@system"]),
        "__stack_switch_to_post_cutover": Function(
            "__stack_switch_to_post_cutover",
            [("stack_top", Type("u64")), ("argument", Type("u64"))], Type("void"), [],
            public=True, attributes=["@system"],
        ),
        "__invlpg": Function("__invlpg", [("address", Type("u64"))], Type("void"), [], public=True, attributes=["@system"]),
        "__rdtsc": Function("__rdtsc", [], Type("u64"), [], public=True, attributes=["@system"]),
        "__cpu_pause": Function("__cpu_pause", [], Type("void"), [], public=True, attributes=["@system"]),
        "__exception_stub_address": Function(
            "__exception_stub_address", [("vector", Type("u16"))], Type("u64"), [], public=True, attributes=["@system"]
        ),
    }
    bootstrap.BUILTIN_FUNCTIONS.update(builtins)

    if _MARKER not in bootstrap.PREAMBLE:
        bootstrap.PREAMBLE = bootstrap.PREAMBLE.rstrip() + _C_INTRINSICS + "\n"

# Sotlas Safety, Systems e C ABI — Contrato Normativo

**Status:** normativo para o frontend de produção do Sotlas.

Este documento define a separação entre código seguro, acesso privilegiado de
sistema e interoperabilidade externa. Quando houver conflito com documentação
histórica, este contrato prevalece para o compilador usado pelo kernel Baken.

## 1. Princípio de linguagem

Sotlas combina três objetivos deliberadamente separados:

- ergonomia de linguagem de alto nível para aplicações, UI e abstrações;
- fronteiras `unsafe` explícitas para operações que o compilador não consegue
  provar seguras;
- acesso direto, previsível e sem runtime obrigatório ao hardware e à ABI C.

A arquitetura conceitual é:

```text
                ┌──────────────────────┐
                │   Sotlas Safe Layer  │
                │ objects / arrays /   │
                │ optionals / UI / app │
                └──────────┬───────────┘
                           │
                    explicit @system
                           │
                ┌──────────▼───────────┐
                │ Sotlas Systems Layer │
                │ pointers / MMIO /    │
                │ DMA / interrupts     │
                └──────────┬───────────┘
                           │
                     extern "C"
                           │
            ┌──────────────▼──────────────┐
            │ C / ASM / Obj-C / firmware │
            └─────────────────────────────┘
```

Essas camadas não são equivalentes. Em especial, `@system` **não** desativa os
guardrails de memória.

## 2. `@system` é uma capability boundary

Uma função sem `@system` pertence à camada segura e não pode chamar diretamente
uma API marcada `@system` nem uma função FFI `extern "C"`.

```sotlas
@system
fn read_timer() -> u64 {
    return x86_read_timer();
}
```

`@system` significa que a função participa da camada de sistemas e pode acessar
APIs privilegiadas do Baken. Ele não significa "confie em tudo dentro desta
função".

Portanto isto continua inválido:

```sotlas
@system
fn bad(ptr: *mut u32) -> void {
    *ptr = 42; // erro: exige unsafe
}
```

## 3. `unsafe` é uma memory-safety boundary

`unsafe { ... }` autoriza somente o bloco lexical em que aparece. O escopo deve
ser tão pequeno quanto possível.

Operações que exigem `unsafe` incluem, no mínimo:

- desreferenciar `*mut T` ou `*const T`;
- indexar memória através de ponteiro cru;
- acessar campos através de ponteiro cru;
- invocar métodos através de ponteiro cru;
- criar/converter um endereço não nulo para ponteiro cru com `as *mut T` ou
  `as *const T`;
- chamar uma função FFI explicitamente declarada `unsafe fn`.

Exemplo rejeitado:

```sotlas
let ptr: *mut u32 = 0xDEADBEEF as *mut u32;
*ptr = 42;
```

Forma válida:

```sotlas
unsafe {
    let ptr: *mut u32 = 0xDEADBEEF as *mut u32;
    *ptr = 42;
}
```

O sentinela nulo pode ser construído sem `unsafe`:

```sotlas
let none: *mut u8 = null as *mut u8;
```

A construção do sentinela não acessa memória. Qualquer desreferenciamento
posterior permanece sujeito a `unsafe`.

## 4. Referências e ponteiros crus são conceitos diferentes

O lowering C pode representar ambos como endereços nativos, mas o frontend deve
preservar a diferença semântica:

- `&T` / `&mut T`: referência controlada pela linguagem;
- `*const T` / `*mut T`: ponteiro cru, sem prova automática de validade.

Essa distinção é metadado de compilação e não adiciona custo de runtime.

A longo prazo, borrow/lifetime analysis pode fortalecer referências sem alterar
a ABI dos ponteiros crus.

## 5. C ABI estável e bidirecional

Sotlas adota **C ABI** como fronteira externa estável. Isso permite integração
incremental com C, assembly, Objective-C e qualquer linguagem capaz de produzir
ou consumir símbolos com ABI C.

Importação de símbolo externo:

```sotlas
extern "C" fn foreign_sum(left: u32, right: u32) -> u32;
```

Bloco de declarações:

```sotlas
extern "C" {
    fn device_version() -> u32;
    unsafe fn driver_map_mmio(base: u64) -> *mut u8;
}
```

Exportação de Sotlas para consumidores externos continua sendo feita por símbolo
C estável:

```sotlas
@export
pub fn baken_driver_entry() -> u32 {
    return 0;
}
```

Assim a interoperabilidade é bidirecional:

```text
C / ASM / Objective-C -> extern "C" -> Sotlas
Sotlas -> @export -> C ABI -> C / ASM / Objective-C
```

Sotlas não precisa adotar o modelo de objetos, ARC ou permissividade de
Objective-C para interoperar com Objective-C. A interop acontece através da ABI
C explícita.

## 6. Memória estrangeira não ganha ownership Sotlas

Um parâmetro ou retorno de ponteiro cru vindo de `extern "C"` tem ownership e
lifetime **desconhecidos pelo compilador Sotlas**.

```sotlas
extern "C" fn driver_buffer() -> *mut u8;
```

Isto pode transportar o endereço na camada `@system`, mas não torna a memória
segura:

```sotlas
@system
fn read_first() -> u8 {
    let ptr = driver_buffer();
    return *ptr; // erro: falta unsafe
}
```

Forma explícita:

```sotlas
@system
fn read_first() -> u8 {
    let ptr = driver_buffer();
    unsafe { return *ptr; }
}
```

O compilador nunca infere ownership, lifetime ou exclusividade de um ponteiro
FFI apenas por ele ter atravessado a fronteira ABI.

## 7. `unsafe fn` em FFI

Quando a própria chamada possui pré-condições que o compilador não consegue
provar, a declaração deve carregar essa informação:

```sotlas
extern "C" {
    unsafe fn driver_map_mmio(base: u64) -> *mut u8;
}
```

Mesmo dentro de `@system`, a chamada exige um bloco `unsafe`:

```sotlas
@system
fn map_device(base: u64) -> *mut u8 {
    unsafe { return driver_map_mmio(base); }
}
```

Isso diferencia duas classes de FFI:

- `extern "C" fn`: a chamada em si possui contrato seguro, mas ponteiros crus
  continuam crus;
- `extern "C" { unsafe fn ...; }`: até a chamada exige aceitação explícita das
  pré-condições externas.

## 8. ABI suportada

Nesta fase, somente `extern "C"` é uma ABI externa estável. Outras strings de
ABI são rejeitadas pelo frontend.

Objective-C deve interoperar por wrappers/símbolos C, sem introduzir uma ABI
Objective-C implícita no núcleo da linguagem Sotlas.

## 9. Frontend canônico

O frontend de produção é o pipeline instalado por `tools.sotlas_compile`:

```text
source Sotlas
   -> lexer/parser bootstrap canônico
   -> extensões oficiais de gramática
   -> safety + FFI semantic pass
   -> type/interface validation
   -> lowering C11 freestanding
   -> compilador/linker do alvo
```

Nenhum parser auxiliar pode gerar corpos C ou possuir semântica de produção
independente. Parsers/ASTs históricos podem permanecer temporariamente para
migração de tooling e testes de sintaxe, mas o kernel e o CLI oficial devem
convergir para este pipeline.

## 10. Regra para o kernel Baken

Código do kernel deve seguir a seguinte disciplina:

1. usar abstrações seguras quando possível;
2. marcar a passagem para serviços privilegiados com `@system`;
3. limitar `unsafe` ao menor bloco que contém o acesso cru;
4. encapsular MMIO/DMA/ponteiros crus em APIs Sotlas tipadas;
5. manter firmware, C, assembly e Objective-C atrás de `extern "C"` ou
   `@export`;
6. nunca usar `@system` como substituto de `unsafe`.

O objetivo não é impedir programação bare-metal. É tornar cada ponto em que o
compilador deixa de poder provar segurança **visível, auditável e local**.

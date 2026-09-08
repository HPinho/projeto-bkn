# Sotlas Compiler Architecture

**Status:** target architecture for extracting Sotlas into its own repository.

Sotlas is a systems language first and a BakenOS implementation language second.
The compiler must therefore be independently versioned, testable and usable
without importing any BakenOS source tree. BakenOS consumes a pinned Sotlas
toolchain; Sotlas never imports BakenOS internals.

The repository organization is inspired by mature compiler projects such as
Swift, but the phase boundaries below are specific to Sotlas and its bare-metal
requirements.

## 1. Non-negotiable design goals

1. **One source language, one canonical parser, one semantic pipeline.**
2. **`@system` and `unsafe` are different effects.** `@system` grants access to
   privileged capabilities; lexical `unsafe` accepts memory operations the
   compiler cannot prove safe.
3. **Stable bidirectional C ABI.** C, assembly, Objective-C and other languages
   interoperate through `extern "C"` / exported C symbols.
4. **Freestanding is a first-class target.** The compiler must not assume an OS,
   allocator, exceptions, ARC, libc or a mandatory language runtime.
5. **External pointers have unknown ownership/lifetime.** FFI never silently
   promotes a raw pointer into a safe reference.
6. **Deterministic lowering.** The same source + compiler revision + target
   description must produce equivalent IR and object code.
7. **No target-specific UI or Baken policy in the compiler.** Drivers, widgets,
   wallpaper, filesystem policy and boot protocol belong to BakenOS libraries.

## 2. Target standalone repository

```text
sotlas/
├── README.md
├── LICENSE
├── CMakeLists.txt                 # transitional host build
├── compiler/
│   ├── driver/                    # sotlasc, options, diagnostics orchestration
│   ├── source/                    # source manager, spans, files, modules
│   ├── lexer/                     # tokens only
│   ├── parser/                    # canonical parser
│   ├── ast/                       # syntax tree + stable AST invariants
│   ├── sema/                      # names, types, overloads, conformance
│   ├── safety/                    # unsafe, ownership, effects, address spaces
│   ├── ffi/                       # C ABI import/export model
│   ├── sir/                       # Sotlas Intermediate Representation
│   ├── passes/                    # mandatory verification/lowering passes
│   ├── codegen/
│   │   ├── c11/                   # stage-0 bootstrap backend
│   │   └── x86_64/                # future native object-code backend
│   └── targets/                   # data layout / calling convention descriptions
├── stdlib/
│   ├── core/                      # zero-runtime primitives
│   ├── collections/               # hosted/optional pieces
│   └── system/                    # typed systems abstractions, no Baken policy
├── runtime/                       # optional runtime components only
├── include/
│   └── sotlas/capi/               # stable compiler/tooling C API
├── tools/
│   ├── sotlasc/
│   ├── sotlas-format/
│   └── sotlas-dump/
├── tests/
│   ├── lexer/
│   ├── parser/
│   ├── sema/
│   ├── safety/
│   ├── ffi/
│   ├── sir/
│   ├── codegen/
│   ├── diagnostics/
│   └── compatibility/
├── docs/
│   ├── language/
│   ├── compiler/
│   └── abi/
└── utils/
    ├── bootstrap/
    ├── ci/
    └── release/
```

The old `tools/sotlas` modules in the Baken repository are migration material,
not a second production frontend. Features that exist only there must either be
ported into the canonical pipeline with tests or explicitly retired.

## 3. Canonical compilation pipeline

```text
source bytes
   │
   ▼
SourceManager
   │
   ▼
Lexer ────────────────► token diagnostics
   │
   ▼
Parser
   │
   ▼
AST verifier
   │
   ▼
Name binding / module interfaces
   │
   ▼
Type checker
   │
   ▼
Safety + effect checker
   │      ├── raw pointer rules
   │      ├── ownership / lifetime facts
   │      ├── @system capabilities
   │      ├── FFI provenance
   │      └── address-space rules
   ▼
SIR generation
   │
   ▼
SIR verifier
   │
   ├──► C11 bootstrap lowering
   │
   └──► native x86-64 lowering
             │
             ▼
         object file
```

No phase may reparse source text to discover semantics already represented in
AST/SIR. Regex-based source scanning is acceptable only for development tooling,
never as the authoritative compiler semantic path.

## 4. Sotlas Intermediate Representation (SIR)

SIR should become the first representation where all language sugar has been
removed but systems semantics are still explicit. It must be typed and
verifiable before machine lowering.

Minimum information carried by an SIR value:

- scalar/aggregate type;
- mutability;
- safe reference vs raw pointer;
- foreign-pointer provenance;
- address space when known;
- function/effect requirements;
- source span for diagnostics.

Illustrative operations:

```text
%addr = sir.addr.from_int %raw : u64 -> rawptr<kernel,u8>   [unsafe]
%p2   = sir.ptr.cast %p : rawptr<kernel,u8> -> rawptr<kernel,u32>
%v    = sir.load %p2                                         [unsafe]
sir.store %v, %dst                                           [unsafe]
sir.call @driver_map_mmio(...)                               [system:mmio, ffi, unsafe]
```

The verifier, not the C backend, decides whether an operation is legal.

## 5. Address spaces

Raw pointers should eventually carry a compile-time address-space identity.
This gives Sotlas a systems property that a general-purpose safe language does
not need to prioritize.

Initial target set:

```text
kernel      ordinary kernel virtual address
user        userspace virtual address
phys        physical address token, not directly dereferenceable
mmio        volatile device mapping
dma         DMA-capable memory with ownership state
foreign     address/lifetime supplied by FFI
```

A physical address must not become dereferenceable merely by a cast. A mapping
operation changes address-space knowledge explicitly.

Future surface syntax may evolve independently; the semantic rule should be in
SIR from the beginning.

## 6. Capability effects

`@system` starts as one capability boundary but should be designed to refine
without ABI breakage:

```text
@system(io)
@system(mmio)
@system(msr)
@system(irq)
@system(dma)
@system(paging)
```

A safe wrapper may encapsulate a capability and expose a safe contract. The
caller is not automatically tainted merely because the implementation is in the
systems layer. Direct use of privileged intrinsics is checked against the
function's declared capabilities.

`unsafe` remains orthogonal: a function can require a system capability and
still need a small lexical unsafe block for a raw-memory operation.

## 7. FFI contract

The stable external ABI is C:

```sotlas
extern "C" {
    fn device_version() -> u32;
    unsafe fn driver_map_mmio(base: u64) -> *mut u8;
}
```

Rules:

- a foreign raw pointer never gains Sotlas ownership implicitly;
- raw-to-raw casts preserve foreign provenance;
- FFI `unsafe fn` requires lexical `unsafe` at the call site;
- exported Sotlas functions use stable C calling conventions and C-layout types;
- Objective-C interop is implemented through C-compatible wrappers rather than
  importing Objective-C's memory model into Sotlas.

## 8. Bootstrap and self-hosting

The current Python + C11 path is **stage 0**, not the final architecture.

```text
stage0: Python frontend -> C11 -> host C compiler
stage1: stage0 builds a Sotlas-written compiler
stage2: stage1 rebuilds the same compiler
```

A self-hosting milestone is accepted only when stage1 and stage2 pass semantic
and reproducibility checks. Until the native backend exists, C11 remains a
bootstrap implementation detail and must not define language semantics.

## 9. Diagnostics as an API

Every diagnostic should eventually contain:

- stable diagnostic code;
- severity;
- primary source span;
- optional secondary spans;
- concise explanation;
- actionable fix-it when unambiguous.

Example:

```text
SOTLAS-E0401 raw pointer dereference outside unsafe
  --> driver.sotlas:42:12
   |
42 |     return *ptr;
   |            ^^^^ requires `unsafe`
   |
help: wrap only the memory operation: unsafe { *ptr }
```

Tests should assert diagnostic codes rather than fragile full prose.

## 10. BakenOS integration after repository split

BakenOS should contain no compiler implementation. It should contain only a
pinned toolchain contract and build integration:

```text
bakenos/
├── boot/
├── kernel/
├── drivers/
├── userland/
├── sdk/
├── tests/
└── toolchain/
    └── sotlas.lock
```

`sotlas.lock` records at least:

- Sotlas repository URL;
- exact compiler commit or signed release;
- language version;
- C ABI version;
- SIR/object ABI version when those stabilize;
- required target/features.

CI must fail if a different compiler is silently used.

## 11. Cross-repository validation

A Sotlas compiler change is not considered Baken-compatible merely because the
compiler test suite passes. The release pipeline should have two levels:

1. Sotlas self-tests: lexer/parser/sema/safety/SIR/codegen;
2. Baken compatibility: build BakenOS at its declared compatibility fixture and
   run its QEMU hardware smoke tests.

Conversely, BakenOS CI uses only its pinned known-good Sotlas revision unless it
is explicitly running a toolchain-compatibility job.

This prevents compiler development from randomly breaking the operating system
while still allowing both repositories to evolve independently.
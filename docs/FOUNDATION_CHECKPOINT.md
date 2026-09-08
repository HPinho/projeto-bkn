# Baken OS — Foundation Checkpoint

Data de fechamento: 2026-09-08

## Status

**FASE 0 — FUNDAÇÃO BARE-METAL: FECHADA (100%)**

O checkpoint técnico da fundação é o commit:

```text
d5ad8e9163ee10b5e6d84162bc43e5a7722a00f5
feat(smp): preempt and resume real Ring 3 process on AP
```

Esse SHA foi validado pelos três workflows de referência no GitHub Actions:

- CI principal #987 — run `34271845602` — **PASS**;
- SMP #90 — run `34271845718` — **PASS**;
- NVMe-only #187 — run `34271845584` — **PASS**.

O commit documental posterior não altera o runtime; `d5ad8e9` permanece a referência de implementação congelada da Fase 0.

## O que este checkpoint prova

A fundação fechada possui e valida em execução QEMU:

- bootstrap UEFI restrito ao handoff;
- `ExitBootServices()` real e ausência de reentrada em firmware no grafo pós-cutover;
- stack própria, CR3 próprio, page tables W^X e guard stack;
- GDT, TSS per-CPU, IDT e tratamento de exceções/IRQs;
- PMM, VMM, direct-map e active page tables;
- PAT e framebuffer em WC;
- ACPI/MADT, LAPIC, IOAPIC, IRQs e LAPIC timer;
- SMP com APs online, scheduler por CPU e preempção por timer;
- TLB shootdown de mappings kernel globais entre CPUs;
- PCI e DMA nativos;
- xHCI/USB HID nativo na fixture de certificação;
- AHCI e NVMe como BlockDevice nativos;
- GPT/MBR/FAT32 sobre a camada de bloco;
- scheduler, threads, wait/wakeup, sleep, exit e reaper;
- processos com raiz CR3 privada;
- Ring 3, syscalls e user-copy;
- processo real pinned no CPU 1, execução CPL3, preempção pelo LAPIC timer, retorno comprovado a CPL3, syscall `exit`, retorno ao kernel CR3, reaper e teardown;
- build nativo, ISO UEFI, smoke QEMU e guardrails estáticos no mesmo SHA.

## Invariantes congeladas da fundação

Alterações futuras não podem regredir:

1. UEFI é apenas bootstrap. Nenhum `BootServices`, `RuntimeServices`, `SystemTable`, Pointer Protocol ou Block I/O UEFI pode reaparecer no runtime pós-cutover.
2. `BakenBootInfo` e o handoff pós-EBS não transportam pontes executáveis para firmware.
3. O compilador Sotlas permanece genérico: lexer/parser/AST/IR/lowering/ABI/backend/intrínsecos. UI, drivers e política do Baken pertencem ao código Sotlas do sistema.
4. W+X permanece proibido pelas APIs de page tables.
5. Mudanças de PTE kernel publicadas em SMP precisam manter coerência TLB.
6. TSS/RSP0 é per-CPU; Ring 3 não pode voltar a pressupor BSP.
7. Storage e USB da certificação precisam continuar sendo caminhos nativos reais, não mocks que apenas retornam sucesso.
8. `BAKEN:BARE_METAL_READY` continua sendo marker terminal de uma cadeia validada, nunca um marker incondicional.
9. CI geral, SMP e NVMe-only precisam permanecer verdes antes de um novo checkpoint arquitetural.

## O que NÃO está sendo declarado pronto

Fechar a Fundação não significa que o kernel inteiro terminou. Os itens abaixo pertencem às fases seguintes:

- migração genérica de processos BSP ↔ AP e política de load balancing;
- TLB shootdown específico por address space para PTEs de usuário modificadas enquanto o processo pode estar ativo em outro CPU;
- rastreamento de raiz de address space ativa por CPU para invalidação seletiva;
- revisão dos locks do registro de processos para espera de ACK/IPI sem deadlock;
- sincronização SMP completa do heap de propósito geral;
- prova de ownership/migração de contexto FPU/SIMD entre CPUs;
- AML, I2C-HID, rede, áudio e GPU;
- compositor, desktop, installer, OOBE, aplicativos e refinamento visual.

Esses itens não invalidam o fechamento da Fase 0: eles são evolução de Kernel Core, Platform/Drivers e User Experience sobre uma base bare-metal já comprovada.

## Próxima etapa oficial

**FASE 1 — KERNEL CORE**

A ordem recomendada é:

1. tornar locks envolvidos em address-space mutation/IPI compatíveis com SMP;
2. registrar a raiz ativa por CPU;
3. implementar shootdown de página por address space;
4. adicionar migração controlada de uma process thread entre BSP e AP;
5. provar `CPL3 → timer → scheduler → outro CPU → CPL3` sem stale TLB;
6. fechar ownership FPU/SIMD em migração;
7. tornar heap e demais estruturas globais necessárias realmente SMP-safe;
8. só então liberar afinidade `ANY` para processos de uso geral.

## Repositórios

- Baken OS: `HPinho/projeto-bkn`
- LangSotlas: repositório separado e **somente referência nesta etapa**; este checkpoint não requer nem autoriza alterações nele.

# Baken OS / Sotlas — Kernel Handoff

Atualizado em 2026-09-08.

## Estado atual

A **Fase 0 — Fundação Bare-Metal está fechada**.

Checkpoint técnico validado:

```text
d5ad8e9163ee10b5e6d84162bc43e5a7722a00f5
feat(smp): preempt and resume real Ring 3 process on AP
```

Esse SHA passou simultaneamente:

- CI principal #987 — run `34271845602`;
- SMP #90 — run `34271845718`;
- NVMe-only #187 — run `34271845584`.

O CI principal passou suíte completa, grafo Sotlas, build nativo, ISO e smoke QEMU. O SMP passou dispatch em AP, timer, TLB shootdown e processo Ring 3 real preemptado e retomado no CPU 1. O NVMe-only passou contracts, build, fixture e boot proof.

## Arquitetura que deve ser preservada

- UEFI é somente bootstrap.
- Depois de `ExitBootServices()`, o kernel não usa Boot Services, Runtime Services, Pointer Protocol, Block I/O UEFI ou `EFI_SYSTEM_TABLE`.
- O kernel, drivers, gráficos, UI e serviços pertencem ao código Sotlas.
- Python pertence ao host: compilador, build, testes e tooling.
- O compilador Sotlas deve permanecer genérico: lexer/parser/AST/IR/lowering/ABI/backend/intrínsecos, sem lógica específica de UI ou drivers do Baken.
- `BakenBootInfo` não pode voltar a transportar pontes executáveis para firmware.
- W+X continua fail-closed.
- PAT/WC, MMIO e page-table mutations pertencem ao VMM/active page tables.
- TSS/RSP0 é per-CPU.
- Hardware da certificação não pode ser substituído por mocks que apenas retornam sucesso.

## Fundação comprovada

### Boot / CPU / memória

- ExitBootServices real;
- stack trampoline e stack própria;
- CR3 Baken;
- W^X e guard stack;
- GDT, segment reload, TSS/LTR e IDT;
- PMM, VMM, direct-map e active page tables;
- PAT e framebuffer WC;
- auditoria zero-UEFI pós-cutover.

### Plataforma / hardware

- ACPI/MADT;
- LAPIC/IOAPIC;
- IRQ e LAPIC timer;
- PCI e DMA;
- xHCI/USB HID;
- AHCI;
- NVMe;
- BlockDevice;
- GPT/MBR/FAT32.

### Kernel Core já existente

Embora formalmente pertençam à evolução de Kernel Core, várias peças já estão implementadas e testadas:

- scheduler preemptivo;
- threads de kernel;
- wait/wakeup e sleep;
- thread exit e reaper;
- heap PMM-backed;
- registro de processos;
- address spaces privados;
- PID/TID e CR3 por processo;
- Ring 3;
- syscalls;
- user-copy;
- contexto FPU/SIMD por thread no caminho do scheduler;
- scheduler SMP;
- TLB shootdown para mappings kernel-global;
- processo real pinned em AP;
- timer preemptando frame CPL3 no AP;
- retorno comprovado ao mesmo processo em CPL3 antes do `exit`;
- retorno ao kernel CR3, reaper e teardown.

## Limites atuais — não confundir com regressão da Fundação

O checkpoint não declara prontos os seguintes comportamentos genéricos:

1. **Migração irrestrita de processos entre CPUs**
   - o processo SMP provado é explicitamente pinned no CPU 1;
   - `scheduler_create_process_thread()` continua preservando o comportamento BSP histórico;
   - a API `scheduler_create_process_thread_on_cpu()` permite prova controlada em AP.

2. **TLB shootdown por address space de usuário**
   - o shootdown kernel-global está implementado;
   - mappings de usuário do probe são construídos antes do dispatch e desmontados depois que o AP voltou ao kernel root;
   - ainda não liberar mutação concorrente de PTE de processo sem um protocolo root-aware.

3. **Process registry lock + IPI**
   - antes de esperar ACK remoto durante mutação de address space, a aquisição do lock deve ser compatível com recebimento de IPI;
   - evitar spin com IF=0 que possa bloquear o próprio shootdown necessário para progredir.

4. **Heap SMP**
   - revisar a sincronização do heap global antes de permitir uso concorrente amplo por processos/serviços em múltiplos CPUs.

5. **FPU/SIMD em migração**
   - save/restore passa pelo scheduler e a prova CPL3/AP atravessa esse caminho;
   - ainda falta prova explícita de migração da mesma thread entre CPUs preservando ownership e estado SIMD.

## Próximo trabalho — Fase 1

A ordem recomendada é esta:

### 1. Active address-space tracking per CPU

Adicionar uma camada baixa que saiba qual CR3/root está ativo em cada CPU sem criar dependência circular scheduler ↔ memory.

A atualização deve ocorrer sempre que o scheduler:

- seleciona uma process thread;
- troca CR3;
- retorna ao idle/kernel root.

### 2. Process-root TLB shootdown

Criar uma operação conceitualmente equivalente a:

```text
tlb_shootdown_address_space_page(root, virtual_address)
```

Requisitos:

- invalidar somente CPUs que podem possuir tradução daquele root;
- permitir requester BSP ou AP;
- ACK/generation sem depender de requester fixo;
- funcionar se o requester não estiver usando o root alvo;
- preservar o shootdown kernel-global existente.

### 3. Tornar locks envolvidos IPI-friendly

Antes de segurar lock de processo enquanto espera shootdown remoto:

- usar política semelhante ao active-page-table lock;
- `irq_save_disable` + `try_lock`;
- se ocupado, restaurar IRQ e `pause` antes de tentar novamente;
- nunca criar deadlock onde um CPU espera ACK de outro que está girando com IF=0.

### 4. Migração controlada BSP ↔ AP

Adicionar uma prova real:

```text
process thread em CPL3 no BSP
→ timer/preempção
→ thread volta READY
→ scheduler a seleciona no AP
→ CR3 correto
→ TSS.RSP0 do AP correto
→ user state continua
→ syscall
→ exit
→ kernel root
→ reaper
```

A prova deve rejeitar qualquer `BAKEN:HEX=E:` e registrar CPU antes/depois.

### 5. FPU/SIMD migration proof

A mesma process thread deve:

- gravar estado XMM/x87 no primeiro CPU;
- ser preemptada/migrada;
- restaurar exatamente o estado no segundo CPU;
- terminar sem dupla execução/ownership concorrente.

### 6. Heap e estruturas globais SMP-safe

Revisar estruturas globais que ainda dependem apenas de exclusão por IRQ local e convertê-las para sincronização SMP apropriada quando necessário.

### 7. Só então liberar affinity ANY para processos

Não trocar globalmente:

```text
SCHEDULER_THREAD_AFFINITY_CPU = 0
```

para `ANY` antes de page-table coherence, locks e FPU ownership estarem comprovados.

## Fases posteriores

### Fase 2 — Platform / Drivers

- AML;
- I2C-HID;
- rede;
- áudio;
- GPU/aceleração.

### Fase 3 — User Experience

- compositor;
- desktop/window manager;
- installer/OOBE;
- animações;
- aplicativos.

## Validação obrigatória para mudanças futuras

Antes de chamar um novo checkpoint de estável, executar e conferir o SHA exato em:

```text
CI principal
SMP verification
NVMe-only verification
```

Além disso, manter os guardrails de:

- zero firmware reentry;
- compilador sem UI/driver Baken específico;
- W^X;
- TLB/SMP;
- storage real;
- USB real;
- PAT/WC;
- processo/Ring3/syscall/reaper.

## LangSotlas

`HPinho/LangSotlas` permanece **somente leitura/referência** neste trabalho. Não modificar esse repositório sem instrução explícita do usuário.
# Diagnóstico de CI — 2026-09-08 / HEAD 6efb9eb

- Os três runs do HEAD falharam: CI #998 no smoke QEMU, SMP #101 durante a
  instalação de dependências e NVMe-only #198 no smoke QEMU.
- A suíte local do HEAD passou: **1.109 testes**; build EFI passou com **141
  módulos / 143 objetos**; o smoke single-core local original também passou.
- Causa de instabilidade isolada entre o último SHA verde e o HEAD: a espera
  final da probe de wait/sleep executava `scheduler_yield()` em laço apertado,
  gerando interrupções de software enquanto dependia de ticks LAPIC reais.
- Correção local: `x86_halt_until_interrupt()` exige IF=1 e executa `HLT`;
  a probe agora dorme até um IRQ real, sem medir tempo por velocidade de host e
  sem tempestade de yield. Smoke single-core corrigido passou, incluindo Ring 3,
  syscalls, user-copy e loader, sem `BAKEN:HEX=E:`.
- O runner local ganhou `--smp` e `--required-marker`. O smoke local com 2 CPUs
  passou exigindo `SMP_PROCESS_TLB_READY` e `SMP_RING3_ON_AP_READY`, além do
  gate completo single-core; portanto cobriu AP dispatch, timer, TLB shootdown,
  retomada CPL3 no AP e teardown sem marcador de exceção.
- A falha de instalação do SMP é independente do kernel. Os três workflows
  agora usam `Acquire::Retries=3` tanto em `apt-get update` quanto em `install`,
  preservando os timeouts existentes.
- O acesso autenticado aos artefatos GitHub foi bloqueado pelo controle de
  segurança do navegador. Diagnóstico baseado em etapas públicas, diff entre
  SHAs e reprodução local; validar os três workflows no SHA novo antes de
  declarar a correção definitivamente verde.

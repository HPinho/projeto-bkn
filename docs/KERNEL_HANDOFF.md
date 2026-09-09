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
- O CI #999 do primeiro patch mostrou a localização exata: parou em
  `WAIT_BLOCKED`, antes de `WAIT_WAKE`. O HLT apenas no fechamento final não
  cobria os dois handoffs anteriores, que ainda dependiam de yields síncronos.
- Correção complementar: a probe declaradamente BSP-only agora é criada com
  afinidade CPU 0, e as esperas por BLOCKED, RESUMED e reaper avançam todas por
  IRQ LAPIC real via `x86_halt_until_interrupt()`. O runtime não usa mais yield
  para orquestrar essa certificação. Validar novamente CI/SMP/NVMe no novo SHA.
- Diagnóstico final refinado: a prova agora publica duas threads reais, waiter e
  waker, ambas com afinidade BSP. Waiter bloqueia; waker executa o wake e termina;
  o bootstrap aguarda timer/reaper. A criação ganhou helper interno que publica
  `READY` e afinidade sob o mesmo scheduler lock, eliminando a janela `ANY`.
- Validação final local: **1.111 testes em 68,931 s**, build **141 módulos / 143
  objetos**, smoke single-core e smoke SMP com os marcadores finais completos.
- A falha de instalação do SMP é independente do kernel. Os três workflows
  agora usam `Acquire::Retries=3` tanto em `apt-get update` quanto em `install`,
  preservando os timeouts existentes.
- O acesso autenticado aos artefatos GitHub foi bloqueado pelo controle de
  segurança do navegador. Diagnóstico baseado em etapas públicas, diff entre
  SHAs e reprodução local; validar os três workflows no SHA novo antes de
  declarar a correção definitivamente verde.

# Diagnóstico de CI — 2026-09-08 / tracking de CR3 por CPU

- Os runs CI #1002, NVMe-only #202 e SMP #105 falharam no SHA `915a0d6`.
- A CI principal encontrou três contratos antigos que ainda exigiam a chamada
  direta ao scheduler; eles agora validam o wrapper e a ordem seleção ->
  publicação do CR3.
- A falha bare-metal foi reproduzida localmente: o serial parava no primeiro
  tick, em `BAKEN:HEX=T:00000001`. O timer podia chegar antes de o scheduler
  estar ativo e antes do registro do BSP no shootdown, mas o wrapper tentava
  publicar o CR3 e entrava no caminho fail-closed.
- A publicação agora é obrigatória somente quando `scheduler_is_active()`;
  antes disso não existe decisão de scheduling a publicar. Depois da ativação,
  uma falha de tracking continua parando o kernel.
- Validação local final: **1.115 testes**, build **141 módulos / 143 objetos**,
  smoke single-core completo e smoke SMP completo até
  `SMP_PROCESS_TLB_READY` e `SMP_RING3_ON_AP_READY`, sem `BAKEN:HEX=E:`.

# Estado da fundação do kernel — 2026-09-09

## Concluído e comprovado

- Cutover UEFI, `ExitBootServices`, W^X, CR3, GDT/IDT/TSS/IST e memória física
  e virtual própria do kernel.
- ACPI, LAPIC/IOAPIC, timer, IRQs, PCI/DMA, xHCI/HID, AHCI/NVMe, GPT/FAT32 e
  framebuffer PAT/WC.
- Scheduler preemptivo, threads de kernel, reaper, cache de stacks, yield,
  wait queues, sleep por LAPIC e heap geral.
- Processos, espaços de endereço, Ring 3, syscalls, cópia usuário/kernel,
  carregador de userspace e preservação de contexto FPU/SIMD.
- SMP: despacho em AP, timer no AP, heap concorrente, shootdown TLB root-aware,
  migração de processo e retomada Ring 3/FPU no AP.

## Correção de estabilidade da CI

- O workflow principal podia expirar depois de `WAIT_BLOCKED`: a prova dependia
  de uma thread waker ser escolhida imediatamente sob host carregado.
- A prova agora executa a sequência determinística
  `yield -> blocked -> wake pelo bootstrap -> yield -> resume`; o sleep e o
  reaper continuam dependentes de IRQs LAPIC reais.
- O smoke principal recebeu timeout próprio de 180 s e limite de etapa de cinco
  minutos. Isso preserva falha finita e elimina falsos negativos por runner
  lento.

## Evidência local deste estado

- **1.132 testes** aprovados.
- Build Sotlas: **141 módulos / 143 objetos**.
- QEMU single-core: `WAIT_WAKE`, `WAIT_RESUME`, sleep, Ring 3, syscall,
  user-copy e loader aprovados.
- QEMU SMP: heap concorrente, TLB, Ring 3, migração de processo e FPU aprovados
  até `SMP_FPU_MIGRATION_READY`, sem `BAKEN:HEX=E:`.

## Próxima fase

Esta fundação não equivale ao sistema operacional completo. O próximo trabalho
deve concentrar-se em rede, áudio, GPU/aceleração, política de processos e
serviços de userspace, mantendo os três gates CI/NVMe/SMP obrigatórios.

## Fechamento do Kernel Core — pendente de certificação GitHub

A fronteira que faltava para isolar uma falha de userspace foi implementada no
commit atual: o stub de exceção salva todos os GPRs, identifica CPL3
pelo `CS`, termina a thread atual, permite o reaper soltar a referência do
processo e retorna ao scheduler por `IRETQ` usando o frame normalizado da
próxima thread. O probe lê deliberadamente a guard page de stack não mapeada;
ele só é aprovado após teardown completo do address space e o marker
`BAKEN:USER_FAULT_ISOLATED_READY`.

O comportamento de CPL0 não muda: exceções do kernel continuam terminais para
não ocultar corrupção de memória ou de controle. A suíte local e o grafo Sotlas
passaram; esta máquina não possui o cross-compiler UEFI, portanto a confirmação
de boot cabe aos três workflows GitHub do mesmo SHA. Até eles passarem, não
tratar este fechamento como certificado.

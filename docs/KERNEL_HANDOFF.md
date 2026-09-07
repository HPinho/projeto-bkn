# Baken OS / Sotlas — continuidade do kernel

Atualizado em 2026-09-07. Este documento distingue implementação, contratos
estáticos e prova de execução; não equivale a uma certificação do kernel.

## Ponto de partida confirmado

- Repositório: https://github.com/HPinho/projeto-bkn
- Checkout: `E:\projeto-bkn`, branch `main`, base atual `8f9050d`.
- Kernel escrito em `.sotlas`; compilador em `tools/sotlas_compile/`.
- Acesso ao terminal: prefixar comandos com `rtk`; usar `rtk proxy` se o
  comando filtrado não funcionar. Ler as instruções AGENTS/RTK antes de trabalhar.
- Não descartar alterações locais nem declarar funcionalidades completas por
  existirem testes que apenas procuram texto no código.

## Evidência já obtida

- Confirmados no GitHub: CI principal **34156827304** e NVMe-only
  **34156827300**, ambos com sucesso em `8f9050d5dd7d695be04c9c39765f5b3f68c89a0d`.
  Incluem a prova CR3 primeira → segunda → primeira → kernel e os gates
  reforçados. Essa validação não se estende a alterações posteriores.
- CI principal 34155388044 e NVMe-only 34155387973 na base `dcd48c9`
  consultados no GitHub: sucesso. O NVMe exige `SCHEDULER_ROUND_TRIP`.
- Frame sintético de thread corrigido: 21 qwords / 168 bytes, incluindo
  RIP, CS, RFLAGS, RSP e SS; arquivo `kernel/src/arch/x86_64/thread_context.sotlas`.
- Rodada local anterior: 987 testes passaram; rodada direcionada posterior:
  50 testes passaram. Não somar essas contagens: há sobreposição.
- Grafo Sotlas: 126 módulos, sem módulos fora da rota ou raízes órfãs.

## Implementado na base (alcance limitado ao código e smoke existentes)

- Cutover UEFI, ExitBootServices, stack/CR3, GDT/TSS/IDT, PMM/VMM/direct-map.
- ACPI/APIC/timer, PCI/DMA, xHCI/HID, AHCI/NVMe, probes GPT/FAT32, PAT/WC.
- Scheduler e threads de kernel: round trip, yield, wait/wakeup, sleep,
  thread_exit/reaper e liberação de stack.
- Heap PMM-backed com split/coalesce/reuso: 256 descritores; exclusão por
  interrupções locais, NÃO é sincronização SMP. Arenas permanecem reservadas.
- `kernel/src/process/address_space.sotlas`: raízes privadas, mapeamento de
  páginas de usuário e self-test de backing distinto para mesmo VA.
  NÃO executa Ring 3 nem troca CR3 para rodar um processo.

## Alterações publicadas em 8f9050d

- `tools/scripts/verify_kernel_smoke.py`: gate comum que rejeita qualquer
  `BAKEN:HEX=E:` e exige heap, isolamento, scheduler, yield, wait, sleep e reaper.
- `tests/test_kernel_smoke_gate.py`: testes comportamentais e integração.
- `.github/workflows/baken_ci.yml` e `baken_nvme_only.yml`: usam esse gate;
  NVMe também limita instalação de dependências a dez minutos.
- Publicadas pelo usuário; os dois workflows acima passaram.

## Sequência de implementação restante

1. Prova controlada CR3 concluída no smoke. Agora auditar ownership/lifetime
   para processos duradouros, além do self-test temporário.
2. Processos/PID/TID e vínculo thread–address space; garantir reaper seguro.
3. Ring 3: stack de usuário, frame de entrada, TSS.RSP0 e caminho de retorno
   seguro; validar exceções e permissões de páginas em QEMU.
4. Syscalls: definir ABI, entrada/saída, validação de ponteiros e cópias
   usuário/kernel; impedir acesso direto arbitrário à memória do kernel.
5. Loader userspace Sotlas: formato, segmentos, limites, W^X, entrypoint,
   stack e rejeição de imagens inválidas. Primeiro programa isolado mínimo.
6. Contexto FPU/SIMD por thread: política de CPU e save/restore testado.
7. SMP: startup AP, estado por CPU, locks, TLB shootdown e scheduler multicore.

Cada etapa precisa de testes negativos e prova runtime, não apenas markers
incondicionais. O objetivo atual é implementar incrementalmente esta sequência;
não afirmar que o kernel inteiro está pronto antes dessas provas.

## Comandos de validação

```powershell
rtk proxy py -m unittest discover -s tests
rtk proxy py tools/sotlas_compile/compiler.py check kernel/src/main.sotlas
rtk proxy git diff --check
```

Build/QEMU de referência: os dois workflows em `.github/workflows/`.
Verificar o SHA do run antes de atribuir sucesso a alterações novas.

## Histórico da etapa CR3 (já publicada)

- Documento criado primeiro, conforme pedido do usuário.
- Implementado localmente `process_address_space_cr3_probe`: dentro do self-test
  BSP com IRQs desligadas, alterna primeira raiz → segunda → primeira, lê o mesmo
  VA por operações voláteis e restaura CR3 original antes de liberar tabelas.
  A prova é pré-requisito do marker existente `PROCESS_ISOLATION_READY`.
- Atualizado teste que antes proibia toda troca CR3: agora exige restauração,
  leituras voláteis e ausência de retorno antecipado na região de troca.
- Testes direcionados: 17 passaram; grafo: 126 módulos válidos.
- Suíte completa da nova etapa: **988 testes passaram em 63,571 s**.
  Build nativo: compilação dos módulos passou, mas link EFI falhou:
  `kernel__storage__fat32_path.o: undefined reference to memset`.
  GCC encontrado pelo compilador em `tools/w64devkit/bin/gcc.exe`, embora fora
  do PATH. Falha do toolchain local; os builds/QEMU Linux de `8f9050d` passaram.
  Saída separada: `build/cr3-probe/BOOTX64.EFI`, manifest
  `build/cr3-probe.manifest.json`. Não confundir com imagem anterior de CI.
- Nenhum suporte Ring 3/syscall/SMP foi adicionado nesta etapa. Próximo passo:
  prover/verificar as primitivas freestanding exigidas pelo GCC (`memset` é a
  referência não resolvida observada; não mascarar erro nem adicionar libc ao
  kernel), repetir link e validar boot/QEMU antes de avançar para lifetime/PID/TID e
  contexto de processo. A etapa CR3 foi publicada pelo usuário em `8f9050d`.

## Etapa atual — registro de processos (alterações locais)

- Implementado `kernel/src/process/registry.sotlas`: 16 slots BSP, PID 0
  reservado, PIDs monotônicos sem wrap/reuso, ownership privado das raízes.
- APIs kernel-only: `process_create`, `process_destroy`, `process_retain`,
  `process_release`. Todas preservam IF; não são APIs de syscall.
- Destruição exige zero referências e sucesso de `process_address_space_destroy`
  (este também rejeita raiz ativa ou folhas user presentes).
- Self-test de boot: enche os slots, recusa tabela cheia, bloqueia destruição
  com referência, rejeita underflow e PID antigo, reutiliza slot com PID novo,
  verifica devolução da contagem de páginas PMM ao valor inicial.
- Integrado após a prova CR3 e antes de `scheduler_initialize`. O gate comum
  dos dois workflows exige `BAKEN:PROCESS_REGISTRY_READY`; o marker só é
  emitido depois de ativação bem-sucedida. Ainda sem prova QEMU deste patch.
- `tests/test_process_registry.py`: contratos estáticos complementares; não
  confundir com execução do self-test em hardware.
- Grafo: 127 módulos. Rodada intermediária: 995 testes passaram.
- Corrigida a referência local ausente a `memset`: suporte ABI freestanding
  em `tools/sotlas_compile/runtime/memory.c`, compilado pelo driver modular.
  Implementa `memset`, `memcpy`, `memmove`, `memcmp` por bytes voláteis para
  evitar chamadas recursivas geradas pelo otimizador. Não vincula libc ao EFI.
- `tests/test_freestanding_memory.py` compila e executa essas funções com GCC;
  prova de limites, retorno, overlap e comparação unsigned passou localmente.
- Build EFI local após essa correção: **sucesso, 129 objetos / 127 módulos**,
  saída `build/process-registry/BOOTX64.EFI`. A falha `memset` está resolvida
  nesse build. Nenhum QEMU local foi executado.
- Atualizado `tests/test_sotlas_resolver.py`: exige o objeto ABI adicional e
  o bootloader explicitamente. **Suíte final: 996 testes passaram em 62,249 s**.
  `git diff --check` passou; imagem identificada como PE x86-64 / EFI application.
- Ainda pendente: vincular referências ao scheduler/reaper e executar processos
  de usuário. Não confundir registro de processos com Ring 3 funcional.
- Limitação de criação: a raiz ativa deve ser a raiz supervisor do kernel;
  antes de criar processos a partir de outro processo será necessário fixar
  uma raiz canônica do kernel em vez de copiar a raiz corrente.
- Próxima implementação: vínculo thread–PID retido antes de publicar thread,
  liberação após execução/reaper, contexto CR3/TSS por processo, depois Ring 3.
  FPU/SIMD, syscalls, loader userspace e SMP continuam pendentes.
- Alterações desta etapa ainda sem commit/push. Publicar e acompanhar ambos os
  workflows no SHA novo antes de afirmar validação runtime do registro.

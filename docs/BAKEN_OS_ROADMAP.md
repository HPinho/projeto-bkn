# Baken OS — Roadmap de desenvolvimento

Atualizado em 2026-09-09. Este documento separa **implementado**,
**certificado** e **planejado**. Um item só muda para certificado quando os
gates exigidos passam no mesmo commit da `main`.

## Marco imediato — Fechar auditoria rigorosa do Kernel Core

**Estado: gates atuais certificados; fechamento arquitetural ainda pendente.**

O commit `b703cb2e77442873910268532d6fc5272a51873f` passou nos três gates
obrigatórios do mesmo SHA em 2026-09-09:

| Gate | Resultado |
|---|---|
| CI principal #1017 / `34336389649` | ✅ PASS |
| SMP #120 / `34336389592` | ✅ PASS |
| NVMe-only #217 / `34336389646` | ✅ PASS |

O Kernel Core já contém boot sem runtime UEFI, PMM/VMM, SMP, scheduler,
processos, address spaces privados, Ring 3, syscall, FPU/SIMD e drivers de
certificação. A última fronteira adicionada é isolamento de exceções CPL3:
uma falha de userspace deve encerrar apenas seu processo e voltar ao scheduler;
uma falha CPL0 permanece terminal.

Critério de saída:

- CI geral, NVMe-only e SMP verdes no mesmo SHA;
- QEMU exige `BAKEN:USER_FAULT_ISOLATED_READY` e não pode emitir
  `BAKEN:HEX=E:`;
- prova SMP preserva heap, TLB, CR3, Ring 3 e FPU durante migração, incluindo
  um fault CPL3 executado em AP;
- o workflow deve identificar explicitamente o primeiro marker ausente.

Bloqueadores técnicos ainda abertos pela auditoria:

- tornar o snapshot de exceção por-CPU (ou sincronizado), pois o registro atual
  é global e duas CPUs podem sobrescrever o diagnóstico simultaneamente;
- classificar vetores: somente falhas síncronas recuperáveis de CPL3 podem
  terminar o processo. NMI, double fault e machine check precisam permanecer
  terminais, mesmo quando interrompem CPL3;
- executar a prova de fault CPL3 também em AP. O SMP #120 voltou a passar e
  certifica o gate atual, mas ainda não cobre essa combinação arquitetural.

## Fase 2 — Platform e drivers de produção

Objetivo: transformar o hardware já certificado em serviços estáveis de
plataforma, com descoberta, recuperação e contratos de driver.

- AML/ACPI de produção e gerenciamento de energia;
- rede: NIC, ARP, IPv4/IPv6, UDP/TCP e DHCP;
- armazenamento de produção: cache, VFS inicial e montagem segura;
- áudio; GPU/framebuffer acelerado e composição básica;
- HID adicional (I2C-HID), hot-plug e telemetria de drivers.

Saída: drivers possuem timeouts, erros explícitos, testes em QEMU e interfaces
de kernel estáveis; a ausência de um dispositivo opcional não pode derrubar o
sistema.

## Fase 3 — Serviços e userspace

Objetivo: fazer processos reais úteis sobre a base de Ring 3.

- ABI de syscall versionada, handles e permissões;
- VFS, arquivos, processos executáveis Sotlas e carregador de programas;
- IPC, serviço de init, logging e gerenciamento de processos;
- modelo de memória futuro: COW/demand paging somente após a política de
  falhas e TLB estar comprovada;
- empacotamento, atualização e diagnóstico em userspace.

Saída: inicialização de serviços sem privilégios e aplicativos Sotlas isolados
capazes de usar filesystem e IPC.

## Fase 4 — Experiência Baken

Objetivo: entregar um sistema utilizável, não apenas um kernel.

- compositor, janelas, input, fontes e acessibilidade;
- desktop, shell, instalador e OOBE;
- aplicativos-base, configurações e recuperação;
- testes de jornada completa em imagem instalada.

## Regras de prioridade

1. Não iniciar funcionalidade de alto nível para contornar um gate vermelho.
2. Cada marco precisa de prova de runtime, não apenas teste de fonte.
3. Drivers e serviços opcionais degradam com diagnóstico; integridade de
   memória, isolamento e scheduler permanecem fail-closed.
4. Mudanças de processo, page table, CR3, TLB e FPU exigem CI geral + SMP.

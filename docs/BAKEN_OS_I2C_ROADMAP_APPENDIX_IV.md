# Baken OS — Trilha B2 / I2C Foundation Roadmap Appendix IV

Continuação **append-only** de `BAKEN_OS_I2C_ROADMAP_APPENDIX_III.md`. Os apêndices anteriores permanecem intocados.

## 2026-09-13 — I2C-2a reprovado no gate SMP

O primeiro candidato do registry/lifecycle foi publicado em:

```text
022bbec682d6ea5730c110919f21f044ffec8849
feat(i2c): add controller registry lifecycle
```

Resultado exact-SHA:

- CI #1220 ✅
- SMP #323 ❌
- NVMe-only #420 ✅
- HID Dual-device #79 ✅

**Estado: ❌ NÃO CERTIFICADO — 3/4.**

A falha SMP ocorreu depois de contratos e build nativo verdes, durante a primeira prova QEMU. O boot alcançou `BAKEN:SMP_THREAD_ON_AP` e, na janela da prova do timer periódico do AP, reportou uma exceção terminal:

```text
vector = 0x0E (#PF)
error  = 0x00000000   # página não presente, read, supervisor
RIP    = 0x10011BA5
CS     = 0x00000008
RFLAGS = 0x00000082
CPU    = 1
thread = 0
```

A serial ficou parcialmente intercalada com `BAKEN:SMP_TIMER_ON_AP`, porém o dispatcher de exceção produziu um snapshot coerente de #PF CPL0 no AP. O mesmo trecho havia passado 3/3 no SMP #322 da baseline I2C-1d.

O módulo `i2c_controller_registry` ainda não é inicializado nem chamado no runtime deste estágio. Portanto não há evidência de uma execução I2C causando o fault; a adição do objeto alterou layout/timing e expôs uma fragilidade latente na prova SMP/kernel. O candidato permanece congelado e nenhum I2C-2b pode começar.

### Correction-only de diagnóstico

O próximo SHA adiciona somente observabilidade de host/QEMU, sem alterar fontes funcionais do kernel:

- novo workflow `baken_smp_fault_diag.yml`;
- recompila o mesmo grafo Sotlas/EFI;
- executa QEMU SMP com `-d int` para capturar estado de CPU/`CR2` no #PF;
- gera `nm` ordenado do `BOOTX64.EFI`;
- associa automaticamente o RIP ao símbolo mais próximo;
- produz `objdump` ao redor do RIP;
- preserva serial, log de interrupções, symbol map e EFI como artefatos diagnósticos;
- roda até três boots diagnósticos e encerra cedo se reproduzir a exceção.

Essa etapa **não certifica** o I2C-2a, não muda scheduler, MMU, I2C ou LangSotlas e não mascara o gate SMP. Depois da evidência de `CR2 + símbolo`, a correção funcional será aplicada somente à causa comprovada e deverá novamente fechar CI + SMP + NVMe-only + HID Dual-device no mesmo SHA.

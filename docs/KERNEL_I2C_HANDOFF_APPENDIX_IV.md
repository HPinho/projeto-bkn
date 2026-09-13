# Baken OS — Trilha B2 / I2C Kernel Handoff Appendix IV

Continuação operacional **append-only** de `KERNEL_I2C_HANDOFF_APPENDIX_III.md`. Os handoffs anteriores permanecem intocados.

## Candidato I2C-2a — resultado reprovado

```text
022bbec682d6ea5730c110919f21f044ffec8849
feat(i2c): add controller registry lifecycle
```

Gates:

- CI #1220 ✅
- SMP #323 ❌
- NVMe-only #420 ✅
- HID Dual-device #79 ✅

O SHA é **não certificado (3/4)** e deve permanecer no histórico exatamente assim.

### Falha observada

O SMP #323 passou contratos e build nativo, mas a primeira prova QEMU terminou com #PF no AP durante a transição da prova do timer periódico:

```text
E = 0000000E
 e = 00000000
 i = 10011BA5
 c = 00000008
 f = 00000082
 q = 00000001
 t = 00000000
```

Interpretação operacional:

- page fault de página não presente, leitura supervisor;
- CPU slot 1;
- nenhum thread dinâmico current no momento do snapshot (`thread_id=0`);
- janela imediatamente posterior a `SMP_THREAD_ON_AP`, próxima de `SMP_TIMER_ON_AP`;
- baseline anterior I2C-1d/SMP #322 passou a mesma sequência 3/3.

O registry I2C não é chamado no runtime deste candidato. A investigação mostrou que o scheduler AP usa switch-commit em duas fases: `idle_epoch` prova seleção lógica do idle frame e a publicação `owner=NONE` só ocorre numa entrada posterior do scheduler, quando o IRQ anterior já deveria ter concluído o IRET. O mapper W^X também usa `max(VirtualSize, RawSize)` e alinhamento por página, então uma hipótese simples de `.bss` truncada por `RawSize` não foi confirmada.

## Correction-only atual — diagnóstico externo do #PF

O próximo commit deve alterar somente observabilidade:

- adicionar `.github/workflows/baken_smp_fault_diag.yml`;
- não alterar nenhum `.sotlas` funcional;
- recompilar o mesmo kernel e executar até três boots SMP;
- habilitar `QEMU -d int` para obter `CR2`/estado do #PF;
- produzir `x86_64-w64-mingw32-nm -n` do EFI;
- extrair `RIP` da serial e apontar símbolo mais próximo;
- gerar `objdump` em torno do RIP;
- subir serial/int log/symbol map/EFI como artefato.

### Regra de continuação

1. publicar o correction-only diagnóstico sobre `022bbec...`;
2. congelar `main` nesse SHA e ler primeiro o workflow diagnóstico;
3. usar `CR2 + símbolo + disassembly` para escolher a correção funcional mínima;
4. registrar qualquer novo vermelho sem apagar o anterior;
5. somente depois de um SHA corrigido fechar CI + SMP + NVMe-only + HID Dual-device 4/4, considerar I2C-2a certificado;
6. I2C-2b permanece bloqueado até essa certificação.

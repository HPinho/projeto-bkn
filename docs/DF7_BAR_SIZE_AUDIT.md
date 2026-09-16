# DF-7 BAR Size Audit — Corrective Appendix

Data: 2026-09-16 (America/Fortaleza)

Este documento e aditivo e preserva integralmente os roadmaps/handoffs existentes. Para o DF-7b, **este appendix supersede apenas qualquer frase anterior que trate `PciBarClaim.physical.length` como prova da aperture real do BAR**.

## Finding

O primeiro candidato DF-7b foi publicado em:

```text
e6bbc3bf1b3b85545a4cedca63b191dc08ce8e7c
feat(pci): bind MSI-X windows to BAR ownership
```

Durante auditoria antes da certificacao foi confirmado:

1. `pci_probe_bar()` le somente os valores atuais do BAR e inicializa `PciBar.size = 0`.
2. O scan global nao executa write-all-ones sizing, por desenho.
3. `pci_claim_bar()` aceita o `length` fornecido pelo driver quando `known_size == 0`.
4. Logo, um `RESOURCE_KIND_MMIO.length` pode provar ownership/conflito da faixa reivindicada, mas **nao prova sozinho o limite fisico da aperture**.

Conclusao: `e6bbc3bf...` nao pode ser promovido a `CERTIFIED`, mesmo se seus workflows concluirem verdes. Ele e `SUPERSEDED_BY_AUDIT`.

## Correction-only contract

O DF-7b corrigido permanece read-only e agora exige simultaneamente:

```text
inventory PciBar.size > 0
physical.start == current BAR base
physical.length == inventory PciBar.size
Table offset + Table span <= PciBar.size
PBA offset + PBA span <= PciBar.size
```

A prova usa subtraction-based bounds para evitar overflow. O BAR size e reconsultado na segunda validacao antes de publicar `PciMsixLayout`.

Se `PciBar.size == 0`, o resultado obrigatorio e `invalid`.

## Why this is deliberately fail-closed

O Baken OS ja boota em hardware real. Introduzir write-all-ones BAR sizing dentro do enumerador ou dentro de um helper MSI-X read-only poderia alterar decode/configuracao de hardware em um ponto arquitetural inadequado.

Por isso o correction-only **nao tenta obter o tamanho**. Ele somente se recusa a publicar um layout MSI-X sem uma medida de aperture previamente conhecida e confiavel.

## Required follow-up: DF-7b1

Antes de MSI-X source/vector ownership funcional em hardware com `size == 0`, criar um microcorte separado para sizing controlado de BAR com dispositivo quiescente.

Requisitos minimos:

- ownership Device/Driver generation-safe;
- estado/lifecycle apropriado e nenhuma operacao concorrente;
- Bus Master/DMA comprovadamente inativos;
- snapshot de PCI Command e BAR low/high;
- decode tratado explicitamente;
- write-all-ones/read-mask apenas na janela controlada;
- BAR 64-bit medido/restaurado como par;
- restauracao exata + readback antes de publicar size;
- falha de restauracao = fail-closed e sem publicacao;
- nenhum MSI-X Table/PBA access/programming no mesmo corte;
- seis gates obrigatorios no mesmo SHA.

## Certification rule

Baseline funcional permanece:

```text
a34434aad5c1a795cdac70458efe26adb8b3a50a
DF-7a CERTIFIED
```

O SHA correction-only do DF-7b so substitui essa baseline depois de:

```text
CI/CD + QEMU          PASS
SMP Bring-up          PASS
NVMe-only             PASS
HID Dual-device       PASS
SMP Fault Diagnostic  PASS
MSI EDU Runtime       PASS
```

no mesmo commit.

# Baken OS — Roadmap Appendix (autoritativo, append-only)

Este arquivo complementa `docs/BAKEN_OS_ROADMAP.md` sem reescrever o histórico já existente. A partir de 2026-09-13, cada microcorte da trilha HID deve acrescentar uma entrada aqui com o resultado real dos gates, inclusive falhas, antes de avançar para o corte seguinte.

## Política de gates e correções

Um candidato da trilha HID só vira baseline certificada quando **CI principal + SMP + NVMe-only + HID Dual-device** terminam verdes no mesmo SHA.

- candidato com qualquer gate aberto: `⏳ EM VALIDAÇÃO`;
- candidato com qualquer gate vermelho: `❌ REPROVADO`, preservando SHA, workflow/step e causa conhecida;
- correção posterior deve citar explicitamente o SHA reprovado e o defeito corrigido;
- não apagar entradas reprovadas: elas fazem parte do histórico de engenharia;
- não empilhar outro microcorte funcional enquanto o candidato atual não fechar 4/4;
- documentação acompanha cada microcorte; mudanças de LangSotlas só entram quando sintaxe/semântica/lowering realmente exigirem.

---

## 2026-09-13 — baseline HID Report DMA prepare hardening

**✅ CERTIFICADO 4/4**

```text
e39db2528de7bf2d7381befc696680f6d62205bd
fix(xhci): harden HID report DMA prepare publication
```

Provas no mesmo SHA:

- CI #1206 ✅
- SMP #309 ✅
- NVMe #406 ✅
- HID Dual-device #65 ✅

Escopo certificado:

- rollback de candidato HID Report DMA somente enquanto ainda CPU-owned e não publicado;
- falhas de zero/share não descartam owner potencialmente entregue ao device;
- owner antigo/quarentenado impede overwrite por epoch novo;
- `ready=true` é a publicação final do registro per-slot;
- nenhuma mudança de sintaxe, semântica ou lowering em LangSotlas foi necessária.

---

## 2026-09-13 — recovery de enumeração FAILED / Address Device lógico

**⏳ CANDIDATO DESTE MICROCORTE — gates ainda não certificados nesta entrada.**

Objetivo deliberadamente pequeno:

```text
FAILED + slot_id + epoch exatos
→ Disable Slot já confirmado
→ Configuration Descriptor recovery tentado
→ Device Descriptor recovery tentado
→ limpar somente o estado lógico Address Device do mesmo epoch
→ manter EP0, Evaluate Context, SET_CONFIGURATION, Configure Endpoint,
  HID Report DMA, Transfer Ring, Device/Input Context e Slot ID em quarentena
```

Invariantes do corte:

- o helper de `DETACH_PENDING` existente permanece separado e inalterado;
- estado de outro epoch nunca é sobrescrito;
- se Address Device nunca chegou a publicar estado e o slot local já está vazio, cleanup é idempotente;
- estado vivo/stale de outro epoch falha fechado;
- nenhum `dma_release`, `dma_unshare_from_device`, context release ou Slot ID release é introduzido;
- guardrail novo deve provar a ordem `Disable Slot completion → descriptor recovery → Address cleanup`.

### Próximos microcortes, condicionados ao resultado dos gates

1. Se este candidato falhar: registrar SHA + gate/step vermelho + causa e corrigir **somente a regressão** no próximo candidato.
2. Se fechar 4/4: adicionar cleanup lógico `EP0` exact-epoch em `FAILED`.
3. Depois: `Evaluate Context` lógico exact-epoch.
4. Depois: `SET_CONFIGURATION` lógico exact-epoch.
5. Depois: `Configure Endpoint` lógico exact-epoch, sem fingir que Drop Endpoint físico ocorreu.
6. Depois dos estados lógicos: HID Report Descriptor DMA físico, HID Transfer Ring, arena Device/Input Context e, por último, release de Device Table / Slot ID / porta após barrier apropriado.

A porta continua deliberadamente bloqueada enquanto qualquer owner físico ou estado obrigatório de cleanup permanecer em `FAILED`.

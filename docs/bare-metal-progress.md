# Baken OS — Bare-Metal Foundation Progress

Este documento acompanha o progresso da migração para um kernel x86-64 realmente bare-metal.

Critério de status:

- ✅ **validado**: implementado e já observado no caminho pós-`ExitBootServices`/QEMU.
- ⚙️ **implementado, validação parcial**: código real existe, mas o gate de hardware ainda não foi completamente provado.
- 🧱 **fundação pronta**: estruturas necessárias existem, porém a integração ativa ainda está bloqueada por uma etapa anterior.
- ⬜ **pendente**: trabalho principal ainda não iniciado.

> Percentuais são estimativas de engenharia, não contagem de linhas. Uma etapa pode ter bastante código pronto e ainda exigir validação de hardware.

| Etapa | Status | Implementação | Validação runtime | Evidência / observação |
|---|---|---:|---:|---|
| `cutover_prepare` | ✅ | 100% | 100% | Contrato de handoff/cutover canônico |
| W^X page tables | ✅ | 100% | 100% | Política de mappings de transição implementada |
| guarded stack | ✅ | 100% | 100% | Stack própria de transição preparada |
| CR3 mechanism | ✅ | 100% | 100% | Mecanismo de ativação da raiz x86-64 implementado |
| stack trampoline | ✅ | 100% | 100% | Trampoline/stack switch implementado |
| post-cutover Sotlas entry | ✅ | 100% | 100% | Entrada pós-EBS executada no QEMU |
| `ExitBootServices` real | ✅ | 100% | 100% | Boot chega à entrada bare-metal sem Boot Services |
| stack switch | ✅ | 100% | 100% | Caminho pós-cutover utiliza stack própria |
| CR3 | ✅ | 100% | 100% | `BAKEN:STEP=0/1` observado |
| GDT + segment reload | ✅ | 100% | 100% | `BAKEN:STEP=2/3` observado |
| LTR | ✅ | 100% | 100% | TSS/LTR executados antes da continuação |
| LIDT | ✅ | 100% | 100% | IDT própria ativada |
| PMM ativo | ✅ | 100% | 100% | `BAKEN:STEP=P` observado após ativação do allocator/bitmap |
| VMM ativo | ✅ | 100% | 100% | `BAKEN:STEP=V` observado com direct-map ativo |
| ACPI pós-CR3 | ✅ | 100% | 100% | `BAKEN:STEP=A` observado |
| LAPIC / IOAPIC | ✅/⚙️ | 95% | 90% | Inicialização mascarada real observada em `BAKEN:STEP=I`; cobertura total de rotas ainda não concluída |
| IRQs / timer | ⚙️ | 85% | 80% | `BAKEN:TIMER_READY`, `STEP=T` e `STEP=K` observados; LAPIC timer e IRQ1 estão vivos; IRQ12/MSI/MSI-X ainda pendentes |
| DMA real | ⚙️ | 75% | 45% | PMM-backed DMA, ownership/shared state, DCBAA/rings/ERST/context arenas implementados; primeiro DMA de dispositivo ainda depende do xHCI ultrapassar `STEP=X` |
| xHCI → USB HID | ⚙️ | 61% | 22% | QEMU já validou discovery PCI, BAR/MMIO, PCI Memory Space e capability/version até `STEP=8`. Legacy handoff foi corrigido com fallback forçado; rings, port reset, Enable Slot, contexts, Address Device, Transfer TRBs e produtor EP0 stateful estão implementados. GET_DESCRIPTOR, Event consumer compartilhado, Configure Endpoint e HID ainda pendentes |
| NVMe / AHCI | ⬜ | 10% | 0% | Apenas fundações compartilháveis de PCI/DMA existem; driver real ainda não implementado |
| PAT / WC final | ⚙️ | 40% | 20% | PAT e mappings UC existem; política final WC/framebuffer e validação completa ainda pendentes |
| **Fundação bare-metal geral** | ⚙️ | **~74%** | **~61%** | Base CPU/memória/ACPI/IRQ roda pós-EBS e o xHCI já chega a capability validation. O gate imediato é provar `STEP=9/q/w/X`, depois DMA ativo/USB HID, storage e PAT/WC final |

## Estado xHCI atual

Último smoke QEMU confirmado:

```text
BAKEN:STEP=B
BAKEN:STEP=0
BAKEN:STEP=1
BAKEN:STEP=2
BAKEN:STEP=3
BAKEN:STEP=C
BAKEN:STEP=P
BAKEN:STEP=V
BAKEN:STEP=A
BAKEN:STEP=I
BAKEN:STEP=R
BAKEN:TIMER_READY
BAKEN:STEP=T
BAKEN:STEP=K
BAKEN:STEP=4
BAKEN:STEP=5
BAKEN:STEP=6
BAKEN:STEP=7
BAKEN:STEP=8
```

Isso prova em runtime:

```text
STEP=4  active page tables prontas                 ✅
STEP=5  xHCI PCI candidate encontrado              ✅
STEP=6  BAR/MMIO válido                            ✅
STEP=7  PCI Memory Space habilitado                ✅
STEP=8  capability/version válidos                 ✅
STEP=9  legacy ownership concluído                 ⚙️ correção em validação
STEP=q  page size 4 KiB suportado                  ⬜ aguardando gate anterior
STEP=w  halt/HCRST/CNR concluídos                  ⬜ aguardando gate anterior
STEP=X  controller pronto                          ⬜ aguardando gate anterior
STEP=D  DCBAA/CRCR/ERST/ERDP programados           ⬜ aguardando gate anterior
STEP=N  No-op Command Completion real              ⬜ aguardando gate anterior
```

A falha do smoke anterior foi localizada exatamente entre `STEP=8` e `STEP=9`. O handoff agora segue uma política robusta: solicita OS Owned, espera BIOS Owned limpar e, se firmware/emulação não liberar o semáforo, desabilita USB Legacy SMIs e assume ownership após timeout em vez de abortar todo o bring-up.

Depois de `STEP=N`, a sequência preparada/planejada é:

```text
Supported Protocol
→ port inventory/reset
→ Enable Slot
→ Device/Input Context + EP0 ring
→ Address Device
→ Setup/Data/Status Transfer TRBs
→ produtor EP0 stateful + doorbell
→ Event Ring consumer compartilhado
→ GET_DESCRIPTOR
→ Configure Endpoint
→ HID keyboard/mouse
```

## Regra de progresso

Uma etapa só muda para ✅ quando o comportamento correspondente tiver sido observado no caminho pós-`ExitBootServices`, preferencialmente pelo smoke QEMU e depois também em hardware físico. Código compilando sozinho não conta como validação de hardware.

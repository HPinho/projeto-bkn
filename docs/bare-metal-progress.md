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
| DMA real | ⚙️ | 86% | 80% | PMM-backed DMA, ownership/shared state, DCBAA, Command Ring, Event Ring, ERST e programação real do xHC foram observados até `STEP=D/N`; ainda faltam DMA de transferências USB/HID e storage |
| xHCI controller | ✅/⚙️ | 95% | 90% | QEMU observou `STEP=8/g/r/s/p/h/j/9/q/w/X/D/N`, incluindo reset, runtime DMA, Bus Master, Run/Stop, Doorbell 0 e Command Completion Event real |
| xHCI → USB HID | ⚙️ | 88% | 35% | Controller está provado até `STEP=N`; CI agora anexa `usb-kbd` real ao `qemu-xhci`. Port/slot/address/descriptors/configuração/HID já têm fundações; Evaluate Context de EP0 foi adicionado para o fluxo correto de MPS0. Falta ativação incremental e prova runtime |
| NVMe / AHCI | ⬜ | 10% | 0% | Apenas fundações compartilháveis de PCI/DMA existem; driver real ainda não implementado |
| PAT / WC final | ⚙️ | 40% | 20% | PAT e mappings UC existem; política final WC/framebuffer e validação completa ainda pendentes |
| **Fundação bare-metal geral** | ⚙️ | **~82%** | **~69%** | CPU/memória/ACPI/IRQ e xHCI Command/DMA rodam pós-EBS. O gate imediato mudou de bring-up do controller para enumeração de um dispositivo USB real |

## Estado xHCI atual

Smoke QEMU confirmado no CI #590:

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
BAKEN:STEP=g
BAKEN:HEX=1:08001040
BAKEN:HEX=2:0000000F
BAKEN:HEX=C:00087001
BAKEN:STEP=r
BAKEN:STEP=s
BAKEN:STEP=p
BAKEN:STEP=h
BAKEN:STEP=j
BAKEN:STEP=9
BAKEN:STEP=q
BAKEN:STEP=w
BAKEN:STEP=X
BAKEN:STEP=D
BAKEN:STEP=N
```

Isso prova em runtime:

```text
STEP=4  active page tables prontas                 ✅
STEP=5  xHCI PCI candidate encontrado              ✅
STEP=6  BAR/MMIO válido                            ✅
STEP=7  PCI Memory Space habilitado                ✅
STEP=8  capability/version válidos                 ✅
STEP=g  operational MMIO mapeado                   ✅
STEP=r  capability parameters lidos                ✅
STEP=s  MaxSlots válido                            ✅
STEP=p  MaxPorts válido                            ✅
STEP=h  HCSPARAMS estruturais válidos              ✅
STEP=j  entrada no Legacy handoff                  ✅
STEP=9  legacy ownership concluído                 ✅
STEP=q  page size 4 KiB suportado                  ✅
STEP=w  halt/HCRST/CNR concluídos                  ✅
STEP=X  controller pronto                          ✅
STEP=D  DCBAA/CRCR/ERST/ERDP programados           ✅
STEP=N  No-op Command Completion real              ✅
```

A correção que destravou `STEP=8 → g` tornou o mapper de page tables idempotente diante dos bits `Accessed/Dirty` modificados pela CPU, sem aceitar mudanças de endereço físico ou de política da PTE.

## Próximo gate: dispositivo USB real

O QEMU CI passa a anexar:

```text
-device qemu-xhci,id=xhci
-device usb-kbd,bus=xhci.0
```

A sequência a validar incrementalmente é:

```text
Supported Protocol
→ port inventory/reset
→ Enable Slot
→ Device/Input Context + EP0 ring
→ Address Device
→ GET_DESCRIPTOR(Device, primeiros 8 bytes)
→ obter bMaxPacketSize0
→ Evaluate Context do EP0 quando necessário
→ GET_DESCRIPTOR(Device, 18 bytes)
→ GET_DESCRIPTOR(Configuration)
→ parser Interface/HID/Endpoint
→ seleção HID Boot keyboard/mouse + Interrupt IN
→ HID Endpoint Context + Transfer Ring dedicada
→ Configure Endpoint
→ SET_CONFIGURATION
→ SET_PROTOCOL(Boot) / SET_IDLE quando aplicável
→ HID Interrupt IN Normal TRB producer
→ Doorbell Slot/DCI
→ Transfer Event compartilhado
→ parser Boot Keyboard/Mouse
```

## Regra de progresso

Uma etapa só muda para ✅ quando o comportamento correspondente tiver sido observado no caminho pós-`ExitBootServices`, preferencialmente pelo smoke QEMU e depois também em hardware físico. Código compilando sozinho não conta como validação de hardware.

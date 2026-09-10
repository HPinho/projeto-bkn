# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-10 (America/Fortaleza).

Este arquivo é o registro operacional de continuidade. Código presente não equivale a prova: um incremento só vira baseline quando CI principal + SMP 3/3 + NVMe-only passam no mesmo candidato de runtime.

## Política de baseline verde

- `main` recebe somente runtime comprovado;
- trabalho novo ocorre em branch/PR;
- falhas e correções ficam fora de `main` até os gates fecharem;
- nunca remover marker/teste ou aumentar timeout sem causa para obter verde;
- runtime QEMU vale mais que teste textual;
- toda implementação, falha, correção e certificação deve ser registrada aqui e em `docs/BAKEN_OS_ROADMAP.md`.

## Baseline de runtime certificada

```text
dbc5669aebd635b4e94c6e18e209f306cba5837f
feat(hid): isolate input maps per device
```

HID-4b está certificado e foi promovido para `main` por fast-forward, sem merge commit adicional.

- CI #1074 / `34520772415` ✅;
- SMP #177 / `34520772429` ✅ — 3/3 boots;
- NVMe-only #274 / `34520772422` ✅.

A baseline HID-4a `12c308b3` continua preservada no histórico abaixo e permanece ancestral direto da baseline atual.

## Invariantes congelados do Kernel Core

1. afinidade não transfere ownership;
2. thread dinâmica só é selecionável/reapable com owner `NONE`;
3. frame/stack só é liberado após entrada posterior do scheduler na CPU anterior;
4. FPU save -> schedule -> CR3/TSS -> FPU restore permanece sob switch lock;
5. migração Ring3 BSP->AP preserva TID, address-space root e SIMD;
6. teardown ocorre apenas após abandono físico do frame anterior;
7. `BAKEN:HEX=E:` continua terminal;
8. wait/sleep, TLB, Ring3 e SMP não podem ser relaxados para acomodar drivers.

---

# ACPI/AML

**✅ CORE CONCLUÍDO E CERTIFICADO.** AML-0..AML-8 permanecem fechados. Checkpoint final `7803447a`; os gates HID continuam reexercitando essa base.

---

# HID / input de produção

## HID-0 — Boot HID xHCI

**✅ COMPROVADO.** xHCI enumera HID Boot keyboard/mouse, configura Interrupt IN e prova report real no QEMU.

## HID-1 — Report Descriptor genérico

**✅ COMPROVADO em `1b3f94cc`.** Report Descriptor real via EP0, parser bounded/transport-agnostic e marker `BAKEN:USB_HID_DESCRIPTOR_READY`.

## HID-2 — Field map / decoder genérico

**✅ COMPROVADO em `a2e04a78`.** Field map por Report ID, Usage, offsets/flags, sign extension e validação exata de Interrupt IN. Marker `BAKEN:USB_HID_INPUT_MAP_READY`.

## HID-3 — modelo/fila unificada de input

**✅ COMPROVADO em `2775c12a`.** Runtime base `51631f23`; CI #1066 + SMP #169 3/3 + NVMe #266 verdes. O smoke exige `BAKEN:USB_HID_EVENT_MODEL_READY` e `BAKEN:USB_HID_EVENT_READY`; CI/NVMe continuam provando evento real via `sendkey a`.

## HID-4a — identidade, generation e lifecycle seguro

**✅ CERTIFICADO em `12c308b3`.**

Implementação:
- `input_device.sotlas`: registro transport-agnostic fixed-capacity de 16 devices, sem heap;
- identidade `device_id + generation`, impedindo stale handles após detach/re-attach;
- lifecycle ATTACHED/ACTIVE/FAILED/DETACHED;
- registry e fila protegidos com IRQ-save + spinlock;
- `InputEvent` carrega identidade da fonte;
- publicação revalida a identidade dentro do lock da fila;
- purge remove somente a geração desconectada;
- estado HID anterior particionado por device x Report ID;
- bind/unbind HID generation-safe;
- xHCI associa a interface real atual ao registry antes de aceitar Interrupt IN;
- marker `BAKEN:USB_HID_DEVICE_READY`; falha `BAKEN:USB_HID_DEVICE_FAILED`.

### Histórico de validação HID-4a

Primeiro candidato de validação `ebf21182b33252c7bb6270c82eb25441b1746487` falhou antes do QEMU:

- CI #1069 / `34513631621` ❌;
- SMP #172 / `34513631581` ❌;
- NVMe-only #269 / `34513631641` ❌.

Causa única: `compiler.py build` rejeitou `return false` dentro de um `if` usado como expressão em `xhci_hid_descriptor.sotlas`. Correção mínima:

```text
a4762cf614a0748336040be8d15e7f352b17f25f
fix(hid): avoid return in conditional expression
```

O runtime corrigido passou inclusive SMP #173 3/3. O head documental final `12c308b3` foi então revalidado integralmente com CI #1072 + SMP #175 3/3 + NVMe #272 verdes no mesmo SHA e promovido por fast-forward para `main`.

## HID-4b — mapa/decoder HID por device

**✅ CERTIFICADO em `dbc5669a` e integrado à `main`.**

Branch de validação original: `hid4b-validation`, baseada em `12c308b3`.

Objetivo: remover o mapa HID-2 persistente singleton do caminho runtime sem reabrir HID-1/HID-3/HID-4a.

Implementação certificada:
- novo `hid_input_device_map.sotlas`, fixed-capacity e sem heap;
- até `INPUT_DEVICE_CAPACITY` snapshots HID-2 independentes, indexados por `device_id + generation`;
- campos, Report IDs e `expected_bytes` separados por device;
- parser HID-1 permanece stateless;
- builder HID-2 legado fica somente como scratch serializado durante construção do snapshot e é invalidado imediatamente depois;
- Interrupt IN, validação, decode e tradução deixam de consultar o singleton;
- self-test mantém simultaneamente um mapa de teclado e outro de mouse e prova isolamento cruzado;
- attach xHCI ocorre antes do build do mapa para fornecer identidade real;
- bind do event model ocorre somente depois do snapshot específico estar pronto;
- teardown segue `invalidate identity -> purge events -> clear HID event state -> remove device map`;
- novo marker `BAKEN:USB_HID_DEVICE_MAP_READY` e falha `BAKEN:USB_HID_DEVICE_MAP_FAILED`;
- CI, SMP e NVMe passam a exigir/validar essa camada.

### Limite explícito do HID-4b

HID-4b **não declarou xHCI multi-device completo**. Slot, address/context, endpoint/ring e buffer de report do transporte ainda eram singletons. A separação do mapa foi o pré-requisito para migrar esses recursos no HID-4c.

### Certificação HID-4b

Head certificado/promovido:

```text
dbc5669aebd635b4e94c6e18e209f306cba5837f
feat(hid): isolate input maps per device
```

- CI #1074 / `34520772415` ✅;
- SMP #177 / `34520772429` ✅ — 3/3 boots;
- NVMe-only #274 / `34520772422` ✅.

A branch estava 1 commit à frente e 0 atrás da `main`, portanto a promoção foi feita por fast-forward no próprio SHA testado.

## HID-4c — multi-slot/multi-device xHCI

**⏳ EM DESENVOLVIMENTO/VALIDAÇÃO na branch `hid4c-validation`.**

Base da branch:

```text
dbc5669aebd635b4e94c6e18e209f306cba5837f
```

PR de validação: **#22 — `HID-4c: multi-slot xHCI transport state`**.

Objetivo global: remover singletons de transporte xHCI ainda existentes e permitir que slot/context/address/configuration/HID endpoint/ring/report buffer sejam associados ao device/interface corretos sem quebrar a baseline HID-0..HID-4b.

### HID-4c.1 — multi-slot transport core

**✅ VALIDADO NA BRANCH; NÃO PROMOVIDO ISOLADAMENTE.** Implementação inicial `bd6f1708`; head final revalidado da subfatia `22ede5d7`.

Implementação presente:
- novo `xhci_device_table.sotlas`, fixed-capacity de 256 Slot IDs e sem heap;
- registro de `slot_id`, `port_id`, `slot_type`, `state` e `epoch`;
- `epoch` impede que estado antigo seja confundido com um Slot ID reutilizado;
- lifecycle de transporte: `ENABLED`, `CONTEXT_READY`, `ADDRESSED`, `HID_READY`, `FAILED`;
- `xhci_slot_enable_port(port_id, slot_type)` executa Enable Slot para uma porta específica e registra o Slot ID retornado pelo xHC;
- segunda associação para uma porta já ocupada é rejeitada;
- `xhci_slot_enable_first_port()` continua disponível como wrapper do bring-up atual;
- `xhci_slot_id/port_id/slot_type` permanecem wrappers sobre o slot ativo, preservando contratos antigos sem reintroduzir storage singleton;
- `xhci_context` armazena arena DMA, Device Context, Input Context, EP0 ring, Context Size e EP0 Max Packet por Slot ID;
- `xhci_context_prepare_for_slot(slot_id)` prepara contexto do slot selecionado e publica `DCBAA[slot]` no índice correto;
- wrappers `xhci_context_*()` antigos resolvem o slot ativo para não quebrar EP0/descriptor existentes enquanto as próximas subfatias são migradas;
- `xhci_address_slot(slot_id)` envia Address Device usando o Input Context daquele slot;
- estado Addressed e USB Device Address são armazenados por Slot ID + epoch;
- `xhci_address_first_slot()` e getters antigos permanecem como wrappers do slot ativo;
- `kernel/src/main.sotlas` importa `xhci_device_table` no grafo canônico;
- guardrails `test_xhci_slot.py`, `test_xhci_context.py` e `test_xhci_address.py` exigem a arquitetura por-slot e impedem regressão aos antigos singletons desses estágios.

### Validação HID-4c.1

Head `22ede5d7`:
- CI #1078 / `34530989194` ✅;
- SMP #181 / `34530989212` ✅ — 3/3 boots;
- NVMe-only #278 / `34530989192` ✅.

Esses gates validam somente a primeira subfatia. HID-4c continua fora da `main` até o fechamento integral das subfatias multi-device.

### HID-4c.2 — HID Interrupt IN por slot/interface

**⏳ IMPLEMENTADO E EM REVALIDAÇÃO.**

Implementação:
- `xhci_hid_context` troca os singletons persistentes por `XHCI_HID_CONTEXTS[slot_id]` com epoch;
- cada slot mantém DCI, endpoint address, Max Packet, interval, `DmaBuffer` da Transfer Ring e ring physical próprios;
- `xhci_hid_context_prepare_for_slot(slot_id, endpoint_address, max_packet, usb_interval)` escreve o Endpoint Context no Input Context correspondente ao mesmo slot;
- o wrapper `xhci_hid_context_prepare()` usa o slot ativo e a configuração atual, preservando o bring-up certificado;
- `xhci_configure_endpoint` passa a manter READY/epoch/DCI por Slot ID;
- `xhci_configure_hid_endpoint_for_slot(slot_id)` envia Configure Endpoint com o Input Context daquele slot e verifica Endpoint State=Running no Output Device Context correspondente;
- sucesso avança o registro de transporte para `XHCI_DEVICE_STATE_HID_READY`;
- `xhci_hid_report` passa a usar `XHCI_HID_REPORT_STATES[slot_id]` com epoch;
- producer cycle, enqueue index, event marker state, report DMA buffer, last length e fallback Boot keyboard/mouse ficam separados por slot;
- helpers de ring usam `xhci_hid_context_ring_physical_for(slot_id)` e nunca o ring de outro slot;
- `xhci_hid_report_poll_slot_once(slot_id)` toca o doorbell do slot/DCI correto e espera `xhci_transfer_wait_completion(slot_id, dci, physical)`;
- antes de aceitar/publish um report, `input_device_snapshot(device_id, generation)` precisa provar `INPUT_TRANSPORT_USB` e `transport_address == slot_id`;
- wrappers legados continuam delegando ao slot ativo, portanto o smoke QEMU single-device atravessa as mesmas APIs por-slot usadas pela futura enumeração múltipla;
- guardrails de `xhci_hid_context`, `xhci_configure_endpoint`, `xhci_hid_report` e `test_hid4_runtime_contract.py` foram atualizados para impedir retorno aos singletons anteriores.

Commits centrais:
```text
e2486b2b feat(xhci): isolate HID endpoint contexts per slot
d3fcaf8e feat(xhci): configure HID endpoints per slot
0dd3ea5a feat(xhci): isolate HID report rings per slot
f51f5cb0 test(hid): advance runtime contract to HID-4c transport
```

### Histórico de validação/correção HID-4c.2

Os candidatos `f51f5cb0` e `bffcd2d6` mantiveram o runtime real saudável, mas o CI principal parou na suíte por dois guardrails desatualizados:

- `f51f5cb0`: CI #1085 / `34533310356` ❌; SMP #188 / `34533310323` ✅; NVMe-only #285 / `34533310320` ✅;
- `bffcd2d6`: CI #1087 / `34533512920` ❌; SMP #190 / `34533512907` ✅ — 3/3, build Sotlas e QEMU completos; NVMe-only #287 / `34533512927` ✅ — build/ISO/QEMU completos.

Falhas exatas do CI #1087:
1. `test_hid3_runtime_contract.py` ainda fazia split por `fn xhci_hid_report_parse(length: u32) -> bool`, removida pela migração por slot;
2. `test_xhci_hid_context.py` exigia a string de chamada `xhci_hid_context_ring_physical_for(slot_id)` dentro do módulo em vez de provar a definição/retorno do getter por slot.

Correções:
```text
b32cad41 fix(test): align HID-3 event guardrail with per-slot report state
18b6e308 fix(test): validate per-slot HID ring getter definition
```

O primeiro guardrail agora inspeciona `xhci_hid_report_parse_for_slot(slot_id, length)` e mantém a exigência semântica de que o marker real só seja publicado quando `after_events > before_events`. O segundo exige a assinatura pública do getter `_for(slot_id)` e que ele retorne `XHCI_HID_CONTEXTS[slot].ring_physical`; nenhum contrato runtime foi removido ou relaxado.

Revalidação do candidato corrigido `18b6e308`:
- CI #1089 ⏳;
- SMP #192 ⏳;
- NVMe-only #289 ⏳.

### Limite atual do HID-4c.2

A camada de slot/context/address e a camada de Endpoint Context/Interrupt IN ring/report já possuem storage por Slot ID. O bloqueio seguinte é o estado persistente de `xhci_configuration` e `xhci_hid_descriptor`, que ainda representa uma única configuração/interface ativa. Por isso o sistema ainda não declara keyboard+mouse USB simultâneos mesmo com rings separados.

### HID-4c.3 — Configuration/HID descriptor por device/interface

**⬜ PRÓXIMA SUBFATIA.**

Migrar o estado persistente de Configuration Descriptor, interface HID, endpoint, Report Descriptor transport state e bindings xHCI para o slot/interface correspondentes. HID-1 parser, HID-2/HID-4b maps e HID-3 event model continuam transport-agnostic e não devem ser reabertos.

### HID-4c.4 — enumeração simultânea real

**⬜ PLANEJADO.**

- iterar portas conectadas elegíveis em vez de somente `first_connected_port`;
- Enable Slot + context + Address Device independentes por porta/device;
- configurar múltiplos HID no mesmo xHC;
- provar keyboard + mouse simultâneos, cada um com Slot ID/context/endpoint/ring/map/generation próprios;
- garantir que evento/report de um device nunca seja aceito pelo contexto de outro;
- preservar fail-closed e bounds em todos os passos.

## Próximas fatias HID-4

- HID-4c: slot/context/address/HID rings/buffers xHCI por device/interface e enumeração de múltiplos HID simultâneos;
- HID-4d: detach físico, cancel/recovery de Interrupt IN e hot-plug/re-enumeração bounded/fail-closed.

Critério de promoção HID-4c: CI principal + SMP 3/3 + NVMe-only verdes no mesmo head final **depois do fechamento das subfatias multi-device**, não apenas das migrações intermediárias. Até isso ocorrer, `main` permanece na baseline HID-4b `dbc5669a`.

I2C-HID continua somente após transporte I2C/ACPI seguro.

`HPinho/LangSotlas` permanece somente leitura/referência salvo autorização explícita.

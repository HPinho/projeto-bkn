# Baken OS / Sotlas — Kernel & Platform Handoff

Atualizado em 2026-09-11 (America/Fortaleza).

## Estado operacional

- fase: **Fase 2 — Platform/Drivers**
- trilha: **Trilha B — HID/input de produção**
- HID-4c multi-slot xHCI: **✅ concluído e certificado**
- HID-4d hot-plug/recovery: **⏳ em desenvolvimento**
- último checkpoint certificado: **HID-4d.2b**
- candidato atual: **HID-4d.3a — lifetime de DMA temporário / preparação LIFO**
- branch: **`main`**
- Kernel Core: **congelado/invariant-preserving**

## Política de certificação

Todo incremento precisa passar no mesmo SHA:

1. Baken OS CI/CD & Automated QEMU Verification
2. Baken OS SMP Bring-up Verification
3. Baken OS NVMe-only Bare-Metal Verification
4. Baken OS HID Dual-device Verification para a trilha HID multi-device

Não empilhar funcionalidade sobre candidato vermelho. Não enfraquecer markers, proofs ou timeouts.

---

# Baseline certificada atual

```text
efde07d76bb2a27d50fe91e0e2eae208ea624459
feat(xhci): stop detached HID endpoints safely
```

Provas:

- CI #1153 / `34618305685` ✅
- SMP #256 / `34618305742` ✅
- NVMe #353 / `34618305799` ✅
- HID Dual-device #12 / `34618305732` ✅

Esse checkpoint certifica HID-4d.2b:

- `DETACH_PENDING` continua generation-safe por Slot ID + epoch
- `Stop Endpoint` usa o DCI real do endpoint HID
- Command Completion e Transfer Event coexistem no Event Ring único
- TD outstanding é drenado antes de `endpoint_stopped`
- drain aceita apenas SUCCESS ou xHCI 26/27/28
- TD cancelado nunca passa pelo parser HID
- nenhuma identidade, DMA persistente ou Slot ID é liberado ainda

---

# Candidato atual — HID-4d.3a

## Motivo do microcorte

O teardown real precisa devolver buffers DMA ao PMM. A API `dma_release()` usa `pmm_free_pages_lifo`, logo o teardown só é seguro se a ordem de alocação permanecer reversível.

A auditoria encontrou dois buffers temporários de enumeração que não ficavam armazenados em nenhum estado após o parse:

1. probe de 8 bytes do Device Descriptor (`bMaxPacketSize0`)
2. header de 9 bytes do Configuration Descriptor (`wTotalLength` + `bConfigurationValue`)

Eles ficavam abaixo das alocações persistentes mais novas e bloqueariam a liberação LIFO posterior.

## Contrato do 4d.3a

Para os dois buffers temporários, somente após o Control TD completar e os bytes serem copiados para variáveis locais:

```text
buffer DMA shared
→ parse/validate
→ dma_unshare_from_device(&mut buffer)
→ dma_buffer_cpu_owned(&buffer)
→ dma_release(&mut buffer)
→ publicar probe_ready/header_ready
```

Se descriptor/metadata forem inválidos depois da completion, o caminho tenta liberar o buffer temporário antes de falhar fechado.

## O que continua persistente

Este corte **não** libera:

- Device Descriptor completo
- Configuration Descriptor completo
- HID Report Descriptor
- HID report DMA
- HID transfer ring
- EP0 ring/device context arena
- Slot ID/device-table record

Esses recursos possuem lifetime persistente e serão desmontados explicitamente no HID-4d.3b em ordem LIFO.

## Guardrails do candidato

`tests/test_xhci_dma_lifetime.py` exige:

- uso exclusivo de `dma_unshare_from_device()` + `dma_release()`
- nenhuma chamada direta a `pmm_free_pages_lifo` nos drivers
- release do probe Device Descriptor antes de publicar `probe_ready`
- release do Configuration header antes de publicar `header_ready`
- buffers completos continuam armazenados no state e não são liberados prematuramente

---

# Sequência segura do HID-4d

1. **HID-4d.1 ✅** — detectar detach e colocar slot em quarentena.
2. **HID-4d.2a ✅** — Command Completion e Transfer Event coexistem sem perda.
3. **HID-4d.2b ✅** — Stop Endpoint + drain terminal do TD outstanding.
4. **HID-4d.3a ⏳** — remover alocações temporárias órfãs e restaurar disciplina LIFO.
5. **HID-4d.3b ⬜** — teardown persistente generation-safe de report/descriptor/map/config/rings/context.
6. **HID-4d.4 ⬜** — Disable Slot, release, reuse somente com epoch novo.
7. **HID-4d.5 ⬜** — prova runtime detach → reattach → reenumeração sem estado stale.

---

# Ordem planejada do teardown persistente 4d.3b

A ordem deverá seguir o inverso das alocações vivas no caminho de enumeração:

```text
HID report DMA
→ HID Report Descriptor DMA + InputDevice/map/event binding
→ transfer result/mailbox state
→ HID interrupt ring/context
→ Configuration Descriptor completo
→ Device Descriptor completo
→ EP0 state
→ Device/Input/EP0 context arena
```

A ordem exata será validada contra o código real antes do commit. `Disable Slot` continua proibido até 4d.4.

---

# Invariantes congelados

1. Event Ring xHCI tem um único consumidor.
2. Completion nunca é atribuída a Slot ID/endpoint/TRB diferente.
3. Slot ID reutilizado exige cleanup completo e epoch novo.
4. `DETACH_PENDING` bloqueia novos submits, mas não apaga TD já outstanding.
5. Stop Endpoint só abre o gate de teardown após Command Completion + drain terminal.
6. TD cancelado não pode gerar evento de teclado/mouse.
7. DMA temporário sem owner persistente deve ser liberado após a última referência do controller.
8. Drivers usam a API DMA; não chamam PMM free diretamente.
9. Kernel Core, SMP, scheduler, TLB, Ring3 e FPU/SIMD não podem ser relaxados para acomodar driver.
10. `BAKEN:HEX=E:` permanece terminal.
11. `sendkey a`, `DUAL_READY` e `INTERLEAVE_READY` continuam preservados.

---

# Caminho legado obrigatório do primeiro teclado

```text
post_cutover_prepare_first_usb_port
→ post_cutover_enable_first_usb_slot
→ post_cutover_prepare_first_usb_context
→ post_cutover_address_first_usb_device
→ post_cutover_probe_first_usb_descriptor
→ post_cutover_reconcile_first_usb_ep0
→ post_cutover_read_full_usb_device_descriptor
→ post_cutover_probe_first_usb_configuration_header
→ post_cutover_read_full_usb_configuration_descriptor
→ post_cutover_parse_first_usb_hid_interface
→ post_cutover_configure_first_usb_hid_endpoint
→ post_cutover_set_first_usb_configuration
→ post_cutover_prove_first_usb_hid_keyboard_report
→ storage
```

---

# Regra de continuidade

1. confirmar `main` e SHA
2. checar os quatro gates do mesmo SHA
3. ler roadmap + handoff
4. inspecionar ownership/lifetime real antes de liberar DMA
5. fazer um microcorte funcional por vez
6. se qualquer gate falhar, corrigir o próprio checkpoint antes de avançar
7. se 4d.3a ficar verde, avançar para **HID-4d.3b teardown persistente per-epoch**, ainda sem `Disable Slot`

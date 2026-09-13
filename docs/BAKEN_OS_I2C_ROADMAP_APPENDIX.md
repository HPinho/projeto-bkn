# Baken OS — Trilha B2 / I2C Foundation Roadmap Appendix

Este apêndice inicia a continuação append-only da Trilha B para I2C e I2C-HID sem reescrever o histórico USB HID/xHCI já preservado em `BAKEN_OS_ROADMAP.md` e `BAKEN_OS_ROADMAP_APPENDIX.md`.

## 2026-09-13 — transição B1 → B2

A baseline imediatamente anterior fechou **4/4**:

```text
45c1bd406d7d200c50c20af4220a83b14f929db0
fix(xhci): quiesce failed transfer state by epoch
```

- CI #1213 ✅
- SMP #316 ✅
- NVMe #413 ✅
- HID Dual-device #72 ✅

O escopo funcional USB HID/xHCI da Trilha B1 permanece concluído/certificado. O hardening físico adicional de enumeração `FAILED` que ainda existe — HID Report Descriptor DMA, HID Report DMA, HID Transfer Ring, arena Device/Input Context + EP0 Ring e finalização Device Table/Slot ID/porta — fica preservado como backlog pós-certificação; ele não é apagado nem declarado concluído por esta transição.

## Trilha B2 — I2C Foundation / I2C-HID

| Etapa | Estado | Contrato |
| --- | --- | --- |
| I2C-0a — ACPI resource semantic decode | ⏳ | `I2CSerialBus` + `GpioInt` bounded/fail-closed, sem hardware |
| I2C-0b — ACPI namespace/resource binding | ⬜ | resolver `ResourceSource`, `_HID/_CID`, `_CRS` e preparar `_DSM` |
| I2C-1 — Generic I2C Core | ⬜ | read/write/combined/repeated-start + timeout/NACK/arbitration/busy |
| I2C-2 — ACPI ↔ controller binding | ⬜ | registry generation-safe entre device, connection e controller |
| I2C-3 — GPIO/IRQ Foundation | ⬜ | pin/trigger/polaridade/routing/dispatch |
| I2C-4 — Generic I2C Device Model | ⬜ | identidade, address, speed, controller, IRQ e lifecycle |
| I2C-HID-0 — transport | ⬜ | `PNP0C50`, `_DSM`, HID Descriptor Register e validação |
| I2C-HID-1 — enumeration/lifecycle | ⬜ | reset/power/report descriptor/IRQ/recovery |
| I2C-HID-2 — HID Core integration | ⬜ | reutilizar parser/field map/decoder/InputDevice existentes |
| I2C-HID-3 — input runtime | ⬜ | reports por IRQ para dispositivos descritos pelo firmware |
| I2C-HID-4 — power/recovery | ⬜ | suspend/resume, stale IRQ/report e teardown generation-safe |
| I2C-HID-5 — runtime certification | ⬜ | fault injection + provas disponíveis em QEMU/hardware |

## I2C-0a — contrato do primeiro microcorte

O AML-5 já fornece `_HID`, `_CID`, `_CRS` e `ResourceTemplate` cru com EndTag e bounds. Portanto I2C-0a não duplica discovery: adiciona uma camada semântica sobre `AmlResourceDescriptor`.

Escopo deste candidato:

- reconhecer Large Resource `0x0E` como GenericSerialBus e aceitar somente Serial Bus Type `1` para I2C;
- validar Revision ID 2, Type Revision 1, Type Data Length, flags reservados e endereços 7/10-bit;
- expor connection speed, slave address, sharing/consumer/slave-mode, vendor data e `ResourceSource`;
- preservar o byte LVR da ACPI 6.6 para decisão futura no binding do controlador;
- reconhecer Large Resource `0x0C` somente como `GpioInt` revision 1;
- validar flags, polaridade, edge/level, PinConfig, offsets relativos ao início do descriptor, pin table, `ResourceSource` e vendor data;
- manter o módulo read-only e sem estado global mutável.

Fora de escopo deste corte: resolução do namespace de `ResourceSource`, `_DSM`, `PNP0C50`, MMIO, controlador I2C, GPIO programming, IRQ registration, DMA, HID parsing ou input runtime.

A mesma regra de certificação continua valendo: **nenhum I2C-0b começa antes de CI + SMP + NVMe-only + HID Dual-device fecharem verdes no mesmo SHA I2C-0a**. Em caso de gate vermelho, o próximo commit é correction-only e a falha deve ser preservada.

---

## 2026-09-13 — fechamento I2C-0a / semantic ACPI resources

**✅ CERTIFICADO 4/4 — nenhuma correção intermediária necessária.**

```text
acfd6a203a5a3eb6e5e5c20865384704b02055e7
feat(i2c): decode ACPI serial and GPIO resources
```

Provas no mesmo SHA:

- CI #1214 ✅
- SMP #317 ✅
- NVMe-only #414 ✅
- HID Dual-device #73 ✅

Resultado certificado:

- `I2CSerialBus` ACPI 6.6 é decodificado com revision/type revision, flags, TypeDataLength, speed, endereço 7/10-bit, LVR, vendor data e `ResourceSource` bounded;
- `GpioInt` é decodificado com offsets validados, pin table bounded, trigger/polaridade/share/wake, `ResourceSource` e vendor data;
- o módulo pertence ao grafo Sotlas nativo real;
- nenhum MMIO, PCI, DMA, PMM, IRQ, transação I2C, execução AML ou HID runtime foi introduzido;
- LangSotlas permaneceu inalterado.

---

## 2026-09-13 — I2C-0b / ACPI namespace-resource binding

**⏳ CANDIDATO DESTE MICROCORTE — certificação depende de CI + SMP + NVMe-only + HID Dual-device no mesmo SHA.**

Contrato deliberadamente read-only:

```text
AmlResourceDescriptor I2C já validado
→ resolver ResourceSource no namespace AML publicado
→ aceitar caminho absoluto, ^ relativo e namespace search rules
→ exigir controller resolvido como Device ACPI
→ preservar master/source index, address, speed e mode
→ catalogar GpioInt do mesmo device sem programá-lo
→ reconhecer _CID PNP0C50/ACPI0C50 estático
→ localizar _DSM como Method sem executá-lo
→ marcar somente hid_transport_prepared quando recursos estáticos mínimos convergem
```

Invariantes:

- resolver de `ResourceSource` é bounded por `AML_NAME_MAX_SEGMENTS` e `AML_DATA_MAX_STRING_BYTES`;
- NameSeg textual exige exatamente quatro caracteres com gramática AML válida;
- nome sem prefixo usa busca ascendente de namespace; `\\` e `^` têm resolução explícita e fail-closed;
- controller I2C/GPIO resolvido deve ser `AML_NAMESPACE_KIND_DEVICE`;
- binding genérico exige I2C `ResourceConsumer`, mas GPIO permanece apenas catalogado;
- identificação HID estática aceita `_CID` `PNP0C50`, `ACPI0C50` ou EISA integer equivalente;
- CID dinâmica fica `cid_requires_evaluator` e não é promovida como PNP0C50 estática;
- `_DSM` só é localizado como Method; nenhuma query/function é executada;
- GUID HIDI2C `{3CDFF6F7-4267-4555-AD05-B30A3D8938DE}`, revision 1, function 0 e function 1 ficam declarados para o próximo transporte;
- `hid_transport_prepared` exige PNP0C50 estático, `_DSM` Method, exatamente um `GpioInt` consumer com um pin e conexão I2C controller-initiated;
- `_HRV`, execução de `_DSM`, HID Descriptor Register, MMIO, GPIO routing, IRQ e transação I2C permanecem fora deste corte;
- nenhum `static mut`, registry ou lifecycle generation-safe é introduzido ainda;
- nenhum ajuste de lexer/parser/semântica/lowering em LangSotlas é esperado.

Se este candidato fechar 4/4, o próximo microcorte é **I2C-1 — Generic I2C Core**, começando pela interface de transação e estados de erro/timeout sem ainda assumir um controlador físico específico. Se qualquer gate falhar, `main` congela e o próximo commit é correction-only.

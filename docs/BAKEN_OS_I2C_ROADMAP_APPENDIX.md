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

---

## 2026-09-13 — fechamento I2C-0b / ACPI namespace-resource binding

**✅ CERTIFICADO 4/4 — sem correction-only intermediário.**

```text
aa3c48a35172cf30c7f7754ebbbf16a84b0044fc
feat(i2c): bind ACPI resources to namespace controllers
```

Provas no mesmo SHA:

- CI #1215 ✅
- SMP #318 ✅
- NVMe-only #415 ✅
- HID Dual-device #74 ✅

Resultado certificado:

- `ResourceSource` absoluto, relativo por `^` e relativo por namespace search é resolvido fail-closed;
- o alvo I2C/GPIO precisa existir no namespace publicado e ser `Device` ACPI;
- `_CID` estático `PNP0C50`/`ACPI0C50` e EISA equivalente são reconhecidos sem executar AML;
- CID dinâmica permanece explicitamente dependente de evaluator;
- `_DSM` é somente localizado como `Method`; nenhuma function foi executada;
- `hid_transport_prepared` continua sendo apenas prontidão estática, não enumeração HID-I2C;
- nenhum MMIO, PCI, DMA, PMM, IRQ, GPIO programming, transação I2C ou HID runtime foi introduzido;
- LangSotlas permaneceu inalterado.

---

## 2026-09-13 — I2C-1a / generic transaction contract

**⏳ CANDIDATO DESTE MICROCORTE — aguarda CI + SMP + NVMe-only + HID Dual-device no mesmo SHA.**

Primeiro recorte do Generic I2C Core:

```text
I2cTransaction
→ validação bounded/fail-closed
→ I2cTransferPlan
→ checagem de I2cControllerCapabilities
→ I2cTransferResult normalizado
```

Escopo:

- mensagens `WRITE` e `READ` bounded;
- endereço 7-bit/10-bit validado por largura neste estágio;
- `bus_speed_hz` e timeout em microssegundos explícitos;
- máximo de mensagens, bytes por mensagem e bytes totais definidos no contrato;
- uma transação multi-message é combinada: START inicial, repeated START nas fronteiras e STOP ao fim pelo backend futuro;
- leitura 10-bit iniciando a transação registra o repeated START adicional necessário à fase de endereço;
- capabilities declaram 7/10-bit, repeated-start, limites de mensagens/bytes e velocidade máxima;
- resultados normalizam `ADDRESS_NACK`, `DATA_NACK`, `ARBITRATION_LOST`, `BUS_BUSY`, `TIMEOUT`, `CONTROLLER_ERROR` e `UNSUPPORTED`;
- sucesso/erro possuem contagem de mensagens/bytes e índice da mensagem com falha quando aplicável.

Invariantes:

- contrato stateless: nenhum `static mut`;
- zero MMIO/PCI/DMA/PMM/IRQ/GPIO/xHCI;
- zero polling, sleep ou acesso a timer no core deste corte;
- zero execução AML;
- zero registry/controller binding;
- zero HID-specific behavior;
- probe address-only/zero-length fica fora deste primeiro contrato;
- política de endereços I2C reservados/general-call não é embutida ainda: I2C-1a valida largura e deixa política para device/controller layers;
- nenhum ajuste em LangSotlas é esperado.

Se I2C-1a fechar 4/4, o próximo microcorte será **I2C-1b — executor/backend interface + deadline/error propagation**, ainda desacoplado de um controlador físico específico. Qualquer gate vermelho congela `main` e exige correction-only antes de continuar.

---

## 2026-09-13 — fechamento I2C-1a / generic transaction contract

**✅ CERTIFICADO 4/4 — sem correction-only intermediário.**

```text
3bff745182da4324c03b146a9b48c578e44440e9
feat(i2c): add generic transaction contract
```

Provas no mesmo SHA:

- CI #1216 ✅
- SMP #319 ✅
- NVMe-only #416 ✅
- HID Dual-device #75 ✅

Resultado certificado:

- `I2cMessage`, `I2cTransaction`, `I2cTransferPlan`, `I2cControllerCapabilities` e `I2cTransferResult` pertencem ao grafo Sotlas nativo;
- write/read combinado, repeated START, leitura 10-bit, bounds de mensagens/bytes, capabilities e resultados normalizados compilam no lowering real;
- suíte completa, grafo modular, builds nativos, ISO e provas QEMU dos quatro gates permaneceram verdes;
- nenhum backend físico, MMIO, PCI, DMA, IRQ, GPIO, AML evaluation ou HID-I2C runtime foi introduzido;
- LangSotlas permaneceu inalterado.

---

## 2026-09-13 — I2C-1b / executor + backend boundary

**⏳ CANDIDATO DESTE MICROCORTE — certificação depende dos mesmos quatro gates no mesmo SHA.**

Contrato:

```text
I2cTransaction + I2cControllerCapabilities
→ i2c_executor_prepare
→ I2cBackendRequest borrowed/bounded
→ backend físico futuro
→ I2cBackendCompletion
→ i2c_executor_finish
→ I2cExecutionOutcome + I2cTransferResult
```

Escopo:

- `I2cBackendRequest` preserva o borrow da transação e o plano certificado; o backend futuro nunca recebe ownership do buffer;
- preflight inválido falha fechado; capability insuficiente retorna `UNSUPPORTED` sem executar backend;
- `I2cBackendCompletion` carrega status, progresso, mensagem da falha, tempo decorrido e prova de liberação do barramento/quiescência;
- completion é bounded pelo `I2cTransferPlan` que originou o request;
- deadline excedido promove o resultado para `TIMEOUT`;
- sucesso declarado enquanto o backend ainda controla o barramento ou não está quiescente é promovido para `CONTROLLER_ERROR`;
- `recovery_required` permanece separado de `deadline_exceeded`, permitindo ao backend físico futuro decidir recuperação sem esconder a causa lógica;
- a fronteira é data-oriented; não depende de function pointers/callbacks cuja cadeia parser→lowering→codegen ainda não foi usada como contrato do kernel.

Invariantes:

- zero `static mut`;
- zero MMIO/PCI/DMA/PMM/IRQ/GPIO/xHCI;
- zero timer read, sleep ou polling no executor;
- zero execução AML/HID;
- nenhum registry ou controller físico;
- nenhum retry implícito: um backend futuro não poderá duplicar writes não idempotentes silenciosamente;
- LangSotlas não deve ser alterado para este corte.

Se este SHA fechar 4/4, o próximo microcorte será **I2C-1c — controller/backend protocol state machine + recuperação lógica**, ainda separando a máquina de estados genérica do primeiro backend físico específico. Se qualquer gate falhar, `main` congela e a próxima mudança será correction-only.

---

## 2026-09-13 — fechamento I2C-1b / executor + backend boundary

**✅ CERTIFICADO 4/4 — sem correction-only intermediário.**

```text
71a1ed495d02520ad8430bc13366707b9efda885
feat(i2c): add executor backend boundary
```

Provas no mesmo SHA:

- CI #1217 ✅
- SMP #320 ✅
- NVMe-only #417 ✅
- HID Dual-device #76 ✅

Resultado certificado:

- `I2cBackendRequest`, `I2cBackendCompletion` e `I2cExecutionOutcome` compilam no grafo Sotlas nativo;
- preflight reutiliza planner/capabilities do I2C-1a e retorna `UNSUPPORTED` sem tocar backend quando necessário;
- completion é bounded pelo plano e deadline/recovery permanecem semanticamente separados;
- sucesso com barramento não liberado ou controller não quiescente é convertido para `CONTROLLER_ERROR`;
- suíte completa, grafo modular, build nativo, ISO e provas QEMU permaneceram verdes;
- nenhum backend físico, callback obrigatório, MMIO, PCI, DMA, IRQ, GPIO ou mudança em LangSotlas foi introduzido.

---

## 2026-09-13 — I2C-1c / protocol state machine + logical recovery

**⏳ CANDIDATO DESTE MICROCORTE — certificação depende de CI + SMP + NVMe-only + HID Dual-device no mesmo SHA.**

Contrato:

```text
I2cBackendRequest certificado
→ I2cProtocolMachine
→ START → ADDRESS → DATA
→ REPEATED_START → ADDRESS → DATA ...
→ STOP
→ I2cBackendCompletion

qualquer erro
→ preservar primeira causa
→ RECOVER no máximo uma vez se necessário
→ FAILED sem retry implícito
```

Escopo:

- ações abstratas `START`, `ADDRESS`, `WRITE_BYTE`, `READ_BYTE`, `REPEATED_START`, `STOP` e `RECOVER`;
- a máquina só emite uma nova ação depois de receber evento para a ação anterior (`awaiting_event`);
- progresso é bounded por `message_count`, comprimento da mensagem e `total_bytes` do plano certificado;
- `ADDRESS_NACK` só é aceito em `ADDRESS`; `DATA_NACK` só é aceito em `WRITE_BYTE`;
- READ solicita ACK após cada byte exceto o último byte de cada mensagem;
- fronteiras entre mensagens emitem repeated START sem STOP intermediário;
- o restart interno necessário ao address phase de uma primeira leitura 10-bit é sinalizado por `address_phase_restart` na ação `ADDRESS` e permanece responsabilidade do backend físico futuro;
- falhas preservam `completed_messages`, `transferred_bytes` e mensagem da primeira falha;
- nenhuma falha reinicia `message_index`/`byte_index`, portanto não há replay silencioso de writes;
- recovery lógico é emitido no máximo uma vez quando bus ownership/controller quiescence não foram restabelecidos;
- falha do recovery não sobrescreve a causa original e fica indicada separadamente por `recovery_failed`;
- `i2c_protocol_completion` adapta estado terminal para `I2cBackendCompletion`, recebendo `elapsed_us` de fora sem ler clock/timer.

Invariantes:

- zero `static mut`;
- zero MMIO/PCI/DMA/PMM/IRQ/GPIO/xHCI;
- zero timer read, sleep, busy-wait ou polling;
- zero execução AML/HID;
- zero retry automático;
- zero suposição sobre registradores Intel/AMD/DesignWare;
- buffers continuam borrowed pelo `I2cBackendRequest`; a state machine não assume ownership;
- LangSotlas não deve ser alterado para este corte.

Se este SHA fechar 4/4, o próximo microcorte será **I2C-1d — controller instance/backend contract + auditoria do controlador físico alvo**. Nenhum backend de silício será inventado antes de haver evidência concreta no PCI/ACPI ou no hardware alvo. Se qualquer gate falhar, `main` congela e a próxima mudança será correction-only.

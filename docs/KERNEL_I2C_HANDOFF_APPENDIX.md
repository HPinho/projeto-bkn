# Baken OS — Trilha B2 / I2C Kernel Handoff Appendix

Continuação operacional append-only para a fundação I2C. O histórico USB HID/xHCI permanece preservado nos handoffs anteriores; este arquivo começa na transição para a Trilha B2.

## Estado de retomada — 2026-09-13

Branch operacional: **`main`**.

Baseline anterior certificada:

```text
45c1bd406d7d200c50c20af4220a83b14f929db0
fix(xhci): quiesce failed transfer state by epoch
```

Gates no mesmo SHA:

- CI #1213 ✅
- SMP #316 ✅
- NVMe #413 ✅
- HID Dual-device #72 ✅

A baseline encerra o microcorte lógico Transfer do hardening `FAILED`. O escopo funcional USB HID/xHCI continua certificado; os owners físicos `FAILED` ainda pendentes ficam registrados como backlog pós-certificação e não são removidos deste histórico.

## Candidato atual — I2C-0a / semantic ACPI resources

Estado: **⏳ aguarda certificação 4/4 no novo SHA**.

Arquivos funcionais planejados neste corte:

- `kernel/src/acpi/aml_i2c_resources.sotlas`
  - consome somente `AmlResourceDescriptor` já catalogado pelo AML-5;
  - decodifica `I2CSerialBus` (`Large Item 0x0E`, SerialBus Type 1);
  - decodifica `GpioInt` (`Large Item 0x0C`, Connection Type 0);
  - valida revision/type revision, reserved bits, TypeDataLength, endereço 7/10-bit e NUL terminal exato de `ResourceSource`;
  - converte offsets GPIO relativos ao início do descriptor para offsets dentro do payload somente depois de validar bounds/ordem;
  - expõe pin table bounded e accessor que retorna `0xFFFF` fora do range;
  - preserva vendor data e LVR sem interpretar controller físico.
- `kernel/src/main.sotlas`
  - importa o novo módulo para que ele pertença ao grafo nativo real, sem código órfão.
- `tests/test_acpi_i2c_resources.py`
  - guardrails da estrutura ACPI 6.6, bounds, flags reservados e ausência de side effects de hardware/HID.

### Invariantes I2C-0a

- zero execução de Method AML;
- zero `_DSM` neste corte;
- zero MMIO/PCI/DMA/PMM;
- zero programação de GPIO/IRQ;
- zero transação I2C;
- zero parser/input HID novo;
- nenhum `static mut` no decoder semântico;
- `ResourceSource` continua textual e não resolvido no namespace até I2C-0b/I2C-2;
- nenhum ajuste em `HPinho/LangSotlas` é esperado.

## Próxima sequência somente após 4/4

1. I2C-0b — resolver `ResourceSource` para namespace/controller e preparar descoberta `_DSM`/`PNP0C50` sem tocar hardware;
2. I2C-1 — generic transaction core;
3. I2C-2 — binding generation-safe device/controller;
4. I2C-3 — GPIO/IRQ foundation;
5. I2C-4 — generic device model;
6. I2C-HID-0..5 — transporte, lifecycle, integração ao HID Core, runtime/power e certificação.

Se qualquer gate deste candidato falhar, congelar `main` no SHA reprovado, registrar workflow/step/causa e aplicar **somente correction-only** antes de continuar.

---

# Atualização operacional — 2026-09-13 / I2C-0a certificado

O primeiro microcorte da Trilha B2 fechou **4/4**:

```text
acfd6a203a5a3eb6e5e5c20865384704b02055e7
feat(i2c): decode ACPI serial and GPIO resources
```

Status final:

- CI #1214 ✅;
- SMP #317 ✅;
- NVMe-only #414 ✅;
- HID Dual-device #73 ✅.

Portanto `acfd6a20...` é a baseline certificada para a decodificação semântica `I2CSerialBus`/`GpioInt`. Não houve gate vermelho nem correction-only intermediário. LangSotlas permaneceu inalterado.

# Novo candidato — I2C-0b / ResourceSource + ACPI HID-I2C preparation

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Arquivos funcionais deste microcorte:

- `kernel/src/acpi/aml_i2c_binding.sotlas`
  - resolve `ResourceSource` textual usando o namespace AML já publicado;
  - aceita caminho absoluto `\\`, prefixos `^` e busca ascendente para nomes relativos sem prefixo;
  - limita o parser a `AML_NAME_MAX_SEGMENTS`/`AML_DATA_MAX_STRING_BYTES` e exige NameSeg de quatro caracteres;
  - exige que o alvo resolvido seja um `Device` ACPI;
  - cria binding read-only para um recurso I2C específico e seu device owner;
  - preserva controller namespace, master/source index, slave address, speed, 7/10-bit e slave mode;
  - cataloga `GpioInt` do mesmo device e resolve seu GPIO controller quando possível;
  - reconhece `_CID` estático `PNP0C50`, `ACPI0C50` e EISA integer equivalente;
  - localiza `_DSM` apenas se for `Method`;
  - declara o GUID HIDI2C `3CDFF6F7-4267-4555-AD05-B30A3D8938DE`, revision 1 e function indexes 0/1;
  - expõe `hid_transport_prepared` apenas quando PNP0C50 + `_DSM` + I2C controller-initiated + um `GpioInt` consumer de um pin estão presentes estaticamente.
- `kernel/src/main.sotlas`
  - importa `aml_i2c_binding` imediatamente após `aml_i2c_resources`, mantendo o módulo no grafo nativo.
- `tests/test_acpi_i2c_binding.py`
  - prova as três formas de `ResourceSource`;
  - prova target `Device`, bounds e escopo do recurso owner;
  - prova PNP0C50 string/EISA e CID dinâmica fail-closed;
  - prova `_DSM` lookup sem execução;
  - prova requisitos estritos de `hid_transport_prepared`;
  - proíbe MMIO/PCI/DMA/PMM/IRQ/xHCI/HID runtime/execução AML e estado global mutável.

## Fronteira deliberada deste SHA

Este corte **não** implementa:

- `_HRV`;
- chamada `_DSM` function 0;
- chamada `_DSM` function 1;
- leitura do HID Descriptor Register;
- transaction engine I2C;
- controller MMIO;
- GPIO programming ou IRQ routing;
- registry/lifecycle generation-safe;
- parser HID novo ou input runtime.

O objeto `hid_transport_prepared` significa apenas que o firmware estático possui os elementos suficientes para o próximo estágio de transporte; não significa que um dispositivo HID-I2C foi enumerado ou validado.

## Regra de continuação

A `main` deve ficar congelada no SHA I2C-0b até CI principal + SMP + NVMe-only + HID Dual-device fecharem verdes. Se houver qualquer gate vermelho, registrar SHA/run/step/causa e fazer somente correction-only. Com 4/4 verde, iniciar **I2C-1 Generic I2C Core** com interface de transação, repeated-start e modelo de timeout/NACK/arbitration/busy ainda desacoplado de hardware específico.

---

# Atualização operacional — 2026-09-13 / I2C-0b certificado

O binding ACPI I2C/HID-I2C preparation fechou **4/4** no mesmo SHA:

```text
aa3c48a35172cf30c7f7754ebbbf16a84b0044fc
feat(i2c): bind ACPI resources to namespace controllers
```

Status final:

- CI #1215 ✅;
- SMP #318 ✅;
- NVMe-only #415 ✅;
- HID Dual-device #74 ✅.

Não houve gate vermelho, correction-only ou mudança em LangSotlas. Essa passa a ser a baseline certificada para iniciar I2C-1.

# Novo candidato — I2C-1a / generic transaction contract

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Arquivos funcionais deste microcorte:

- `kernel/src/drivers/i2c_core.sotlas`
  - define `I2cMessage`, `I2cTransaction`, `I2cTransferPlan`, `I2cControllerCapabilities` e `I2cTransferResult`;
  - aceita sequências bounded de `WRITE`/`READ` com endereço 7/10-bit, velocidade e timeout explícitos;
  - rejeita ponteiro nulo, mensagem zero-length, direção desconhecida, overflow de bytes e contagens fora do contrato;
  - transforma multi-message em transação combinada com repeated START nas fronteiras;
  - registra o restart adicional da address phase para leitura 10-bit iniciando a transação;
  - normaliza `ADDRESS_NACK`, `DATA_NACK`, `ARBITRATION_LOST`, `BUS_BUSY`, `TIMEOUT`, `CONTROLLER_ERROR` e `UNSUPPORTED`;
  - checa se um plano cabe nas capabilities do controller sem executar hardware;
  - valida resultados de sucesso/erro contra o plano.
- `kernel/src/main.sotlas`
  - importa `kernel::drivers::i2c_core::*;` para incluir o contrato no grafo nativo real.
- `tests/test_i2c_core.py`
  - guardrails de bounds, repeated-start, 10-bit read, capabilities e resultados;
  - proíbe estado global mutável e APIs concretas de MMIO/PCI/DMA/PMM/IRQ/GPIO/xHCI/AML execution.

## Fronteira deliberada deste SHA

I2C-1a **não executa** transações. Não há:

- controller discovery/registry;
- backend callback/dispatch;
- MMIO/PCI/DMA;
- GPIO/IRQ;
- timer, wait ou polling;
- recovery físico do barramento;
- AML evaluation;
- HID-I2C descriptor/report access.

Política de endereços reservados/general-call também fica fora deste recorte; o core valida a largura 7/10-bit e permite que camadas de device/controller imponham política específica.

## Próximo microcorte após 4/4

**I2C-1b — executor/backend interface + deadline/error propagation**:

- interface de backend explicitamente bounded;
- ownership de buffers e duração da chamada definidos;
- propagação de deadline/timeout sem busy-loop no core;
- status normalizado do backend para `I2cTransferResult`;
- nenhuma suposição de DesignWare/Intel/AMD até a interface genérica estar certificada.

Se qualquer gate do I2C-1a falhar, `main` deve congelar no SHA reprovado e o próximo commit será exclusivamente correction-only.

---

# Atualização operacional — 2026-09-13 / I2C-1a certificado

O contrato genérico de transação fechou **4/4** no mesmo SHA:

```text
3bff745182da4324c03b146a9b48c578e44440e9
feat(i2c): add generic transaction contract
```

Status final:

- CI #1216 ✅;
- SMP #319 ✅;
- NVMe-only #416 ✅;
- HID Dual-device #75 ✅.

A suíte completa, o grafo modular, o build nativo Sotlas, a ISO e as provas QEMU permaneceram verdes. Não houve correction-only nem alteração em LangSotlas.

# Novo candidato — I2C-1b / executor + backend boundary

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Arquivos funcionais deste microcorte:

- `kernel/src/drivers/i2c_executor.sotlas`
  - importa somente `i2c_core`;
  - define `I2cBackendRequest`, `I2cBackendCompletion` e `I2cExecutionOutcome`;
  - prepara request apenas depois de planner + capability gate certificados;
  - mantém `transaction` como borrow durante a execução, sem transferência de ownership;
  - retorna `UNSUPPORTED` imediatamente quando o plano é válido mas o controller não suporta suas capacidades;
  - valida completion contra message_count/total_bytes/failed_message_index do plano;
  - converte deadline excedido em `TIMEOUT`;
  - marca `recovery_required` quando o barramento não foi liberado ou o controller não ficou quiescente;
  - não aceita sucesso terminal com ownership de barramento ainda ativo: converte para `CONTROLLER_ERROR`;
  - reaproveita `i2c_result_success`, `i2c_result_error` e `i2c_result_consistent` do I2C-1a.
- `kernel/src/main.sotlas`
  - importa `i2c_executor` logo após `i2c_core`.
- `tests/test_i2c_executor.py`
  - prova a fronteira data-oriented, borrow, preflight, bounds de completion, deadline/recovery e retorno imediato `UNSUPPORTED`;
  - proíbe `static mut`, MMIO/PCI/DMA/PMM/IRQ/GPIO/xHCI, timer/sleep/polling e AML execution.

## Decisão de arquitetura

A especificação da LangSotlas contém `FunctionType`, mas não usamos function pointers/callbacks como dependência deste corte porque essa cadeia ainda não foi necessária como contrato do kernel. O I2C-1b usa request/completion data-oriented e evita introduzir mudança de linguagem sem necessidade real.

## Fronteira deliberada

I2C-1b ainda **não** contém:

- dispatch para um controller real;
- state machine de protocolo físico;
- leitura/escrita de registradores;
- timer source ou busy-wait;
- IRQ/DMA;
- registry generation-safe;
- reset/recovery físico do barramento;
- HID-I2C.

Se este candidato fechar 4/4, o próximo microcorte será **I2C-1c — controller/backend protocol state machine + recuperação lógica**, ainda sem escolher prematuramente Intel/AMD/DesignWare. Qualquer gate vermelho congela `main` e exige correction-only.

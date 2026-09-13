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

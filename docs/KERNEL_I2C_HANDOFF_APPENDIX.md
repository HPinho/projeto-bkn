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

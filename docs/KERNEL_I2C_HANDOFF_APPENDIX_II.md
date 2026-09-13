# Baken OS — Trilha B2 / I2C Kernel Handoff Appendix II

Continuação operacional **append-only** de `KERNEL_I2C_HANDOFF_APPENDIX.md`. O arquivo anterior permanece intocado; este arquivo passa a ser o handoff ativo a partir do fechamento do I2C-1c.

## Baseline certificada — 2026-09-13 / I2C-1c

```text
09f02d1daef40ef2b9b5e24d3445ae671c34e1b9
feat(i2c): add protocol state machine
```

Gates no mesmo SHA:

- CI #1218 ✅
- SMP #321 ✅
- NVMe-only #418 ✅
- HID Dual-device #77 ✅

Essa baseline certifica o Generic I2C Core até a máquina de estados abstrata de protocolo/recovery lógico. Não houve correction-only nem alteração em LangSotlas.

## Candidato atual — I2C-1d / controller identity + ACPI binding contract

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Arquivos funcionais deste microcorte:

- `kernel/src/drivers/i2c_controller.sotlas`
  - importa apenas namespace/binding ACPI e `i2c_core`;
  - define `I2cControllerHandle`, `I2cControllerDescriptor` e `I2cControllerBinding`;
  - usa `controller_id + generation` como identidade autorizadora;
  - valida coherence `backend_ready ↔ backend_instance` sem conhecer o tipo do backend;
  - exige que `AmlI2cAcpiBinding.controller_namespace_index` corresponda ao node ACPI do descriptor;
  - rejeita conexão `device_initiated` neste host-controller core;
  - valida address width, velocidade e suporte 7/10-bit contra `I2cControllerCapabilities`;
  - cria binding generation-safe preservando resource/device/source index e parâmetros da conexão;
  - não autoriza execução de binding sem o mesmo descriptor/generation/backend token;
  - detecta binding stale quando o mesmo `controller_id` reaparece com generation diferente.
- `kernel/src/main.sotlas`
  - importa `i2c_controller` imediatamente após `i2c_protocol`.
- `tests/test_i2c_controller.py`
  - prova identidade/generation, namespace/capability gate, backend-ready coherence, stale binding e ausência de efeitos físicos/registry.
- `docs/BAKEN_OS_I2C_ROADMAP_APPENDIX_II.md`
  - registra o fechamento 4/4 do I2C-1c e o contrato deste candidato.
- `docs/KERNEL_I2C_HANDOFF_APPENDIX_II.md`
  - este handoff operacional.

## Fronteira deliberada

Este SHA **não** implementa:

- registry global de controllers;
- attach/detach ou incremento de generation;
- ACPI `_ADR`/PCI BDF mapping;
- identificação Intel LPSS/Serial-IO, AMD ou DesignWare;
- MMIO/PIO;
- DMA/IRQ/GPIO;
- timer source, polling ou waits;
- execução AML;
- HID-I2C.

A ausência de backend físico é intencional. O PCI core existente possui inventário genérico, mas não há evidência suficiente no repositório para selecionar silício sem risco de hardcode incorreto. O lado firmware já possui `controller_namespace_index`, endereço e velocidade; o próximo estágio deverá criar ownership/lifecycle da instância e o elo certificado até o controller concreto.

## Próximo passo somente após 4/4

**I2C-2 — controller registry/lifecycle + discovery/binding generation-safe**:

1. registry bounded de controllers com `controller_id + generation`;
2. attach/activate/fail/detach e invalidação de handles stale;
3. discovery bridge que publica descriptors sem tocar hardware antes de identificar o backend correto;
4. correlação ACPI namespace → controller instance concreta;
5. somente depois, backend físico alvo e seus registradores.

Se qualquer gate do I2C-1d falhar, congelar `main` no SHA reprovado, registrar run/step/causa e aplicar **somente correction-only**.

# Baken OS — Kernel I2C Handoff Appendix X

> Append-only. Preservar integralmente todos os apêndices e resultados anteriores (mantendo os Apêndices VIII e IX como históricos).

## Estado operacional — 2026-09-14

Branch operacional: **`main`**.

Fase: **Fase 2 — Platform/Drivers**  
Trilha: **Trilha B2 — I2C Foundation & I2C-HID**  
Status da Fundação I2C & Backend Físico: **Certificados (I2C-0 a I2C-5F)**  
Status do I2C-HID: **I2C-HID-0 Certificado (Descoberta ACPI + Avaliação de _DSM)**

---

### Módulos Adicionados / Modificados em I2C-HID-0

1. `kernel/src/acpi/aml_evaluator.sotlas` (AML-6b):
   - Suporte à flag `Serialized` (`0x08`) no cabeçalho do método.
   - Suporte à comparação byte-a-byte de `AML_EVAL_VALUE_BUFFER` em `AML_LEQUAL_OP`.
   - Funções auxiliares `aml_eval_buffer()` e `aml_eval_package()`.

2. `kernel/src/drivers/i2c_hid_acpi.sotlas`:
   - Detecção de `PNP0C50` / `ACPI0C50` em `_HID` e `_CID`.
   - Extração estruturada de `I2CSerialBusConnection` e `GpioInt` do `_CRS`.
   - Avaliação completa de `_DSM` (Function 0 para confirmação de suporte, Function 1 para obtenção do registrador do descritor).
   - Amarração com o controlador I2C correspondente via `i2c_discovery_bridge`.
   - Tabela estática de capacidade 4 (`I2C_HID_MAX_DEVICES`), sem alocação dinâmica.

3. `kernel/src/main.sotlas`:
   - Inclusão de `import kernel::drivers::i2c_hid_acpi::*;`.

4. `kernel/src/baken_native_runtime.sotlas`:
   - Inclusão de `i2c_hid_acpi_scan_devices()` na rota canônica de boot.

---

### Métricas e Validação

- **Resolução de Grafo Modular Sotlas**: **180 módulos resolvidos**, 0 raízes órfãs.
- **Suítes de Teste**:
  - `tests/test_aml_evaluator_dsm.py` (4/4) ✅
  - `tests/test_i2c_hid_acpi.py` (7/7) ✅
  - `tests/test_i2c_hid_contract.py` (4/4) ✅
  - Suítes de regressão I2C (59 testes) ✅
  - Suíte do avaliador AML (10 testes) ✅
  - Total I2C/HID ativo: **89 testes com 100% de sucesso**.
- **Preservação de Invariantes**: Boot smoke em QEMU e isolamento de falhas SMP 100% preservados.

---

### Próxima Etapa: I2C-HID-1

- **Objetivo**: Leitura física dos 30 bytes do `I2c_HID_Descriptor` no endereço do registrador obtido via `_DSM` através da transação de barramento `i2c_dw_transfer` no controlador e slave address catalogados.

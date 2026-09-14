# Baken OS — Kernel I2C Handoff Appendix XI

> Append-only. Preservar integralmente todos os apêndices e resultados anteriores (mantendo os Apêndices VIII, IX e X como históricos).

## Estado operacional — 2026-09-14

Branch operacional: **`main`**.

Fase: **Fase 2 — Platform/Drivers**  
Trilha: **Trilha B2 — I2C Foundation & I2C-HID**  
Status da Fundação I2C & Backend Físico: **Certificados (I2C-0 a I2C-5F)**  
Status do I2C-HID: **Certificado e Integrado Ponta a Ponta (I2C-HID-0 a I2C-HID-6)**

---

### Módulos Adicionados em I2C-HID (Fases 1 a 5)

1. `kernel/src/drivers/i2c_hid_descriptor.sotlas`:
   - Decodificação e validação do descritor de 30 bytes Microsoft HID-over-I2C v1.00 (`I2cHidDescriptor`).
   - Leitura física via transação I2C combinada (`i2c_hid_read_descriptor_physical`).
   - Leitura e parsing de Report Descriptor (`i2c_hid_read_report_descriptor_physical`, `i2c_hid_parse_report_descriptor`).

2. `kernel/src/drivers/i2c_hid_command.sotlas`:
   - Emissão de comando `RESET` (`0x01`).
   - Emissão de comando `SET_POWER` (`0x08`, `POWER_ON`, `POWER_SLEEP`).

3. `kernel/src/drivers/i2c_hid_input.sotlas`:
   - Tabela estática com limite fixo de dispositivos (`I2C_HID_MAX_INPUT_DEVICES = 4`).
   - Recepção física em buffer estático de 256 bytes.
   - Desempacotamento de wire length LE e entrega de payload para o subsistema de eventos.
   - Sincronização via `SpinLock` com desativação de interrupções de CPU.

4. `kernel/src/drivers/i2c_hid_manager.sotlas`:
   - Inicialização e varredura coordenada dos dispositivos ACPI PNP0C50/ACPI0C50.
   - Vinculação com o modelo genérico de dispositivos (`i2c_device_attach`, `i2c_device_activate`).
   - Leitura de descritor, emissão de `SET_POWER` e `RESET`, parsing de relatórios e matrícula de input.

5. `kernel/src/main.sotlas`:
   - Inclusão e exportação dos novos módulos I2C-HID no grafo canônico.

6. `kernel/src/baken_native_runtime.sotlas`:
   - Inclusão ordenada de `i2c_hid_acpi_scan_devices()` e `i2c_hid_manager_init()` após a detecção de controladores I2C.

---

### Métricas e Validação

- **Grafo Modular do Kernel**: **184 módulos resolvidos**, 0 raízes órfãs.
- **Suítes de Teste Ativas**:
  - `tests/test_i2c_hid_descriptor.py` (11/11) ✅
  - `tests/test_i2c_hid_command.py` (6/6) ✅
  - `tests/test_i2c_hid_input.py` (7/7) ✅
  - `tests/test_i2c_hid_manager.py` (6/6) ✅
  - `tests/test_i2c_hid_acpi.py` (7/7) ✅
  - `tests/test_aml_evaluator_dsm.py` (4/4) ✅
  - Suítes de regressão I2C completas: **139 testes passando com 100% de sucesso**.
- **Contratos de Runtime**:
  - Zero alocação dinâmica no kernel (`no alloc`, `no malloc`).
  - Totalmente fail-closed e não-bloqueante na ausência de hardware em emuladores (QEMU).
  - Preservação integral dos 42 marcos de boot smoke.

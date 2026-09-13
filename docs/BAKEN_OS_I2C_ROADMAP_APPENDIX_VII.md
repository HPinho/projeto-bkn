# Baken OS — I2C Roadmap Appendix VII

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores.

## 2026-09-13 — Conclusão da Fundação I2C (I2C-2b, I2C-3 e I2C-4)

Com a estabilização do SMP no commit `5e9d2c9`, a Fundação I2C (Trilha B2) avança e conclui suas subfases centrais de abstração e arquitetura de dispositivos:

### 1. I2C-2b — ACPI ↔ Controller Discovery Bridge
- **Módulo**: `kernel/src/drivers/i2c_discovery_bridge.sotlas`
- **Testes**: `tests/test_i2c_discovery_bridge.py`
- **Escopo**:
  - Varredura de recursos ACPI (`AmlI2cAcpiBinding`) e registro automático no `i2c_controller_registry`.
  - Tabela estática bounded (`I2C_BRIDGE_CONTROLLERS`, capacidade 16 slots, sem heap).
  - Associação de capabilities de barramento (Standard 100 kHz, Fast-mode 400 kHz, suporte 7-bit/10-bit).
  - Descoberta e indexação de controladores a partir do `controller_namespace_index`.
  - Proteção por `SpinLock` com `x86_irq_save_disable()` e `x86_irq_restore(flags)`.

### 2. I2C-3 — GPIO & IRQ Foundation
- **Módulo**: `kernel/src/drivers/gpio_core.sotlas`
- **Testes**: `tests/test_gpio_core.py`
- **Escopo**:
  - Mapeamento de interrupções por pinos descritos em `GpioInt` ACPI.
  - Tabela de conexões bounded (`GPIO_CONNECTIONS`, capacidade 32 conexões).
  - Ciclo de vida generation-safe com `GpioPinHandle` (`connection_id + generation`).
  - Suporte a polaridades (*Active-High*, *Active-Low*, *Active-Both*) e disparo (*Edge* vs. *Level*).
  - Operações de mascaramento (`gpio_connection_mask`/`unmask`) e sinalização/consumo de IRQs pendentes (`gpio_connection_signal`/`consume_pending`).

### 3. I2C-4 — Generic I2C Device Model
- **Módulo**: `kernel/src/drivers/i2c_device.sotlas`
- **Testes**: `tests/test_i2c_device.py`
- **Escopo**:
  - Abstração unificada de dispositivo `I2cDevice` / `I2cTarget`.
  - Estados de ciclo de vida: `EMPTY → ATTACHED → ACTIVE → SUSPENDED → FAILED → DETACHED`.
  - Identidade generation-safe com `I2cDeviceHandle` (`device_id + generation`).
  - Vínculo direto ao `I2cControllerHandle` e à conexão GPIO correspondente.
  - API de transações síncronas:
    - `i2c_device_write`: envio de buffer de comando/dados.
    - `i2c_device_read`: recepção de bytes.
    - `i2c_device_write_read`: combined transaction com repeated START.
  - Execução estruturada via `i2c_core` (planejamento), `i2c_executor` (preparação) e `i2c_protocol` (máquina de estados).

---

## Estado da Trilha B2

A **Fundação I2C** está completa no nível de abstração, ciclo de vida e dispatch de transações. O grafo canônico do kernel modular em Sotlas (`kernel/src/main.sotlas`) agora resolve **177 módulos** sem raízes órfãs.

Próximo passo planejado da Trilha B2:
- Abertura formal da subtrilha **I2C-HID** (começando por **I2C-HID-0 — Transport**: identificação de `PNP0C50`, avaliação de `_DSM` e leitura/validação dos registradores do HID Descriptor via I2C).

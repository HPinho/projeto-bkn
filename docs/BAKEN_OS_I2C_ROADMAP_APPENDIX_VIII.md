# Baken OS — I2C Roadmap Appendix VIII

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores.

## 2026-09-13 — Implementação do Backend Físico I2C (I2C-5) & Hardening (I2C-5E)

A Fundação Arquitetural (I2C-0 a I2C-4) foi complementada com a camada física de controle de barramento (**I2C-5**) e consolidada na etapa de hardening (**I2C-5E**), garantindo segurança de tipos, filtro de hardware fail-closed, serialização SMP, medição temporal real de deadlines e vinculação completa ACPI ↔ PCI ↔ Registry:

### 1. I2C-5a — Hardware Discovery & Mapeamento MMIO (BAR/VMM)
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Testes**: `tests/test_i2c_physical_discovery.py`
- **Escopo**:
  - **Filtro Seguro de Hardware (P0)**: Validação estrita da classe PCI `0x0C` (Serial Bus, subclasses `0x80` e `0x05`) e correspondência exata a IDs de controladores Intel LPSS (SunrisePoint, Apollo Lake, Gemini Lake, Cannon Lake, Ice Lake, Tiger Lake, Alder Lake, Elkhart Lake, Meteor Lake) e Synopsys DesignWare (vendor `0x16C3`). Todo e qualquer outro dispositivo (NICs, xHCI, NVMe, SATA, GPU) retorna `I2C_HARDWARE_TYPE_UNKNOWN`.
  - **Correção de Sondagem de BAR (P0)**: Aceita retorno `step >= 1` de `pci_probe_bar()`, admitindo BARs 32-bit e 64-bit válidos e descartando BARs de E/S ou inválidos.
  - Ativação de Memory Space + Bus Master (`pci_enable_device`).
  - Mapeamento das páginas do BAR MMIO na VMM ativa (`active_page_tables_map_mmio_identity_4k`).
  - **Associação ACPI ↔ PCI**: Resolução do índice do namespace ACPI via correspondência de `_ADR` (`(slot << 16) | func`) contra a tabela de dispositivos `aml_discovery`.
  - **Ativação no Registry**: Inicialização física (`i2c_dw_init`), registro/lookup na bridge (`i2c_discovery_bridge`), publicação de backend (`i2c_controller_registry_publish_backend`) e ativação (`i2c_controller_registry_activate`).
  - **Serialização SMP**: Array de spinlocks por controlador físico (`I2C_PHYSICAL_CONTROLLER_LOCKS`) com APIs `i2c_physical_lock_controller` e `i2c_physical_unlock_controller` protegendo a transação inteira contra concorrência entre núcleos.

### 2. I2C-5b & I2C-5c — Driver Synopsys DesignWare APB / Intel LPSS
- **Módulo**: `kernel/src/drivers/i2c_designware.sotlas`
- **Testes**: `tests/test_i2c_designware.py`
- **Escopo**:
  - Mapeamento completo dos registradores do controlador (`DW_IC_CON`, `DW_IC_TAR`, `DW_IC_DATA_CMD`, `DW_IC_STATUS`, `DW_IC_TX_ABRT_SOURCE`, etc.).
  - **Separação LPSS Wrapper vs. Core DesignWare**: Constantes e procedimentos de desativação de reset privado LPSS (`i2c_lpss_reset_release`).
  - **Timings de Clock Sensíveis ao Hardware**: Cálculo dinâmico de `HCNT` e `LCNT` para Standard-mode (100 kHz) e Fast-mode (400 kHz) parametrizável pela frequência de clock de entrada (100 MHz, 120 MHz, 133 MHz, etc.).
  - **Deadline Temporal Real (Timeout)**: Substituição de contadores cegos de spin por medição temporal usando `x86_timer_read_tsc()` e `x86_timer_cycles_per_us()`, respeitando estritamente o contrato `transaction.timeout_us`.
  - Polling síncrono com monitoramento de thresholds dos FIFOs TX (`TFNF`, `TFE`) e RX (`RFNE`).
  - Detecção exata de causas de abort (`DW_ABRT_7B_ADDR_NOACK`, `DW_ABRT_TXDATA_NOACK`, `DW_ABRT_ARB_LOST`).
  - **Gravação física real**: na leitura (`DW_IC_CMD_READ`), os bytes recebidos do FIFO são copiados diretamente para o buffer de memória do chamador (`*buf.add(byte_idx) = received_byte;`).

### 3. Remoção do Fallback Sintético no Despachador de Dispositivo
- **Módulo**: `kernel/src/drivers/i2c_device.sotlas`
- **Escopo**:
  - `i2c_device_execute_transaction()` despacha exclusivamente através do backend de hardware ativo com lock de controlador SMP.
  - Se `!desc.backend_ready || desc.backend_instance == 0`, a função falha fechada imediatamente retornando `I2C_STATUS_CONTROLLER_ERROR`. Nenhum sucesso sintético falso é retornado em ambiente de produção.
  - A emulação de protocolo para testes e validação analítica foi segregada em `i2c_device_simulate_protocol()`.

### 4. I2C-5d & I2C-5E — Testes Semânticos e Contratuais Executáveis
- **Testes**: `tests/test_i2c_semantic_execution.py`, `tests/test_i2c5_runtime_contract.py`
- **Escopo**:
  - Validação semântica e comportamental executável de WRITE, READ com mutação de buffer, e WRITE→RESTART→READ (combined transaction).
  - Injeção e tratamento de falhas: ADDRESS_NACK, DATA_NACK, ARBITRATION_LOST, TIMEOUT temporal por SCL hang.
  - Teste estrito de segurança contra *stale generation*, serialização SMP por lock e conformidade total com o QEMU Boot Smoke gate.

---

## Estado da Trilha B2

- **Fundação Arquitetural**: ✅ Concluída.
- **Backend Físico do Controlador (MMIO / DesignWare / LPSS)**: ✅ Implementado, endurecido e certificado.
- **Grafo do Kernel Modular**: **179 módulos resolvidos**, 0 raízes órfãs.
- **Suíte I2C**: **109 testes passando com 100% de sucesso**.

Próximo passo liberado com base física e arquitetural completa:
- **I2C-HID-0**: Identificação formal de `PNP0C50`, avaliação de `_DSM` e leitura física dos registradores do descritor HID através de `i2c_device_read()`.

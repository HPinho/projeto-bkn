# Baken OS — I2C Roadmap Appendix VIII

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores.

## 2026-09-13 — Implementação do Backend Físico I2C (I2C-5)

A Fundação Arquitetural (I2C-0 a I2C-4) foi complementada com a camada física de controle de barramento (**I2C-5**), substituindo o laço sintético de eventos por um backend de hardware real orientado a registradores MMIO e gravação física em memória:

### 1. I2C-5a — Hardware Discovery & Mapeamento MMIO (BAR/VMM)
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Testes**: `tests/test_i2c_physical_discovery.py`
- **Escopo**:
  - Varredura PCI procurando controladores da classe `0x0C` (Serial Bus, subclasses `0x80` e `0x05`) e famílias Intel LPSS (SunrisePoint, Kaby Lake, Tiger Lake, Alder Lake).
  - Leitura de BAR 0 (`pci_probe_bar`), ativação de Memory Space + Bus Master (`pci_enable_device`).
  - Mapeamento das páginas do BAR MMIO na VMM ativa (`active_page_tables_map_mmio_identity_4k`).
  - Registro central dos controladores físicos em tabela estática bounded (`I2C_PHYSICAL_CONTROLLERS`).

### 2. I2C-5b & I2C-5c — Driver Synopsys DesignWare APB / Intel LPSS
- **Módulo**: `kernel/src/drivers/i2c_designware.sotlas`
- **Testes**: `tests/test_i2c_designware.py`
- **Escopo**:
  - Mapeamento completo dos registradores do controlador (`DW_IC_CON`, `DW_IC_TAR`, `DW_IC_DATA_CMD`, `DW_IC_STATUS`, `DW_IC_TX_ABRT_SOURCE`, etc.).
  - Configuração de timings de barramento SCL para Standard-mode 100 kHz e Fast-mode 400 kHz.
  - Polling síncrono com monitoramento de thresholds dos FIFOs TX (`TFNF`, `TFE`) e RX (`RFNE`).
  - Detecção exata de causas de abort (`DW_ABRT_7B_ADDR_NOACK`, `DW_ABRT_TXDATA_NOACK`, `DW_ABRT_ARB_LOST`).
  - **Gravação física real**: na leitura (`DW_IC_CMD_READ`), os bytes recebidos do FIFO são copiados diretamente para o buffer de memória do chamador (`*buf.add(byte_idx) = received_byte;`).
  - Despacho integrado em `i2c_device_execute_transaction()`.

### 3. I2C-5d — Testes Semânticos Executáveis
- **Testes**: `tests/test_i2c_semantic_execution.py`
- **Escopo**:
  - Validação semântica e comportamental executável de WRITE, READ com mutação de buffer, e WRITE→RESTART→READ (combined transaction).
  - Injeção e tratamento de falhas: ADDRESS_NACK, DATA_NACK, ARBITRATION_LOST, TIMEOUT por SCL hang.
  - Teste estrito de segurança contra *stale generation* e handles desanexados.

---

## Estado da Trilha B2

- **Fundação Arquitetural**: ✅ Concluída.
- **Backend Físico do Controlador (MMIO / DesignWare)**: ✅ Implementado e testado.
- **Grafo do Kernel Modular**: **179 módulos resolvidos**, 0 raízes órfãs.
- **Suíte I2C**: **95 testes passando com 100% de sucesso**.

Próximo passo liberado com base sólida:
- **I2C-HID-0**: Identificação formal de `PNP0C50`, avaliação de `_DSM` e leitura física dos registradores do descritor HID através de `i2c_device_read()`.

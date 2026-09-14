# Baken OS — Kernel I2C Handoff Appendix VIII

> Append-only. Preservar integralmente todos os apêndices e resultados anteriores.

## Estado operacional — 2026-09-13

Branch operacional: **`main`**.

Fase: **Fase 2 — Platform/Drivers**
Trilha: **Trilha B2 — I2C Foundation & Physical Backend**
Status da Fundação I2C & Backend: **Concluída (I2C-0 a I2C-5)**

### Módulos adicionados e certificados localmente

1. `kernel/src/drivers/i2c_physical_discovery.sotlas`:
   - Descoberta de controladores I2C físicos via barramento PCI (classe `0x0C`, subclasses `0x80` e `0x05`, e IDs específicos Intel LPSS).
   - Sondagem e validação de BAR 0 MMIO (`pci_probe_bar`).
   - Ativação de comandos PCI (Memory Space + Bus Master).
   - Mapeamento das páginas do espaço MMIO na VMM ativa (`active_page_tables_map_mmio_identity_4k`).
   - Registro em tabela estática de controladores físicos (`I2C_PHYSICAL_CONTROLLERS`).
   - Teste correspondente: `tests/test_i2c_physical_discovery.py`.

2. `kernel/src/drivers/i2c_designware.sotlas`:
   - Driver de silício Synopsys DesignWare APB / Intel LPSS.
   - Mapeamento de registradores MMIO (`DW_IC_CON`, `DW_IC_TAR`, `DW_IC_DATA_CMD`, `DW_IC_STATUS`, `DW_IC_TX_ABRT_SOURCE`, etc.).
   - Configuração de timings de clock SCL para Standard-mode (100 kHz) e Fast-mode (400 kHz).
   - Polling síncrono e controle de FIFOs TX/RX.
   - Decodificação precisa de abortos e falhas (`ADDRESS_NACK`, `DATA_NACK`, `ARBITRATION_LOST`).
   - Gravação física de bytes lidos diretamente no ponteiro de dados do buffer (`I2cMessage.data`).
   - Integração direta no despachador de transações `i2c_device_execute_transaction()` em `kernel/src/drivers/i2c_device.sotlas`.
   - Testes correspondentes: `tests/test_i2c_designware.py` e `tests/test_i2c_semantic_execution.py`.

### Grafo Modular de Compilação Sotlas

- `kernel/src/main.sotlas` atualizado com as importações canônicas dos 2 novos módulos.
- Resolução do compilador: **179 módulos resolvidos**, 0 fora da rota ativa, 0 raízes órfãs.
- Suíte específica I2C/GPIO: **95 testes passando com 100% de sucesso**.

### Fronteiras deliberadas e Non-Goals deste corte

- O backend físico opera em modo síncrono por polling das FIFOs, simplificando a latência e garantindo previsibilidade determinística antes da introdução de buffers assíncronos e interrupções complexas.
- A detecção e mapeamento MMIO são estáticos e bounds-checked (limite máximo de controladores físicos `MAX_PHYSICAL_CONTROLLERS = 8`).
- Não há modificação no parser, lexer ou semântica do compilador Sotlas (`HPinho/LangSotlas`).
- O ciclo de boot normal do QEMU não falha caso controladores físicos I2C não estejam presentes na máquina virtual (fail-safe e gracefully non-blocking).

### Próximo passo autorizado

Com o Backend Físico I2C (I2C-5) implementado e certificado:
- **I2C-HID-0**: Identificação formal de `PNP0C50`, avaliação de `_DSM` (Function 1) e leitura real do HID Descriptor via `i2c_device_read()`.

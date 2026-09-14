# Baken OS — Kernel I2C Handoff Appendix VIII

> Append-only. Preservar integralmente todos os apêndices e resultados anteriores.

## Estado operacional — 2026-09-13

Branch operacional: **`main`**.

Fase: **Fase 2 — Platform/Drivers**
Trilha: **Trilha B2 — I2C Foundation & Physical Backend**
Status da Fundação I2C & Backend: **Certificada e Endurecida (I2C-0 a I2C-5E)**

### Módulos adicionados e certificados localmente

1. `kernel/src/drivers/i2c_physical_discovery.sotlas`:
   - Descoberta de controladores I2C físicos via barramento PCI com filtro estrito de classe (`0x0C`, subclasses `0x80` e `0x05`) e listas fechadas de IDs homologados Intel LPSS e Synopsys DesignWare. Dispositivos de rede, vídeo, armazenamento e USB retornam `UNKNOWN` e são sumariamente descartados.
   - Sondagem e validação de BAR 0 MMIO (`bar_step >= 1 && bar0.base_address != 0 && !bar0.is_io`).
   - Ativação de comandos PCI (Memory Space + Bus Master).
   - Mapeamento das páginas do espaço MMIO na VMM ativa (`active_page_tables_map_mmio_identity_4k`).
   - Associação com o namespace ACPI via correspondência exata de `_ADR` (`(slot << 16) | func`) contra a tabela `aml_discovery`.
   - Inicialização do hardware (`i2c_dw_init`), publicação de backend (`i2c_controller_registry_publish_backend`) e ativação (`i2c_controller_registry_activate`).
   - Serialização de transações no barramento através de array de locks de controlador (`I2C_PHYSICAL_CONTROLLER_LOCKS`).
   - Teste correspondente: `tests/test_i2c_physical_discovery.py`.

2. `kernel/src/drivers/i2c_designware.sotlas`:
   - Driver de silício Synopsys DesignWare APB / Intel LPSS.
   - Mapeamento de registradores MMIO (`DW_IC_CON`, `DW_IC_TAR`, `DW_IC_DATA_CMD`, `DW_IC_STATUS`, `DW_IC_TX_ABRT_SOURCE`, etc.).
   - Separação entre bloco core DesignWare e wrapper privado Intel LPSS com procedimento de liberação de reset (`i2c_lpss_reset_release`).
   - Cálculo dinâmico de timings SCL sensível à frequência de entrada (`i2c_dw_calc_scl_hcnt`, `i2c_dw_calc_scl_lcnt`).
   - Deadline temporal real baseado no timer calibrado do kernel (`x86_timer_read_tsc`, `x86_timer_cycles_per_us`), respeitando `transaction.timeout_us`.
   - Polling síncrono e controle de FIFOs TX/RX.
   - Decodificação precisa de abortos e falhas (`ADDRESS_NACK`, `DATA_NACK`, `ARBITRATION_LOST`).
   - Gravação física de bytes lidos diretamente no ponteiro de dados do buffer (`I2cMessage.data`).
   - Teste correspondente: `tests/test_i2c_designware.py`.

3. `kernel/src/drivers/i2c_device.sotlas`:
   - Despacho físico obrigatório com lock de controlador SMP (`i2c_physical_lock_controller`).
   - Eliminação completa de fallback sintético: transações sem backend ativo falham fechadas retornando `I2C_STATUS_CONTROLLER_ERROR`.
   - Emulação de protocolo isolada para validação e testes em `i2c_device_simulate_protocol()`.

### Grafo Modular de Compilação Sotlas

- `kernel/src/main.sotlas` atualizado com as importações canônicas.
- Resolução do compilador: **179 módulos resolvidos**, 0 fora da rota ativa, 0 raízes órfãs.
- Suíte específica I2C/GPIO: **109 testes passando com 100% de sucesso**.

### Fronteiras deliberadas e Non-Goals deste corte

- O backend físico opera em modo síncrono por polling das FIFOs, com deadline temporal real baseado no TSC calibrado do kernel.
- A detecção e mapeamento MMIO são estáticos e bounds-checked (limite máximo de controladores físicos `MAX_PHYSICAL_CONTROLLERS = 8`).
- Não há modificação no parser, lexer ou semântica do compilador Sotlas (`HPinho/LangSotlas`).
- O ciclo de boot normal do QEMU permanece fail-safe e não-bloqueante (sem loops infinitos ou panics quando não há controlador físico presente).

### Próximo passo autorizado

Com o Backend Físico I2C endurecido e certificado (I2C-5E):
- **I2C-HID-0**: Identificação formal de `PNP0C50`, avaliação de `_DSM` (Function 1) e leitura real do HID Descriptor via `i2c_device_read()`.

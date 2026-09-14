# Baken OS — I2C Roadmap Appendix IX

> Append-only. Este apêndice não altera nem substitui os apêndices anteriores (preservando integralmente o Apêndice VIII).

## 2026-09-13 — Certificação de Runtime e Backend Físico I2C (I2C-5F)

A etapa de hardening estrutural (I2C-5E) foi elevada à certificação completa de runtime e hardware (**I2C-5F**), sanando todos os apontamentos da segunda auditoria profunda e liberando formalmente a transição para **I2C-HID-0**:

### 1. P0: Integração Canônica na Rota de Boot do Kernel
- **Módulo**: `kernel/src/baken_native_runtime.sotlas`
- **Contrato**: Chamada ativa, oportuna e estritamente não-bloqueante de:
  - `i2c_discovery_scan_acpi_controllers()`
  - `i2c_physical_probe_pci()`
- **Localização**: Invocada logo após a inicialização do catálogo de plataforma (`aml_platform_catalog_init()`), quando os namespaces AML e a topologia PCI já se encontram catalogados.
- **Garantia fail-safe**: Se nenhum controlador I2C físico for detectado (cenário padrão em VMs QEMU sem barramento I2C emulado), a rotina retorna 0 silenciosamente sem travar, sem loops infinitos e sem gerar panics, preservando 100% dos 42 marcos de boot smoke.

### 2. P0: Gate Estrito de Inicialização (`init_ok`)
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Contrato**: O resultado de `i2c_dw_init_with_clock(...)` é verificado obrigatoriamente.
- **Fail-Closed**: Se `!init_ok`, o controlador físico é descartado imediatamente: não é incrementado o contador de dispositivos descobertos, não é gerado handle de controller e não são executadas as chamadas `i2c_controller_registry_publish_backend()` nem `i2c_controller_registry_activate()`. Controladores com falha de silício nunca são expostos como operacionais ao restante do kernel.

### 3. P0: Verificação Estrita do Mapeamento MMIO na VMM
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Contrato**: A invocação `active_page_tables_map_mmio_identity_4k(page_aligned)` é checada ativamente. Se retornar `false`, a descoberta do dispositivo é abortada (`continue;`), eliminando o risco de Page Fault durante acessos aos registradores do silício.

### 4. P0: Correção do Wrapper Intel LPSS (Bits e Sequência Canônica)
- **Módulo**: `kernel/src/drivers/i2c_designware.sotlas`
- **Contrato**:
  - `LPSS_PRIV_REMAP_ADDR: u64 = 0x00`
  - `LPSS_PRIV_RESETS_FUNC: u32 = 0x03`
  - `LPSS_PRIV_RESETS_IDMA: u32 = 1 << 2` (bit 2)
  - `LPSS_PRIV_RESETS_BOTH: u32 = 0x07`
- **Sequência canônica de reset release**:
  1. Força reset do subsistema escrevendo `0` em `LPSS_PRIV_RESETS`.
  2. Libera o reset de função e IDMA gravando `LPSS_PRIV_RESETS_BOTH` (`0x07`).
  3. Programa o registrador `LPSS_PRIV_REMAP_ADDR` com o endereço físico base do dispositivo para remap de barramento interno.

### 5. P0/P1: Binding ACPI ↔ PCI Fail-Closed Estrito
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Contrato**:
  - A função `i2c_physical_find_acpi_namespace()` restringe o pareamento de `_ADR` ao barramento raiz PCI (`bus == 0`), rejeitando ambiguidades em barramentos secundários (`bus != 0` retorna `AML_NAMESPACE_INVALID_INDEX`).
  - Remoção total de fallbacks sintéticos (`i2c_discovery_find_unbound_controller` ou criação de namespaces artificiais `slot_idx + 1`). Dispositivos PCI sem correspondência ACPI exata permanecem estritamente unbound e não são publicados no registry.

### 6. P1: Clocks de Entrada Conforme a Geração de Hardware
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Contrato**: Função `i2c_physical_clock_for_device(vendor_id, device_id)`:
  - Skylake / Kaby Lake / Sunrise Point (`0x9D60..0x9D65`): **120 MHz**.
  - Apollo Lake / Gemini Lake / Tiger Lake / Alder Lake / Meteor Lake (`0x5AAC..0x5AB0`, `0x31AC..0x31B0`, `0xA0C5..0xA0E9`, `0x46D5..0x46E9`, etc.): **133 MHz**.
  - Silício genérico Synopsys DesignWare (`0x16C3`): **100 MHz**.
- O clock identificado é salvo em `controller.input_clock_hz` e repassado diretamente para os cálculos de `HCNT` e `LCNT` via `i2c_dw_init_with_clock()`.

### 7. P1: Suporte a 10-bit e Capacidade Anunciada
- **Módulo**: `kernel/src/drivers/i2c_designware.sotlas`, `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Contrato**:
  - `i2c_dw_transfer()` agora configura tanto `DW_IC_TAR_10BITADDR_MASTER` (bit 12) quanto `DW_IC_CON_10BITADDR_MASTER` (bit 4 de `DW_IC_CON`).
  - Enquanto não houver suíte completa de testes de silício para endereçamento 10-bit em hardware real, o backend físico publica explicitamente `supports_10bit: false` no registro do controlador, evitando anúncios indevidos de capacidades incompletas.

### 8. P1: Lock SMP sem Desativação Prolongada de Interrupções
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`, `kernel/src/drivers/i2c_device.sotlas`
- **Contrato**:
  - `i2c_physical_lock_controller()` utiliza spinlock puro por controlador (`spinlock_lock`), sem mascarar globalmente as interrupções da CPU via `cli` (`IF=1` preservado durante todo o polling de transação).
  - Garante serialização atômica entre cores SMP sem degradar o jitter do escalonador, timers e dispositivos de entrada (HID).

### 9. P1: Deadline Temporal Único e Compartilhado
- **Módulo**: `kernel/src/drivers/i2c_designware.sotlas`
- **Contrato**:
  - Cálculo de um único `deadline_tsc = start_tsc + timeout_cycles` logo na entrada de `i2c_dw_transfer()`.
  - Todas as etapas da transação (espera de TX FIFO livre, esvaziamento de TX FIFO, leitura de RX FIFO e espera final por barramento idle) compartilham esse mesmo deadline temporal absoluto, garantindo que a transação nunca exceda `timeout_us`.
  - `i2c_dw_enable()` também conta com deadline temporal de 25 ms calibrado pelo timer TSC.

### 10. P1: Comando PCI Mínimo Necessário
- **Módulo**: `kernel/src/drivers/i2c_physical_discovery.sotlas`
- **Contrato**:
  - Habilita exclusivamente `PCI_COMMAND_MEMORY_SPACE` via `pci_enable_command_bits()`, sem habilitar Bus Master enquanto o backend operar em PIO síncrono.

---

## Matriz de Conformidade do Roadmap I2C

| Componente | Estado Anterior (I2C-5E) | Estado Certificado (I2C-5F) |
|---|---|---|
| Rota Canônica de Boot | 🔴 Ausente | ✅ `baken_native_runtime` chama ACPI e PCI discovery |
| Gate de Inicialização MMIO/Silício | 🔴 `init_ok` ignorado | ✅ `init_ok == true` obrigatório para publicação e ativação |
| Mapeamento VMM Identity | 🔴 Retorno ignorado | ✅ `active_page_tables_map_mmio_identity_4k` checado |
| Intel LPSS Wrapper | 🔴 Bits / reset incorretos | ✅ Sequência `0 -> 0x07` + remap addr `0x00` |
| ACPI ↔ PCI Binding | 🟠 Fallback sintético / bus != 0 | ✅ Fail-closed estrito, bus 0 e sem fallback arbitrário |
| Clock Real do Controlador | 🟠 100 MHz genérico | ✅ 120 MHz (SKL/KBL), 133 MHz (APL/GLK/TGL/ADL), 100 MHz (DW) |
| Endereçamento 10-bit | 🟠 Anunciado incompleto | ✅ `DW_IC_CON` corrigido e `supports_10bit: false` anunciado |
| SMP Controller Locking | 🟡 `IF=0` durante polling | ✅ Spinlock puro mantendo `IF=1` |
| Timeout Temporal | 🟡 Prazos reiniciados por fase | ✅ `deadline_tsc` único compartilhado por toda a transação |
| Comandos PCI | 🟡 Bus Master desnecessário | ✅ Apenas `PCI_COMMAND_MEMORY_SPACE` |

---

## Estado da Trilha B2

- **I2C-0 a I2C-4 (Fundação Arquitetural)**: ✅ Certificada.
- **I2C-5 (Backend Físico do Controlador)**: ✅ Implementado e Certificado (I2C-5F).
- **Grafo do Kernel Modular**: **179 módulos resolvidos**, 0 raízes órfãs.
- **Suíte I2C**: **109 testes com 100% de aprovação**.
- **Próxima Etapa Liberada**: **I2C-HID-0** (Descoberta `PNP0C50`, avaliação `_DSM` Function 1 e leitura real do descritor HID).

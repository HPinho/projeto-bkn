# Baken OS — Kernel I2C Handoff Appendix IX

> Append-only. Preservar integralmente todos os apêndices e resultados anteriores (mantendo o Apêndice VIII como histórico).

## Estado operacional — 2026-09-13

Branch operacional: **`main`**.

Fase: **Fase 2 — Platform/Drivers**  
Trilha: **Trilha B2 — I2C Foundation & Physical Backend**  
Status da Fundação I2C & Backend: **Certificada para Runtime e Hardware Físico (I2C-5F)**

---

### Módulos Certificados em I2C-5F

1. `kernel/src/baken_native_runtime.sotlas`:
   - Vinculação canônica e não-bloqueante de `i2c_discovery_scan_acpi_controllers()` e `i2c_physical_probe_pci()` logo após a inicialização do catálogo de plataforma.
   - Preservação total de segurança em QEMU e bare-metal (zero loops infinitos ou panics quando não há controlador I2C presente).

2. `kernel/src/drivers/i2c_physical_discovery.sotlas`:
   - Gate estrito de inicialização: `if !init_ok { continue; }` impede a publicação ou ativação de hardware com falha de silício.
   - Verificação de mapeamento MMIO: `if !active_page_tables_map_mmio_identity_4k(page_aligned) { continue; }`.
   - Binding ACPI estrito: restrito a dispositivos no barramento raiz PCI (`bus == 0`), descartando fallbacks sintéticos.
   - Clocks por geração de hardware (`i2c_physical_clock_for_device`): 120 MHz para Skylake/Kaby Lake, 133 MHz para Apollo/Gemini/Tiger/Alder Lake, 100 MHz para Synopsys genérico.
   - Capacidade 10-bit anunciada com segurança: `supports_10bit: false` durante registro de capacidades.
   - Lock SMP sem mascarar interrupções: `i2c_physical_lock_controller()` e `i2c_physical_unlock_controller()` mantêm `IF=1` durante todo o polling de transação.
   - Comandos PCI enxutos: apenas `PCI_COMMAND_MEMORY_SPACE` habilitado.

3. `kernel/src/drivers/i2c_designware.sotlas`:
   - Wrapper Intel LPSS com registradores e constantes de referência: `REMAP_ADDR = 0x00`, `RESETS_FUNC = 0x03`, `RESETS_IDMA = 1 << 2`, `RESETS_BOTH = 0x07`.
   - Sequência canônica de reset release: reset assert (0) -> reset deassert (`0x07`) -> gravação do remap address base.
   - Deadline temporal compartilhado: cálculo inicial de `deadline_tsc` estritamente respeitado em todas as fases de `i2c_dw_transfer()`.
   - Timeout temporal também calibrado em `i2c_dw_enable()` (25 ms).
   - Suporte a 10-bit master completo no silício: `DW_IC_TAR_10BITADDR_MASTER` e `DW_IC_CON_10BITADDR_MASTER`.

4. `kernel/src/drivers/i2c_device.sotlas`:
   - Despacho físico de transações utilizando o lock SMP sem mascaramento de interrupções.

---

### Verificação e Métricas

- **Resolução de Grafo Modular Sotlas**: 179 módulos resolvidos, 0 raízes órfãs.
- **Suítes de Testes I2C (5 suites)**:
  - `test_i2c_physical_discovery.py` (8/8)
  - `test_i2c_designware.py` (8/8)
  - `test_i2c5_runtime_contract.py` (11/11)
  - `test_i2c_semantic_execution.py` (8/8)
  - `test_i2c_device.py` (6/6)
  - **Total**: 41 testes contratual/semânticos executáveis + 68 testes de fundação = **109 testes passando (100% de sucesso)**.
- **Invariantes do QEMU Boot Smoke**: 42 marcos de boot preservados sem regressão.

---

### Próxima Etapa Liberada: I2C-HID-0

Com a certificação física e de runtime I2C-5F concluída, está autorizada a abertura da subtrilha I2C-HID:
- Identificação formal de `PNP0C50` / `ACPI0C50` via `aml_discovery`.
- Execução do método `_DSM` (Function 1) com o UUID canônico da Microsoft (`3CD64FD8-7F28-446A-81E5-3A26A4A0A477`) para obter o registrador do descritor HID.
- Leitura física do `HID Descriptor` via `i2c_device_read()`.

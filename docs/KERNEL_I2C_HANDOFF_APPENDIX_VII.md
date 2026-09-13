# Baken OS — Kernel I2C Handoff Appendix VII

> Append-only. Preservar integralmente todos os apêndices e resultados anteriores.

## Estado operacional — 2026-09-13

Branch operacional: **`main`**.

Fase: **Fase 2 — Platform/Drivers**
Trilha: **Trilha B2 — I2C Foundation & I2C-HID**
Status da Fundação I2C: **Concluída (I2C-0, I2C-1, I2C-2, I2C-3, I2C-4)**

### Módulos adicionados e certificados localmente

1. `kernel/src/drivers/i2c_discovery_bridge.sotlas`:
   - Bridge entre o namespace ACPI e os slots do `i2c_controller_registry`.
   - Mapeamento de capabilities e escaneamento automático de controladores.
   - Teste correspondente: `tests/test_i2c_discovery_bridge.py`.

2. `kernel/src/drivers/gpio_core.sotlas`:
   - Roteamento e lifecycle de interrupções GPIO ACPI (`GpioInt`).
   - Tabela de conexões com handles generation-safe (`connection_id + generation`).
   - Mascaramento, unmask e sinalização de interrupções sob `SpinLock` IRQ-safe.
   - Teste correspondente: `tests/test_gpio_core.py`.

3. `kernel/src/drivers/i2c_device.sotlas`:
   - Modelo genérico de dispositivo I2C (`I2cDevice` / `I2cTarget`).
   - Ciclo de vida com estados `EMPTY → ATTACHED → ACTIVE → SUSPENDED → FAILED → DETACHED`.
   - Dispatch de transações síncronas (`write`, `read`, `write_read` com repeated START) através do `i2c_protocol` e `i2c_core`.
   - Teste correspondente: `tests/test_i2c_device.py`.

### Grafo Modular de Compilação Sotlas

- `kernel/src/main.sotlas` atualizado com as importações canônicas dos 3 novos módulos.
- Resolução do compilador: **177 módulos resolvidos**, 0 fora da rota ativa, 0 raízes órfãs.
- Suíte específica I2C/GPIO: **76 testes passando com 100% de sucesso**.

### Fronteiras deliberadas e Non-Goals deste corte

- Não há drivers de silício específicos (ex: registradores MMIO Intel LPSS/DesignWare); a camada de bridge e executor continua data-oriented e compatível com mock/hardware loops.
- Não há modificação no parser, lexer ou semântica do compilador Sotlas (`HPinho/LangSotlas`).
- O Kernel Core permanece congelado e invariant-preserving.

### Próximo passo autorizado

Com a Fundação I2C estabelecida, a Trilha B2 pode avançar para **I2C-HID**:
- **I2C-HID-0**: Identificação formal de `PNP0C50`, avaliação do método `_DSM` (Function 1) e leitura dos registradores do HID Descriptor via transação `i2c_device_read()`.

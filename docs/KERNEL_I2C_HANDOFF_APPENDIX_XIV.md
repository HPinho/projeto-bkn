# Baken OS — Kernel I2C Handoff Appendix XIV — GPIO-PHYS-0

> Handoff aditivo. Não substitui nem reescreve o conteúdo dos handoffs anteriores.

## Base de integração

Base esperada antes deste estágio:

`9bfa54e148875b22c011cd16f47e811cf27af111`

Essa base contém I2C-HID-6 e o boundary lógico de GPIO que exigia um backend físico antes de publicar conexões úteis.

## O que GPIO-PHYS-0 adiciona

### 1. Core GPIO vendor-neutral

`kernel/src/drivers/gpio_core.sotlas`

- registro ACPI passa a criar `CONFIGURED`, não `ACTIVE`;
- somente um backend físico pode promover para `ACTIVE`;
- novas operações `gpio_connection_activate()` e `gpio_connection_deactivate()`;
- unregister recusa conexão ainda `ACTIVE`/`MASKED`;
- exatamente um pin por `GpioInt` nesta etapa;
- revalidação do backend sob o lock do core evita janela TOCTOU durante o registro;
- nenhum conhecimento de fabricante foi adicionado ao core.

### 2. Dispatcher físico neutro

`kernel/src/drivers/gpio_physical.sotlas`

Consumidores deixam de depender diretamente de um backend de fabricante. A camada expõe:

- `gpio_physical_probe_all()`;
- `gpio_physical_arm_connection()`;
- `gpio_physical_disarm_connection()`;
- `gpio_physical_irq_dispatch()`.

O único backend conectado em GPIO-PHYS-0 é Tiger Lake. Backends AMD/Intel adicionais e, em arquiteturas ARM futuras, Qualcomm/MediaTek/NVIDIA-Tegra entram como módulos separados.

### 3. Intel Tiger Lake físico

`kernel/src/drivers/intel_tigerlake_gpio.sotlas`

Fluxo efetivo:

`AML device -> static _CRS -> FixedMemory32 + ExtendedIRQ -> MMIO identity map -> REVID/PADBAR -> ACPI gpio number -> community/GPP/pad -> PAD_OWN -> PADCFGLOCK/PADCFGLOCKTX -> HOSTSW_OWN -> PADCFG0 -> GPI_IS/GPI_IE -> IOAPIC GSI -> IRQ 0x46`

Suporte inicial:

- `INT34C5` / `INTC1055`: Tiger Lake-LP;
- `INT34C6`: Tiger Lake-H.

A política é intencionalmente restritiva:

- `_CRS` por Method/evaluator: recusado;
- MMIO inválido/desalinhado/excessivo: recusado;
- pad sem tradução GPIO conhecida: recusado;
- pad não pertencente ao host: recusado;
- config/tx lock ativo: recusado;
- `HOSTSW_OWN` não concedido: recusado;
- pad fora de GPIO mode ou RX disabled: recusado;
- GPI_IE preexistente que não pertença ao Baken: recusado;
- nenhum fallback polling/synthetic IRQ.

`HOSTSW_OWN` não é escrito pelo backend inicial.

### 4. I2C-HID

`kernel/src/drivers/i2c_hid_manager.sotlas`

A ordem obrigatória torna-se:

`ACPI HID -> I2C device attach/activate -> logical GPIO CONFIGURED -> gpio_physical_arm_connection -> logical GPIO ACTIVE -> i2c_device_set_gpio -> HID descriptor -> power/reset -> IRQ reset ACK -> report descriptor -> input registration`

Rollback faz teardown de input primeiro e depois tenta disarm físico + unregister lógico antes de destacar o I2C target. Se o teardown físico falhar, o target não é destacado, evitando IRQ direcionado a uma geração já destruída.

### 5. IRQ x86-64

`kernel/src/interrupts/irq.sotlas`

- vector `0x46` reservado para GPIO físico;
- gate instalado no IDT;
- dispatcher chama `gpio_physical_irq_dispatch()`, não Tiger Lake diretamente;
- contador `IRQ_GPIO_COUNT` contabiliza sinais tratados;
- LAPIC EOI permanece no dispatcher x86-64.

No backend Tiger Lake, cada entrada armada valida:

`pending = GPI_IS & GPI_IE & armed_bit`

Quando `pending != 0`, a ISR chama `gpio_connection_signal(connection_id)` e limpa o status com W1C.

## Regra de independência

Esta etapa não introduz Linux, Unix, BSD, Windows, Darwin/XNU ou qualquer outro SO como dependência. O backend é código do Baken executando diretamente sobre ACPI/MMIO/IOAPIC/LAPIC já implementados no próprio kernel. Não há HAL, runtime ou driver de terceiros no caminho.

## Estado de certificação

**Implementação de software: pronta para gates.**

Ainda não marcar GPIO-PHYS-0 como certificado em hardware apenas pela presença do código. Certificação requer resultados verdes de CI e, para a afirmação de suporte físico Tiger Lake, execução em máquina compatível.

## Teste de contrato novo

`tests/test_intel_tigerlake_gpio_contract.py`

Cobre:

- neutralidade do core;
- `CONFIGURED -> ACTIVE` somente via arm físico;
- dispatcher vendor-neutral;
- IDs Tiger Lake suportados;
- `_CRS` estático, FixedMemory32 e ExtendedIRQ;
- MMIO real;
- REVID/PADBAR/stride;
- PAD_OWN/locks/HOSTSW_OWN;
- PADCFG0 GPIO RX + IOxAPIC;
- `GPI_IS/GPI_IE` e `gpio_connection_signal()`;
- vector 0x46;
- ordenação I2C-HID;
- ausência de dependência de código/runtime de outro SO.

## Próximo handoff recomendado

Se todos os gates permanecerem verdes, o próximo estágio deve preservar esta separação e avançar como `GPIO-PHYS-1`, priorizando evaluator ACPI necessário para `_CRS` dinâmico e certificação física. Expansões AMD e outras famílias devem entrar por backend próprio, nunca por condicionais de fabricante dentro de `gpio_core`.

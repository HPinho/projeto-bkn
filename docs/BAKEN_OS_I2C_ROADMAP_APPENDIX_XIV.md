# Baken OS — I2C Roadmap Appendix XIV — GPIO-PHYS-0

> Este apêndice é aditivo. Os apêndices I–XIII permanecem inalterados.

## Estado

GPIO-PHYS-0 implementa a primeira ponte de interrupção GPIO física usada pelo HID-over-I2C. A implementação de software é considerada **pronta para certificação**, mas a certificação final depende dos gates de CI/QEMU e de validação em hardware compatível.

## Regra arquitetural

O GPIO do Baken permanece **agnóstico de fabricante**. `gpio_core.sotlas` mantém apenas identidade, lifecycle, polaridade, trigger, pending IRQ e ownership lógico. Nenhum detalhe Intel, AMD, Qualcomm, MediaTek, NVIDIA/Tegra ou de qualquer outro fabricante pertence ao core.

A nova camada `gpio_physical.sotlas` é o ponto de despacho para backends físicos separados. O primeiro backend é `intel_tigerlake_gpio.sotlas`; backends futuros serão adicionados como módulos independentes sem alterar consumidores como HID-over-I2C.

Estrutura alvo:

`ACPI/firmware description -> gpio_core CONFIGURED -> gpio_physical -> backend de silício -> pad/IRQ real -> gpio_core ACTIVE -> consumidor`

## Backend inicial: Intel Tiger Lake

Escopo inicial fail-closed:

- Tiger Lake-LP: ACPI `INT34C5` e `INTC1055`;
- Tiger Lake-H: ACPI `INT34C6`;
- `_CRS` estático apenas; `_CRS` dependente de evaluator continua recusado nesta etapa;
- regiões MMIO provenientes exclusivamente do `_CRS` do próprio controlador;
- GSI proveniente exclusivamente do Extended Interrupt Descriptor do `_CRS`;
- PADBAR lido do hardware;
- stride de PADCFG derivado em runtime da revisão do controlador;
- tradução explícita ACPI GPIO number -> community/GPP/pad;
- ranges sem mapeamento GPIO válido são recusados;
- `PAD_OWN`, `PADCFGLOCK`, `PADCFGLOCKTX` e `HOSTSW_OWN` são validados antes de qualquer arm;
- `HOSTSW_OWN` é somente leitura nesta etapa: o Baken não toma ownership do firmware à força;
- somente pads já configurados em modo GPIO e com RX habilitado são elegíveis;
- `PADCFG0` altera apenas rota/trigger/polaridade necessária ao IRQ e é restaurado no disarm;
- `GPI_IS` e `GPI_IE` são MMIO reais, sem IRQ sintético;
- bits `GPI_IE` não pertencentes ao Baken causam recusa fail-closed;
- GSI é programado no IOAPIC inicialmente mascarado e só é liberado após pad + logical connection estarem armados;
- vector x86-64 dedicado: `0x46`;
- ISR: `GPI_IS & GPI_IE & armed_bit -> gpio_connection_signal()` -> W1C do status.

## Lifecycle lógico corrigido

Antes de GPIO-PHYS-0, `gpio_connection_register_from_acpi()` publicava a conexão como ACTIVE cedo demais. Agora:

1. o recurso ACPI é validado e registrado como `CONFIGURED`;
2. a camada física seleciona um backend proprietário do namespace do controlador;
3. o backend valida MMIO, pad, ownership, locks e IRQ;
4. somente após o arm físico bem-sucedido `gpio_connection_activate()` promove para `ACTIVE`;
5. teardown físico executa `gpio_connection_deactivate()` antes de `gpio_connection_unregister()`;
6. unregister recusa conexão `ACTIVE` ou `MASKED`.

Isso impede que HID ou qualquer consumidor interprete uma descrição ACPI como hardware operacional antes de existir um caminho físico real.

## Independência de terceiros

GPIO-PHYS-0 não adiciona dependência de Linux, Unix, BSD, Windows, Darwin/XNU ou qualquer outro sistema operacional. O código do Baken permanece próprio e bare-metal. Especificações de hardware/firmware podem ser usadas como documentação técnica, mas nenhum runtime, HAL, driver ou código-fonte de outro SO faz parte da implementação.

## Expansão multi-plataforma

Tiger Lake é somente o primeiro backend, não a arquitetura GPIO definitiva. A extensão planejada permanece separada por família/plataforma, por exemplo:

- Intel: backends adicionais por geração quando diferenças de register map exigirem;
- AMD x86-64: backend(s) GPIO/SoC próprios;
- ARM genérico: integração conforme controlador/plataforma e GIC;
- Qualcomm Snapdragon: backend GPIO/TLMM específico;
- MediaTek: backend GPIO/EINT específico;
- NVIDIA Tegra/Jetson: backend GPIO específico do SoC.

Nenhum desses backends deverá alterar a API lógica do `gpio_core`.

## Gates de certificação

Software/contract gates esperados para esta etapa:

- contratos Python existentes do kernel continuam verdes;
- novo contrato `test_intel_tigerlake_gpio_contract.py` valida separação core/backend, lifecycle, ACPI/MMIO real, pad ownership, IRQ real e ausência de fallback sintético;
- build/lowering Sotlas completo;
- CI/QEMU principal;
- SMP bring-up e SMP fault diagnostics;
- NVMe-only gate;
- HID dual-device gate.

Validação física posterior deve confirmar em Tiger Lake suportado: descoberta do controlador, arm do pad, entrega do GSI, incremento do contador GPIO, reset handshake I2C-HID e teardown/restauração do pad.

## Próximas etapas

Depois da certificação de GPIO-PHYS-0:

1. GPIO-PHYS-1 — ampliar cobertura ACPI onde `_CRS` exigir evaluator, sem relaxar fail-closed;
2. certificação em hardware Tiger Lake real;
3. expansão Intel por geração em módulos separados;
4. primeiro backend AMD x86-64;
5. quando a arquitetura ARM do Baken avançar, backends SoC/GIC separados para Qualcomm, MediaTek, NVIDIA/Tegra e demais plataformas;
6. continuar HID/touchpad e demais dispositivos consumindo somente a API genérica GPIO.

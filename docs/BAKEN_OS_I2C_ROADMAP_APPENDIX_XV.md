# Baken OS — I2C Roadmap Appendix XV — GPIO-PHYS-1 / AMD x86-64

> Apêndice aditivo. Os apêndices anteriores permanecem como histórico.

## Estado

Este estágio integra `_CRS` dinâmico ao consumo de recursos físicos e adiciona
um backend GPIO AMD x86-64 separado para `AMDI0030` e `AMDIF031`.

**Software implementado; certificação em CI e hardware AMD ainda pendente.**

## `_CRS` dinâmico

`aml_dynamic_discovery` já avaliava métodos `_CRS`, mas os backends físicos só
consumiam a tabela estática de `aml_discovery`. A nova camada
`aml_runtime_resources.sotlas` fornece uma visão única:

- `Name(_CRS, ResourceTemplate(...))` usa os descritores estáticos existentes;
- `Method(_CRS) -> Buffer(ResourceTemplate)` usa o resultado validado do evaluator;
- parsing bounded de Small/Large Resource, overflow checks e EndTag obrigatório;
- associação preservada por `device_slot` e `namespace_index`;
- nenhum endereço ou IRQ é fabricado quando avaliação ou formato falha.

O backend Tiger Lake passa a consumir essa visão e também aceita `_HID` resolvido
pelo evaluator, mantendo todas as verificações de ownership, lock e register map.

## Backend AMD

Alvo inicial comprovado na plataforma de desenvolvimento:

- AMD Ryzen 7 7700X;
- ASUS TUF GAMING B650M-PLUS;
- controladores ACPI `AMDI0030` e `AMDIF031`;
- controlador I2C ACPI `AMDI0010` já coberto pelo subsistema I2C separado.

O backend `amd_gpio.sotlas`:

- reconhece somente `AMDI0030` e `AMDIF031`;
- obtém MMIO e GSI exclusivamente do `_CRS` runtime validado;
- aceita Memory32Fixed e IRQ/ExtendedIRQ ACPI bounded;
- mapeia MMIO UC pela arena ativa de page tables;
- recusa pin fora de faixa, região inválida, pin em output ou IRQ já habilitado;
- programa trigger/polaridade, enable/unmask e status por registrador de pin;
- entrega IRQ real via `gpio_connection_signal()`;
- emite EOI no bloco GPIO e mantém EOI LAPIC no dispatcher comum;
- usa lifecycle generation-safe e restaura o registrador original no teardown;
- mascara a rota IOAPIC quando a última conexão é removida.

Não existe endereço fixo, polling que imite IRQ nem marcador sintético de sucesso.

## Limite multi-arquitetura

Qualcomm, MediaTek e NVIDIA/Tegra são plataformas ARM/ARM64 e não podem receber
backends físicos funcionais enquanto o Baken ainda for exclusivamente x86-64.
Esses backends dependem primeiro de boot ARM64, MMU ARM, GIC, timer, device tree ou
ACPI ARM e primitivas MMIO/IRQ específicas. Adicionar nomes vazios agora produziria
suporte fictício e violaria a política fail-closed.

Outras gerações Intel também permanecem separadas: um novo ID somente será aceito
com register map, communities, pad ownership e tradução GPIO confirmados para a
geração. O backend Tiger Lake não é tratado como universal.

## Gates

- validação local em 2026-09-14: 1857 testes Python aprovados;
- build nativo: 188 módulos, 190 objetos, lowering e link aprovados;
- smoke integrado SATA/FAT32/memória/IRQ/NVMe/PAT aprovado;
- QEMU SMP: 3/3 boots independentes aprovados;
- contratos ACPI runtime resources;
- contratos AMD GPIO e Tiger Lake atualizado;
- suíte Python completa;
- build/lowering/link nativo;
- CI principal, SMP, SMP fault diagnostic, NVMe-only e HID dual-device pendentes
  no commit publicado;
- validação posterior em hardware AMD para afirmar suporte físico.

## Próximo corte

Após os gates do commit fecharem verdes, executar a imagem em uma máquina AMD
compatível e registrar discovery, arm, IRQ, RESET I2C-HID e relatório de entrada.
Em paralelo, a expansão Intel deve ser feita geração por geração. A trilha ARM64
começa pela arquitetura base, não por drivers GPIO isolados.

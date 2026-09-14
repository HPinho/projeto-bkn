# Baken OS — Kernel I2C Handoff Appendix XV

## Entrega

GPIO-PHYS-1 adiciona duas unidades nativas ao grafo Sotlas:

- `kernel::acpi::aml_runtime_resources` — visão bounded de recursos `_CRS`
  estáticos ou produzidos pelo evaluator;
- `kernel::drivers::amd_gpio` — backend físico x86-64 para `AMDI0030` e
  `AMDIF031`.

O dispatcher `gpio_physical` continua vendor-neutral e tenta backends isolados.
Consumidores como I2C-HID permanecem dependentes somente da API do `gpio_core`.

## Invariantes que devem ser preservados

1. Resultado dinâmico só é consumido quando `crs_resolved`, buffer, comprimento,
   namespace e EndTag são válidos.
2. Backends nunca inventam MMIO/GSI nem promovem conexão para ACTIVE antes do arm.
3. AMD não toma pin com IRQ preexistente nem pin configurado como output.
4. Falha depois de programação restaura registrador, lifecycle e rota.
5. IRQ somente sinaliza conexão generation-safe armada e com status físico.
6. A mesma IDT vector `0x46` pode agregar backends; cada um reconhece somente seus
   próprios controladores/conexões e o dispatcher LAPIC emite o EOI final.
7. `AMDI0010` é I2C, não GPIO; permanece no caminho I2C físico existente.

## Evidência da plataforma de desenvolvimento

Inventário Windows lido antes da implementação:

- CPU: `AMD Ryzen 7 7700X 8-Core Processor`;
- placa: `ASUSTeK TUF GAMING B650M-PLUS`;
- GPIO: `ACPI\\AMDI0030` e `ACPI\\AMDIF031`;
- I2C: `ACPI\\AMDI0010`.

Isso comprova os IDs presentes, mas não substitui boot do Baken e captura de IRQ
na máquina física. CI/QEMU também não emula esses blocos AMD.

## Validação local

- 1857 testes Python aprovados;
- 24 contratos direcionados ACPI/AMD/Tiger Lake aprovados após o ajuste final;
- build nativo aprovado: 188 módulos e 190 objetos;
- smoke integrado de fundação/storage aprovado;
- 3/3 boots SMP independentes aprovados;
- `git diff --check` sem erro (somente avisos de normalização LF/CRLF).

## Referências técnicas

- ACPI 6.6: `_CRS` retorna Buffer de Resource Descriptors e Small/Large Resource
  seguem o encoding padronizado;
- mapa público do driver AMD GPIO do kernel Linux: registradores de pin, bits de
  trigger/polaridade/enable/mask/status, status agrupado e EOI do controlador.

Nenhum runtime, HAL ou código de outro sistema operacional é incorporado ao Baken.

## Trabalho posterior

- provar o caminho na B650 física e ajustar somente com evidência serial/hardware;
- adicionar famílias Intel com mapas próprios;
- iniciar uma fundação ARM64/GIC antes de Qualcomm/MediaTek/Tegra;
- não declarar certificação física apenas a partir dos contratos ou do QEMU.

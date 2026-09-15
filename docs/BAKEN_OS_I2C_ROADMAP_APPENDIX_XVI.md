# Apêndice XVI — catálogo universal de silício I²C/GPIO

## Implementado

- Catálogo I²C versionado por ID PCI/ACPI, família, clock, política de acesso e
  intervalo de revisão do componente.
- Detecção em MMIO de `DW_IC_COMP_TYPE` e `DW_IC_COMP_VERSION` antes de
  inicializar o bloco DesignWare.
- Intel Serial IO/LPSS selecionado pelo controlador, cobrindo as famílias já
  enumeradas no catálogo até Alder/Raptor/Meteor/Lunar Lake, sem depender da CPU.
- AMD `AMD0010`, `AMDI0010` e Hygon `HYGO0010` via `_CRS` estático ou dinâmico,
  com clocks de 133/150 MHz e publicação no registry universal.
- `AMDI0019` reconhecido como barramento compartilhado com PSP e recusado antes
  do primeiro acesso MMIO enquanto não houver protocolo de posse comprovado.
- Catálogo GPIO Intel separando Tiger, Alder, Raptor, Meteor e Lunar Lake. Apenas
  Tiger usa as communities estáticas existentes; gerações posteriores precisam
  de descrição completa do firmware ou mapa homologado próprio.
- Fixtures ACPI sintéticas com proveniência explícita e matriz comunitária para
  registrar evidência física sem transformar expectativa em compatibilidade.

## Ainda depende de hardware/documentação

- Capturas DSDT/SSDT reais e sanitizadas de máquinas Alder, Raptor, Meteor,
  Lunar Lake e múltiplas gerações AMD.
- Tabelas completas de communities GPIO por variante de PCH quando o firmware
  não fornecer propriedades suficientes.
- Handshake PSP para `AMDI0019`; não será simulado nem contornado.
- Testes físicos de interrupção GPIO, RESET, touchpad e arbitragem concorrente.

Esses itens não podem receber selo de validação física por software local ou
QEMU. O comportamento atual para qualquer lacuna é continuar o boot sem anexar
o controlador, preservando o core universal e evitando escritas especulativas.

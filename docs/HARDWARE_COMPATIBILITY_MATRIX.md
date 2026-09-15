# Baken OS — matriz comunitária de hardware

Esta matriz diferencia suporte arquitetural, prova automatizada e validação física.
Uma família reconhecida não é automaticamente autorizada a receber escritas MMIO.

| Família | Subsistema | Estado no código | QEMU/contrato | Hardware físico |
|---|---|---|---|---|
| Intel Tiger Lake LP/H | GPIO | backend e communities estáticas | sim | pendente |
| Intel Alder/Raptor/Meteor/Lunar Lake | GPIO | catálogo separado; exige layout completo de firmware ou mapa homologado | fail-closed | pendente |
| Intel LPSS BXT/SPT/CNL/EHL e IDs catalogados posteriores | I²C | PCI + ACPI + assinatura/revisão DesignWare | sim | pendente |
| AMD `AMD0010` | I²C DesignWare 133 MHz | backend ACPI `_CRS` | contrato sintético | pendente |
| AMD/Hygon `AMDI0010`/`HYGO0010` | I²C DesignWare 150 MHz | backend ACPI `_CRS` | contrato sintético | pendente |
| AMD `AMDI0019` | I²C compartilhado com PSP | política ACQUIRE/RELEASE criada; transporte PSP ainda fail-closed | sim | bloqueado até handshake PSP |
| AMD `AMDI0030`/`AMDIF031` | GPIO | backend ACPI `_CRS` | sim | pendente |
| ID/revisão desconhecida | qualquer | não suportado com recusa segura | sim | não aplicável |

## Formato de contribuição física

Cada contribuição deve informar fabricante/modelo, CPU/PCH, IDs ACPI e PCI,
revisão do controlador, hash das tabelas ACPI, log serial completo, dispositivo
testado e resultado. Dumps devem remover serial, UUID e outros identificadores.
Fixtures sintéticas permanecem marcadas como `captured_from_hardware: false`;
somente uma captura reproduzível pode mudar esse campo para `true`.

O kernel emite uma linha `BAKEN:I2C=` por controlador observado. Os campos são
`origem:identidade:estado`, em hexadecimal; `estado` compacta família, motivo de
recusa e os 16 bits inferiores da revisão. `BAKEN:I2C_DIAG_READY` encerra o
relatório. Isso permite anexar o trecho serial sem expor UUID ou número de série.

## Política universal

O core trabalha com capacidades e interfaces neutras. Módulos de família traduzem
firmware e silício para essas interfaces. CPUID nunca autoriza acesso a registrador;
ID do controlador, recursos ACPI, assinatura, revisão e política de arbitragem devem
ser validados antes da primeira escrita.

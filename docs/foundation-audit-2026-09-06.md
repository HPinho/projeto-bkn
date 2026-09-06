# Auditoria das fundações bare-metal — 2026-09-06

Este documento registra o estado técnico auditado antes da nova rodada de QEMU. O critério continua sendo: um gate de hardware só é considerado concluído depois de prova real no CI/QEMU; presença de código ou teste estático não basta.

## Baseline comprovado

O CI #735 foi a última execução verde antes da expansão recente das fundações. Ele comprovou a cadeia pós-cutover existente até AHCI, Block Device, GPT, FAT32, diretório raiz, leitura de arquivo e marcador final J. A expansão posterior adicionou VMM/DMA dinâmicos, IRQ externo diagnosticável, Protective MBR, path FAT32/LFN, NVMe independente e PAT/WC.

## Regressão encontrada na auditoria

O CI #740 chegou até `STEP=a` e parou. A causa é determinística: com AHCI e NVMe presentes simultaneamente, `storage_discovery_scan()` aceitava o primeiro controlador PCI compatível. Após a inclusão do dispositivo NVMe na topologia do QEMU, o NVMe podia ser escolhido antes do AHCI. O probe MMIO publicava `a`, mas o caminho GPT/FAT seguinte dependia de uma Block Device já registrada pelo caminho AHCI.

A correção exige separar dois conceitos: descoberta genérica de controladores e seleção do dispositivo de boot/sistema. No pós-cutover atual, o caminho de sistema seleciona AHCI, que é o backend já comprovado para GPT/FAT; o NVMe permanece um gate independente e é exercitado depois, sem depender da ordem PCI.

## Riscos preventivos corrigidos nesta rodada

A alocação DMA com máscara de endereço não deve reservar uma página arbitrária e só depois rejeitá-la. Isso falha desnecessariamente em máquinas que possuem regiões convencionais acima e abaixo do limite de um dispositivo de 32 bits. O PMM passa a oferecer alocação alinhada com `max_address` e `boundary` aplicados antes da reserva, e o DMA usa essa operação diretamente. Falhas de conversão para direct-map também precisam desfazer a última reserva LIFO para não vazar páginas do bootstrap.

## Estado dos gates

- Cutover, CR3, GDT/TSS/IDT, PMM, VMM, ACPI, LAPIC/IOAPIC, timer, teclado e xHCI: comprovados em QEMU na baseline e novamente alcançados pelo #740 até o início de storage.
- AHCI, Block Device, GPT e FAT32: comprovados na baseline #735; a regressão de seleção multi-controlador da expansão recente precisa de nova prova após a correção.
- Protective MBR, path FAT32/LFN, IRQ externo adicional, novo probe VMM/DMA, NVMe e PAT/WC: implementados, mas ainda não devem ser marcados como concluídos até uma execução QEMU alcançar seus marcadores.
- DMA amplo: a limitação mais imediata de máscara/boundary foi corrigida; free-list arbitrária e políticas mais avançadas de IOMMU continuam fora desta fase de bootstrap.

## Guardrails

A CI deve manter AHCI e NVMe presentes ao mesmo tempo para impedir que a correção dependa da ordem de enumeração do QEMU. Testes estáticos verificam que o caminho de boot pós-cutover ignora NVMe antes de programar MMIO, exige Block Device AHCI pronta e mantém o NVMe como prova independente posterior.

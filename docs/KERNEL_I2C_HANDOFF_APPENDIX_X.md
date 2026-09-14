# Baken OS — Kernel I2C Handoff Appendix X

> Append-only. Preservar integralmente os handoffs e apêndices anteriores; este documento registra somente o fechamento I2C-5G.

## Contexto

O I2C-5F integrou o backend DesignWare/Intel LPSS ao runtime real. A auditoria posterior encontrou os últimos pontos que impediam considerar a fundação fisicamente fechada em hardware Intel real. O I2C-5G corrige esses pontos sem alterar a arquitetura base.

## Alterações do I2C-5G

### `kernel/src/drivers/i2c_designware.sotlas`
- `LPSS_PRIV_REMAP_ADDR = 0x40` e high dword em `0x44`.
- Remap LPSS escrito em 64 bits.
- `i2c_dw_speed_supported()` limita o backend físico certificado a 100/400 kHz.
- `I2cTransaction.bus_speed_hz` passa a selecionar fisicamente Standard/Fast Mode.
- `i2c_dw_enable_until()` compartilha o deadline absoluto da transação.
- Disable/enable necessários para TAR/10-bit/speed agora são obrigatoriamente verificados.
- Timings SS/FS permanecem pré-programados a partir do clock real da plataforma.

### `kernel/src/drivers/i2c_physical_discovery.sotlas`
- Allowlist Intel passa a ser derivada da tabela explícita de clocks homologados.
- Clocks conhecidos: 100/120/133/216 MHz conforme família.
- IDs sem clock conhecido falham fechado.
- Vínculo ACPI único é exigido **antes** de qualquer efeito PCI/MMIO.
- `_ADR` ambíguo é rejeitado.
- `PCI_COMMAND_MEMORY_SPACE` continua sendo o único command bit habilitado.
- Slot físico é revertido e hardware é desabilitado se publish/activate falhar.
- `discovered` representa somente controllers totalmente ativos.

### `kernel/src/drivers/i2c_controller_registry.sotlas`
Novo contrato:

`i2c_controller_registry_update_capabilities(controller_id, generation, capabilities)`

Só pode ser executado antes da publicação do backend e na mesma generation. O objetivo é substituir capabilities inferidas pelo ACPI pelas capabilities realmente certificadas do backend físico.

Capabilities DesignWare/LPSS deste corte:
- 7-bit: true;
- 10-bit: false até certificação dedicada;
- repeated START: true;
- max speed: 400 kHz;
- limites de mensagens/bytes: mesmos limites bounded do core I2C.

## Invariantes de segurança após o corte

1. Dispositivo PCI desconhecido nunca vira I2C por fallback.
2. Controller PCI sem namespace ACPI lógico válido não tem PCI command/MMIO alterado.
3. MMIO não mapeado nunca é acessado.
4. Silício que falha no init nunca é publicado.
5. Capabilities físicas são fixadas antes do backend ficar visível.
6. Publish e activate precisam retornar sucesso.
7. Falha de ativação revoga o backend lógico e remove o slot físico.
8. 10-bit não é anunciado ao executor.
9. Speed diferente de 100/400 kHz falha `UNSUPPORTED`.
10. Timeout cobre reconfiguração + transferência inteira.
11. Nenhum fallback sintético existe no caminho de produção.
12. Lock por controller continua SMP-safe sem manter IRQs globalmente desabilitadas durante o polling.

## Arquivos alterados neste fechamento

- `kernel/src/drivers/i2c_designware.sotlas`
- `kernel/src/drivers/i2c_physical_discovery.sotlas`
- `kernel/src/drivers/i2c_controller_registry.sotlas`
- `tests/test_i2c_designware.py`
- `tests/test_i2c_physical_discovery.py`
- `tests/test_i2c5_runtime_contract.py`
- `docs/BAKEN_OS_I2C_ROADMAP_APPENDIX_X.md`
- `docs/KERNEL_I2C_HANDOFF_APPENDIX_X.md`

## Gate de entrega

O commit I2C-5G deve ser considerado certificado quando os workflows canônicos do `main` permanecerem verdes, especialmente:
- CI/CD + QEMU smoke;
- SMP bring-up;
- SMP fault diagnostic;
- HID dual-device regression;
- NVMe-only bare-metal regression.

## Próximo ponto de entrada

Após o gate verde, não abrir outro estágio de fundação I2C. Seguir diretamente para **I2C-HID-0**:
1. localizar `PNP0C50` / `ACPI0C50`;
2. resolver o controller I2C generation-safe;
3. executar `_DSM` Function 1 com UUID HID-I2C;
4. obter o HID Descriptor Register;
5. ler o HID Descriptor pelo backend físico;
6. só então abrir IRQ GPIO/input report lifecycle.

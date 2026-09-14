# Baken OS — I2C Roadmap Appendix X

> Append-only. Este apêndice preserva integralmente os Apêndices I–IX e registra apenas o fechamento posterior da fundação física I2C.

## 2026-09-13 — I2C-5G: fechamento definitivo da fundação física

O I2C-5G fecha os últimos contratos encontrados na auditoria pós-I2C-5F antes da abertura da trilha HID-over-I2C.

### 1. Intel LPSS remap canônico
- `LPSS_PRIV_REMAP_ADDR` corrigido para `0x40` dentro da região privada `BAR0 + 0x200`.
- Remap passa a ser escrito como valor completo de 64 bits (`0x40` low dword + `0x44` high dword).
- `LPSS_PRIV_RESETS = 0x04`, `FUNC = 0x03`, `IDMA = bit 2` e `BOTH = 0x07` permanecem fail-closed.

### 2. Tabela de clock por família homologada
`i2c_physical_clock_for_device()` deixa de usar um fallback Intel genérico e passa a ser a própria allowlist do backend:
- SPT/KBL e TGL-LP homologados: 120 MHz.
- CNL/CML homologados: 216 MHz.
- EHL homologado: 100 MHz.
- APL/GLK/ICL e famílias baseadas em `bxt_i2c_info` homologadas: 133 MHz.
- DesignWare genérico homologado: 100 MHz.
- ID sem clock explicitamente conhecido: `0` → hardware `UNKNOWN` → não é tocado.

### 3. Velocidade física por transação
- Backend físico certifica explicitamente 100 kHz (Standard Mode) e 400 kHz (Fast Mode).
- `I2cTransaction.bus_speed_hz` passa a selecionar de fato os bits de speed de `IC_CON` sob o lock do controlador.
- Velocidades não certificadas falham com `I2C_STATUS_UNSUPPORTED`; nunca são arredondadas silenciosamente para 400 kHz.
- Timings SS/FS continuam calculados a partir do clock real da família.

### 4. Deadline único inclui reconfiguração
- `i2c_dw_enable_until()` recebe o mesmo `deadline_tsc` da transação.
- Disable → TAR/IC_CON → enable → TX/RX → drain compartilham o mesmo orçamento temporal.
- Falha em disable/enable durante uma transação retorna `I2C_STATUS_TIMEOUT` e não prossegue com registradores em estado indefinido.

### 5. Binding ACPI ↔ PCI completamente fail-closed
- O namespace ACPI é resolvido antes de habilitar `PCI_COMMAND_MEMORY_SPACE`, mapear MMIO, liberar reset LPSS ou escrever registradores.
- Apenas namespaces já existentes na `i2c_discovery_bridge` são elegíveis.
- `_ADR` duplicado/ambíguo no root bus é rejeitado.
- Controller PCI sem vínculo ACPI exato permanece intocado.

### 6. Capabilities físicas substituem inferências ACPI
Novo gate `i2c_controller_registry_update_capabilities()` permite atualizar capabilities somente enquanto o controller está:
- `ATTACHED`;
- na mesma `generation`;
- sem backend publicado.

O DesignWare físico publica:
- 7-bit: suportado;
- 10-bit: **não anunciado** até certificação específica de silício;
- repeated START: suportado;
- velocidade máxima certificada: 400 kHz.

Isso impede o executor de aceitar recursos que o backend físico ainda não certificou, mesmo que um recurso ACPI os anuncie.

### 7. Publicação/ativação transacional
- Retornos de `update_capabilities()`, `publish_backend()` e `activate()` são obrigatoriamente checados.
- Falha posterior à inicialização remove o slot físico, desabilita o DesignWare e, quando necessário, marca o controller lógico como `FAILED`.
- `discovered` só é incrementado depois de backend publicado e controller ativado com sucesso.

### 8. Testes endurecidos
Os testes I2C passam a bloquear regressões em:
- remap LPSS `0x40/0x44`;
- tabela de clocks 100/120/133/216 MHz;
- IDs Intel incorretos que antes podiam entrar na allowlist;
- binding ACPI antes de efeitos PCI/MMIO;
- capabilities físicas antes de publish/activate;
- rollback fail-closed;
- seleção real 100/400 kHz por transação;
- deadline compartilhado também durante enable/disable.

---

## Estado da trilha B2 após I2C-5G

| Etapa | Estado |
|---|---|
| I2C-0 — contratos base | ✅ |
| I2C-1 — transaction/executor/protocol | ✅ |
| I2C-2 — controller registry/discovery | ✅ |
| I2C-3 — GPIO/IRQ foundation | ✅ |
| I2C-4 — generic device model | ✅ |
| I2C-5 — physical DesignWare/LPSS backend | ✅ código concluído |
| I2C-5G — hardening final de clock/remap/speed/capabilities | ✅ implementado |
| Gate final | ⏳ workflows CI/QEMU do commit I2C-5G |
| I2C-HID-0 | 🔓 liberar após gate final verde |

### Próxima etapa após CI verde
**I2C-HID-0**: descoberta `PNP0C50`/`ACPI0C50`, `_DSM` Function 1, HID Descriptor e primeira leitura real pelo transporte I2C certificado.

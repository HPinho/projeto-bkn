# Baken OS — Trilha B2 / I2C Foundation Roadmap Appendix II

Continuação **append-only** de `BAKEN_OS_I2C_ROADMAP_APPENDIX.md`. O arquivo anterior permanece intocado; este apêndice assume como último candidato histórico o I2C-1c.

## 2026-09-13 — fechamento I2C-1c / protocol state machine + logical recovery

**✅ CERTIFICADO 4/4 — sem correction-only intermediário.**

```text
09f02d1daef40ef2b9b5e24d3445ae671c34e1b9
feat(i2c): add protocol state machine
```

Provas no mesmo SHA:

- CI #1218 ✅
- SMP #321 ✅
- NVMe-only #418 ✅
- HID Dual-device #77 ✅

Resultado certificado:

- state machine `START → ADDRESS → DATA → REPEATED_START → ... → STOP` pertence ao grafo Sotlas nativo real;
- eventos são action-scoped e progresso só avança após `OK`;
- leitura NACKa o último byte, fronteiras multi-message usam repeated START e o address-phase restart de leitura 10-bit permanece delegado ao backend;
- primeira causa de falha é preservada, recovery lógico ocorre no máximo uma vez e não existe retry/replay implícito;
- suíte completa, grafo modular, builds nativos, ISO e provas QEMU dos quatro gates permaneceram verdes;
- nenhum backend físico, MMIO, PCI, DMA, IRQ, GPIO ou mudança em LangSotlas foi introduzido.

---

## 2026-09-13 — I2C-1d / controller identity + ACPI binding contract

**⏳ CANDIDATO DESTE MICROCORTE — certificação depende de CI + SMP + NVMe-only + HID Dual-device no mesmo SHA.**

Contrato:

```text
AmlI2cAcpiBinding validada
        +
I2cControllerDescriptor
(controller_id + generation + ACPI node + capabilities + backend token)
        ↓
namespace/capability/address/speed gate
        ↓
I2cControllerBinding generation-safe
        ↓
execução somente se o mesmo descriptor/generation provar backend_ready
```

Escopo:

- `I2cControllerHandle` usa `controller_id + generation` e reserva zero como identidade inválida;
- `I2cControllerDescriptor` associa identidade lógica ao `acpi_namespace_index`, capabilities e um `backend_instance` opaco;
- `backend_ready=false` exige token zero; `backend_ready=true` exige token não zero;
- o descriptor não identifica DesignWare/Intel/AMD e não contém registradores;
- `i2c_controller_can_host_acpi` exige o mesmo namespace controller resolvido pelo ACPI, conexão controller-initiated, endereço válido e velocidade/capability compatíveis;
- `I2cControllerBinding` preserva resource/device/source index, endereço, velocidade e 7/10-bit junto da identidade generation-safe do controller;
- um binding lógico pode existir antes do backend físico ficar pronto, mas não é executável;
- `i2c_controller_binding_matches_descriptor` exige a mesma `controller_id`, `generation`, namespace e token/ready snapshot;
- troca de generation torna o binding antigo explicitamente stale;
- este estágio não possui registry global nem lifecycle: ownership de slots/attach/detach e avanço de generation continuam reservados ao I2C-2.

Invariantes:

- zero `static mut` e zero `SpinLock`;
- zero PCI discovery/mapping neste módulo;
- zero MMIO/PIO/DMA/IRQ/GPIO;
- zero timer/sleep/polling;
- zero execução AML;
- zero HID-I2C;
- zero backend físico ou suposição de silício;
- LangSotlas não deve ser alterado.

### Auditoria do controlador físico alvo

O PCI core atual já cataloga BDF/vendor/device/class/BAR de forma read-only, mas não há identificação específica de I2C/Serial-IO/LPSS nem backend DesignWare. O binding ACPI já fornece `controller_namespace_index`, porém o AML atual ainda não fornece um elo concreto e certificado ACPI→controller físico/PCI suficiente para selecionar silício com segurança.

Por isso o I2C-1d **não inventa** um backend. Se fechar 4/4, o próximo estágio entra em **I2C-2 — registry/lifecycle generation-safe + discovery/binding de controller**, onde o elo ACPI→instância concreta será estabelecido antes de qualquer acesso a registradores.

Qualquer gate vermelho congela `main` no SHA I2C-1d e exige correction-only antes de continuar.

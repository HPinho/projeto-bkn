# Baken OS — Trilha B2 / I2C Foundation Roadmap Appendix III

Continuação **append-only** de `BAKEN_OS_I2C_ROADMAP_APPENDIX_II.md`. Os apêndices anteriores permanecem intocados.

## 2026-09-13 — fechamento I2C-1d / controller identity + ACPI binding contract

**✅ CERTIFICADO 4/4 — sem correction-only intermediário.**

```text
7e21976b48839be98407ff8439c4424f5be7cd12
feat(i2c): add controller identity binding
```

Provas no mesmo SHA:

- CI #1219 ✅
- SMP #322 ✅
- NVMe-only #419 ✅
- HID Dual-device #78 ✅

Resultado certificado:

- `I2cControllerHandle` usa `controller_id + generation` como identidade autorizadora;
- `I2cControllerDescriptor` separa identidade firmware, capabilities e token opaco de backend;
- `I2cControllerBinding` preserva identidade da conexão ACPI e fica stale quando a generation muda;
- execução exige o mesmo descriptor/generation/backend snapshot e `backend_ready=true`;
- namespace, endereço, velocidade e suporte 7/10-bit são validados antes do binding;
- suíte completa, grafo modular, lowering/build nativo, ISO e provas QEMU permaneceram verdes;
- nenhum registry, MMIO, PCI mapping, DMA, IRQ, GPIO, HID-I2C ou mudança em LangSotlas foi introduzido.

---

## 2026-09-13 — I2C-2a / controller registry + lifecycle generation-safe

**⏳ CANDIDATO DESTE MICROCORTE — certificação depende de CI + SMP + NVMe-only + HID Dual-device no mesmo SHA.**

Contrato:

```text
ACPI controller node + I2cControllerCapabilities
        ↓ attach
slot bounded + controller_id + generation
        ↓
ATTACHED
        ↓ publish_backend (uma vez por generation)
ATTACHED + backend_ready
        ↓ activate
ACTIVE
        ↓ fail / detach
FAILED ou DETACHED
        ↓
backend token revogado + generation avançada no detach
```

Escopo:

- registry estático de 16 slots, sem heap;
- estados `EMPTY`, `ATTACHED`, `ACTIVE`, `FAILED`, `DETACHED`;
- `controller_id` deriva do slot e zero permanece reservado como identidade inválida;
- `generation` inicia em 1 e avança a cada detach antes da reutilização do slot;
- `attach` exige capabilities válidas e impede dois owners lógicos vivos para o mesmo `acpi_namespace_index`;
- `publish_backend` aceita um token opaco não zero somente em `ATTACHED`, apenas uma vez naquela generation;
- `activate` exige backend publicado e não zero;
- `FAILED` revoga imediatamente `backend_instance/backend_ready` sem mudar generation;
- `DETACHED` revoga backend, limpa namespace/capabilities, invalida o record e avança generation;
- snapshots generation-safe expõem `I2cControllerRecord` e `I2cControllerDescriptor` para o contrato I2C-1d;
- `handle_is_current` e `is_active` exigem identidade/generation atuais;
- contador de controllers ativos é mantido sob o mesmo lock.

### Concorrência

O registry usa `SpinLock` com `x86_irq_save_disable()` / `x86_irq_restore(flags)` em cada operação mutável ou snapshot. O valor salvo dos flags **não é usado como sentinela de falha**, então chamadas com IF já limpo continuam corretas e restauram exatamente o estado anterior.

### Fronteira deliberada

Este microcorte ainda não implementa:

- ACPI `_ADR` → PCI BDF mapping;
- discovery concreto Intel LPSS/Serial-IO, AMD ou DesignWare;
- registradores MMIO/PIO;
- DMA/IRQ/GPIO;
- execução de transações por hardware;
- reset físico de controller/bus;
- HID-I2C;
- política de hotplug físico.

Se I2C-2a fechar 4/4, o próximo corte será **I2C-2b — discovery bridge / ACPI namespace → controller instance**, ainda fail-closed e sem selecionar um backend de silício sem evidência concreta. Qualquer gate vermelho congela `main` e exige correction-only.

# Baken OS — Trilha B2 / I2C Kernel Handoff Appendix III

Continuação operacional **append-only** de `KERNEL_I2C_HANDOFF_APPENDIX_II.md`. Os handoffs anteriores permanecem intocados.

## Baseline certificada — 2026-09-13 / I2C-1d

```text
7e21976b48839be98407ff8439c4424f5be7cd12
feat(i2c): add controller identity binding
```

Gates no mesmo SHA:

- CI #1219 ✅
- SMP #322 ✅
- NVMe-only #419 ✅
- HID Dual-device #78 ✅

Essa baseline certifica a identidade stateless de controller, o binding ACPI generation-safe e a separação entre identidade lógica e token opaco de backend. Não houve correction-only nem alteração em LangSotlas.

## Candidato atual — I2C-2a / controller registry + lifecycle

Estado: **⏳ aguardando certificação 4/4 no novo SHA**.

Arquivos funcionais deste microcorte:

- `kernel/src/drivers/i2c_controller_registry.sotlas`
  - registry bounded de 16 slots sem heap;
  - estados `EMPTY/ATTACHED/ACTIVE/FAILED/DETACHED`;
  - ownership real de `controller_id + generation`;
  - attach por `acpi_namespace_index + I2cControllerCapabilities`;
  - impede owner lógico duplicado para o mesmo node ACPI;
  - backend token começa ausente e só pode ser publicado uma vez em `ATTACHED` por generation;
  - ativação exige backend pronto;
  - `FAILED` revoga backend e conserva generation para diagnóstico/teardown;
  - `DETACHED` revoga tudo e avança generation antes de liberar o slot;
  - snapshots generation-safe produzem record ou `I2cControllerDescriptor` compatível com I2C-1d;
  - expõe generation corrente por id, handle-current, active-state e active-count.
- `kernel/src/main.sotlas`
  - importa `i2c_controller_registry` imediatamente após `i2c_controller`.
- `tests/test_i2c_controller_registry.py`
  - guardrails de capacidade, lifecycle, generation, owner ACPI único, backend-once, fail revocation, detach e IRQ safety.
- `docs/BAKEN_OS_I2C_ROADMAP_APPENDIX_III.md`
  - registra o fechamento do I2C-1d e o contrato deste candidato.
- `docs/KERNEL_I2C_HANDOFF_APPENDIX_III.md`
  - este handoff operacional.

## Decisão de concorrência

Diferentemente do padrão antigo que podia tratar `flags == 0` como falha, este registry salva/desabilita IRQ e restaura os flags diretamente em cada operação. Portanto o lock continua utilizável quando a chamada já entra com interrupções desabilitadas; nenhum valor de RFLAGS é usado como sentinela.

## Fronteira deliberada

I2C-2a não faz discovery físico. Ainda não existe neste corte:

- `_ADR`/ACPI → PCI BDF;
- identificação LPSS/Serial-IO/DesignWare/AMD;
- BAR/MMIO/PIO;
- DMA/IRQ/GPIO;
- execução de hardware I2C;
- recovery elétrico;
- HID-I2C.

O token `backend_instance` continua opaco. O registry só controla ownership/lifecycle e impede reuso stale; quem cria o token físico será um estágio posterior depois da identificação concreta do controlador.

## Próximo passo somente após 4/4

**I2C-2b — discovery bridge / ACPI namespace → controller instance concreta**:

1. auditar quais identificadores ACPI/PCI já existem para o controller alvo;
2. adicionar bridge bounded e fail-closed sem hardcode de silício;
3. publicar no registry somente descriptors cuja identidade física possa ser comprovada;
4. manter backend específico bloqueado até vendor/device/interface evidenciarem qual implementação usar.

Se qualquer gate do I2C-2a falhar, congelar `main` no SHA reprovado, registrar run/step/causa e aplicar **somente correction-only** antes de continuar.

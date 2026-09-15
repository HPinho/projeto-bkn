# Baken OS — Hardware Portability Appendix

> Documento aditivo. Não substitui nem reescreve o histórico existente em `BAKEN_OS_ROADMAP.md` ou nos apêndices anteriores.

## 2026-09-15 — hardware físico ultrapassa SMP e expõe dependência indevida de COM1

Boot real alcançado:

```text
SMP APPLICATION PROCESSORS
BAKEN:SMP_BASE_READY
PROCESS ADDRESS SPACES
E-PROC-002
ADDRESS SPACE MARKER
```

A sequência prova que a fundação SMP já avançou além do antigo bloqueio e que `process_address_space_activate_foundation()`, readiness e self-test de isolamento passaram antes da falha do marcador. A causa do `E-PROC-002` foi separada do subsistema de paginação: a camada diagnóstica capturava o byte no boot log em RAM, mas tratava ausência/falha de COM1 como falha da operação.

### Baseline integrada

**✅ CERTIFICADO 4/4 e integrado na `main`.**

```text
9125cc564191b668761cf96a499518568a416213
fix: make UART optional for boot diagnostics
```

PR: `#25`

Gates do candidato que originou a integração:

- CI principal #1258 ✅
- SMP #361 ✅
- NVMe-only #458 ✅
- HID Dual-device #117 ✅

Contrato integrado:

- boot log em RAM é o sink autoritativo de diagnóstico;
- COM1/UART é espelho opcional best-effort;
- ausência de UART legado não pode produzir falha fatal de processo/FPU/userspace;
- `x86_serial_is_ready()` continua representando saúde do transporte físico;
- nenhuma exceção por fabricante/modelo foi adicionada.

---

## 2026-09-15 — hardening pós-integração: inicialização diagnóstica independente do transporte

Problema residual encontrado após a integração da PR #25:

`post_cutover` usa o retorno de `x86_serial_init()` para decidir se publica checkpoints iniciais. Mesmo com as escritas já tolerando ausência de UART, `x86_serial_init()` ainda retornava `false` quando COM1 não existia. Isso impedia que esses checkpoints fossem preservados no próprio boot log em RAM em hardware moderno.

Correção:

```text
x86_serial_init()
    ├─ falha apenas se a infraestrutura diagnóstica/lock não puder inicializar
    ├─ detecta COM1 separadamente
    ├─ X86_SERIAL_READY=true somente quando o UART é realmente utilizável
    └─ retorna true mesmo sem UART, mantendo o boot log operacional
```

Hardening adicional já incluído no candidato:

- scheduler diagnostics deixam de pré-condicionar captura em RAM a `x86_serial_is_ready()`;
- markers de sleep e wait queue permanecem registrados sem UART;
- wait-queue probe mantém seu checkpoint em RAM;
- marker de saída por exceção CPL3 permanece disponível no log de falha;
- novos guardrails impedem regressão desses contratos.

Nenhuma mudança de sintaxe, semântica ou lowering em LangSotlas foi necessária.

### Primeiro candidato do hardening

**❌ REPROVADO pelo gate CI principal; falha de guardrail textual, sem evidência de regressão funcional.**

```text
19563a3147e1535e2d8a25b0901e53364e26723d
```

Resultado observado:

- CI principal #1260 ❌ em `Run Complete Test Suite`;
- 1913 testes executados: 1912 passaram e 1 falhou;
- falha: `test_serial_markers_are_not_boot_prerequisites_without_com1`;
- causa: o teste exigia literalmente a antiga condição negativa `status == 0xFF || (status & 0x20) == 0`, enquanto a nova implementação usa a forma positiva equivalente para marcar o transporte como disponível e mantém o boot log ativo sem UART.

Correção-only aplicada no candidato seguinte:

- o guardrail agora valida a semântica: probe do Line Status Register, publicação de `X86_SERIAL_READY` somente para UART utilizável, `return true` da infraestrutura diagnóstica e ausência de retorno fatal por COM1 inexistente;
- nenhum comportamento funcional do kernel foi revertido;
- nenhum novo recurso foi empilhado sobre o gate vermelho.

### Próximo gate

O candidato corrigido só deve entrar na `main` se **CI principal + SMP + NVMe-only + HID Dual-device** fecharem verdes no mesmo SHA. Em seguida, o próximo boot físico deve verificar o avanço além de `E-PROC-002`, preservando no framebuffer/boot log os próximos checkpoints mesmo em máquina sem COM1 legado.

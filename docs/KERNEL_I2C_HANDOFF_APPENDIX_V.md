# Baken OS — Kernel I2C Handoff Appendix V

> Append-only. Este arquivo preserva integralmente o histórico anterior.

## Estado recebido

- Último SHA funcionalmente candidato a I2C-2a: `022bbec682d6ea5730c110919f21f044ffec8849`.
- Resultado: **3/4**, portanto não certificado.
  - CI #1220 ✅
  - SMP #323 ❌
  - NVMe-only #420 ✅
  - HID Dual-device #79 ✅
- Falha SMP observada após `BAKEN:SMP_THREAD_ON_AP` durante a prova do timer periódico no AP:
  - vector `0x0E` (#PF)
  - error code `0x00000000` (non-present, supervisor)
  - RIP baixo `0x10011BA5`
  - CS `0x08`
  - CPU slot `1`
  - scheduler thread id `0`

## Primeiro diagnóstico e falha de infraestrutura

O commit `521f1dcc3d3a3c31ef34ccddbb21cc5add2c8203` adicionou somente workflow/documentação de diagnóstico. O kernel Sotlas não foi alterado. O novo workflow falhou antes de criar job porque um heredoc Python ficou fora da indentação do bloco YAML. Registrar essa falha; não tratá-la como execução de kernel.

## Correction-only preparado

Publicar somente:

1. `.github/workflows/baken_smp_fault_diag.yml` corrigido, sem heredoc;
2. `tools/scripts/symbolize_pe_rip.py`;
3. este Appendix V;
4. `docs/BAKEN_OS_I2C_ROADMAP_APPENDIX_V.md`.

O workflow deve:

- compilar o mesmo grafo Sotlas;
- gerar `BOOTX64.symbols.txt` com `x86_64-w64-mingw32-nm -n`;
- rodar três boots SMP com `QEMU -d int`;
- parar na primeira exceção terminal ou sucesso total;
- extrair `BAKEN:HEX=i:<RIP>` da serial;
- resolver o símbolo mais próximo via `symbolize_pe_rip.py`;
- emitir disassembly ao redor do RIP;
- imprimir o trecho `v=0e` do log de interrupções do QEMU para obter CR2/contexto do #PF;
- subir serial, log `-d int`, símbolos e `BOOTX64.EFI` como artifacts.

## Regras para o próximo passo

- `main` fica congelada em correction-only.
- Não iniciar I2C-2b.
- Se o #PF reproduzir, usar CR2 + símbolo + disassembly para corrigir a causa mínima; não afrouxar o gate SMP.
- Se o diagnóstico não reproduzir, ainda exigir os quatro gates exact-SHA antes de liberar desenvolvimento funcional.
- A certificação só volta quando CI principal + SMP + NVMe-only + HID Dual-device estiverem verdes no mesmo SHA.

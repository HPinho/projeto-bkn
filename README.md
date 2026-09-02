# Baken OS

O Baken OS usa uma rota UEFI única para o desktop nativo. Consulte
[a arquitetura](docs/architecture.md) e execute `run_baken.ps1` para gerar e
iniciar a imagem local.

O escopo e os comandos de validação da versão inicial estão em
[docs/initial-release.md](docs/initial-release.md).

As correções de nitidez, double buffering, frame pacing e transições do
installer/OOBE estão documentadas em
[README_AUDITORIA_VISUAL.md](README_AUDITORIA_VISUAL.md).

A remoção da UI embutida no compilador e o lowering nativo dos módulos estão
documentados em [README-LOWERING-SOTLAS.md](README-LOWERING-SOTLAS.md).

A limpeza do código legado e os limites honestos desta etapa estão em
[docs/legacy-audit.md](docs/legacy-audit.md). A próxima ISO permanece adiada
até as integrações indicadas ali serem concluídas.

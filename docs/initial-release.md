# Baken OS — versão inicial (MVP)

## O que é entregue

- Rota de boot UEFI validada no QEMU em 27/08/2026, tanto pelo disco UEFI
  gravável quanto pela ISO óptica El Torito. VirtualBox continua sendo a
  próxima porta de validação antes de distribuir uma imagem mais ampla.
- Uma única rota de interface em execução: bootloader -> kernel gráfico ->
  desktop. A árvore Sotlas tem `kernel::main -> desktop_compositor` como rota
  canônica validada pelo sotlas compile.
- Desktop gráfico com wallpaper, topbar, dock e cursor. O dock abre os
  aplicativos conectados ao `window_manager` Sotlas.
- Prévia do assistente de instalação no mesmo tema do desktop; ela não grava
  discos nem avança para uma instalação concluída.
- O gerador de disco virtual cria GPT, ESP FAT32 e o marcador BakenFS em
  `build/`; a UI ainda não particiona discos físicos.
- Testes automatizados do grafo de módulos Sotlas, contratos de segurança e
  empacotamento. O boot em VM é executado separadamente antes de uma ISO.

## Como validar

```powershell
python -m unittest tests.test_sotlas_resolver
python tools/sotlas_compile/compiler.py check kernel/src/main.sotlas --manifest build/sotlas-main.manifest.json
./tools/build_uefi_desktop.ps1
python tools/scripts/create_fat32_img.py
python tools/test_qemu_desktop.py --install
```

## Limites conhecidos

Esta é uma versão inicial, não uma distribuição de produção. O registro
persistente ainda não é um BakenFS completo: arquivos de usuário, permissões,
diretórios e cópia do rootfs continuam sendo a próxima etapa. A ISO El Torito
é mídia óptica para VM, não uma imagem híbrida para pendrive. O Sotlas Compile
resolve, reduz e compila o grafo modular; a antiga ponte C foi removida.

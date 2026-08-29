# Rota de build canônica do Baken OS via VortexC.
# O VortexC resolve kernel::main, emite um objeto por módulo Cq e faz o link
# com o bootloader UEFI. A entrada pública e o desktop pertencem ao grafo Cq.

param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "..\build\iso_root\EFI\BOOT\BOOTX64.EFI")
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$toolchain = Join-Path $root "tools\w64devkit\bin"
$gcc = Join-Path $toolchain "gcc.exe"
$vortex = Join-Path $root "tools\vortexc\vortexc.py"
$entry = Join-Path $root "kernel\src\main.cq"
$font_packer = Join-Path $root "tools\scripts\generate_alpha_font.py"
$icon_packer = Join-Path $root "tools\scripts\generate_material_icons.py"
$app_icon_packer = Join-Path $root "tools\scripts\generate_baken_app_icons.py"
$motion_icon_packer = Join-Path $root "tools\scripts\generate_motion_icons.py"
$color_lut_packer = Join-Path $root "tools\scripts\generate_color_lut.py"
$icon_header = Join-Path $root "kernel\include\material_icons_atlas.h"
$app_icon_header = Join-Path $root "kernel\include\baken_app_icons_atlas.h"
$motion_icon_header = Join-Path $root "kernel\include\baken_motion_icons_atlas.h"
$resvg_runtime = Join-Path $root "build\tooling\resvg\node_modules\@resvg\resvg-js"

if (-not (Test-Path -LiteralPath $gcc)) {
    throw "Toolchain GCC nao encontrado: $gcc"
}
if (-not (Test-Path -LiteralPath $vortex) -or -not (Test-Path -LiteralPath $entry) -or -not (Test-Path -LiteralPath $font_packer) -or -not (Test-Path -LiteralPath $icon_packer) -or -not (Test-Path -LiteralPath $app_icon_packer) -or -not (Test-Path -LiteralPath $motion_icon_packer) -or -not (Test-Path -LiteralPath $color_lut_packer)) {
    throw "Backend VortexC, empacotador de ativos ou entrada kernel::main nao encontrados."
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
$env:PATH = "$toolchain;$env:PATH"

& python $font_packer
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o atlas local Inter." }
& python $color_lut_packer
if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar a LUT sRGB do compositor." }
if (Test-Path -LiteralPath $resvg_runtime) {
    & python $icon_packer
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o atlas local Material Symbols." }
    & python $app_icon_packer
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o atlas Phosphor dos aplicativos." }
    & python $motion_icon_packer
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o atlas Morphicons de movimento." }
} elseif (-not (Test-Path -LiteralPath $icon_header) -or -not (Test-Path -LiteralPath $app_icon_header) -or -not (Test-Path -LiteralPath $motion_icon_header)) {
    throw "Atlas Material/Phosphor/Morphicons ausente. Execute o empacotador de ativos no host."
} else {
    Write-Host "Usando atlas Material Symbols, Phosphor e Morphicons ja gerados." -ForegroundColor Yellow
}

& python $vortex build $entry '-o' $OutputPath '-m' (Join-Path $root 'build\cq-main.manifest.json')
if ($LASTEXITCODE -ne 0) { throw "Falha no build modular VortexC do BOOTX64.EFI." }

Write-Host "OK: EFI modular Cq vinculado em $OutputPath" -ForegroundColor Green

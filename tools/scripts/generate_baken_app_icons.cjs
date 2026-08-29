#!/usr/bin/env node
/*
 * Compila a familia visual dos aplicativos Baken OS para mascaras alpha.
 *
 * O kernel EFI deliberadamente nao interpreta SVG. O host rasteriza os
 * Ionicons preenchidos em tamanhos nativos e o compositor apenas amostra o atlas.
 * Isso preserva curvas, preenchimentos e opacidades em telas HiDPI.
 */
const fs = require('fs');
const path = require('path');
const { Resvg } = require(path.join(process.cwd(), 'build', 'tooling', 'resvg', 'node_modules', '@resvg', 'resvg-js'));
const { PNG } = require(path.join(process.cwd(), 'build', 'tooling', 'resvg', 'node_modules', 'pngjs'));

const root = process.cwd();
const source = path.join(root, 'assets', 'icons', 'ionicons.designerpack');
const output = path.join(root, 'kernel', 'include', 'baken_app_icons_atlas.h');
const sizes = [32, 48, 64, 96];

// A ordem e o contrato publico usado por desktop, dock e launcher.
const icons = [
  ['BAKEN_APP_FILES', 'folder.svg'],
  ['BAKEN_APP_STUDIO', 'cube.svg'],
  ['BAKEN_APP_BROWSER', 'globe.svg'],
  ['BAKEN_APP_PAINT', 'color-palette.svg'],
  ['BAKEN_APP_CAMERA', 'camera.svg'],
  ['BAKEN_APP_MEDIA', 'musical-notes.svg'],
  ['BAKEN_APP_NOTES', 'create.svg'],
  ['BAKEN_APP_EDITOR', 'document-text.svg'],
  ['BAKEN_APP_STORE', 'storefront.svg'],
  ['BAKEN_APP_TERMINAL', 'terminal.svg'],
  ['BAKEN_APP_SETTINGS', 'settings.svg'],
  ['BAKEN_APP_PERSONAL', 'folder-open.svg'],
  ['BAKEN_APP_CALENDAR', 'calendar.svg'],
  ['BAKEN_APP_PROFILE', 'person-circle.svg'],
  ['BAKEN_APP_SEARCH', 'search.svg'],
  ['BAKEN_APP_GALLERY', 'images.svg'],
];

for (const [, file] of icons) {
  const full = path.join(source, file);
  if (!fs.existsSync(full)) throw new Error(`Ionicons asset ausente: ${full}`);
}

const lines = [
  '#pragma once',
  '#include <stdint.h>',
  '',
  '/* Generated from Ionicons filled SVGs; MIT License. */',
  'typedef struct { uint8_t px; const uint8_t *alpha; } CqBakenAppIconAtlas;',
  'enum BakenAppIconId {',
  ...icons.map(([name], index) => `    ${name} = ${index},`),
  `    BAKEN_APP_ICON_COUNT = ${icons.length}`,
  '};',
  '',
];

for (const size of sizes) {
  const rows = icons.map(([, file]) => {
    const sourceSvg = fs.readFileSync(path.join(source, file), 'utf8');
    // Ionicons usa viewBox 512x512. O viewport quadrado mantem centro optico
    // e margem interna iguais em todos os tiles do Baken OS.
    let svg = sourceSvg;
    if (/<svg[^>]*\bwidth="[0-9.]+"/.test(svg)) svg = svg.replace(/width="[0-9.]+"/, `width="${size}"`);
    else svg = svg.replace('<svg ', `<svg width="${size}" `);
    if (/<svg[^>]*\bheight="[0-9.]+"/.test(svg)) svg = svg.replace(/height="[0-9.]+"/, `height="${size}"`);
    else svg = svg.replace('<svg ', `<svg height="${size}" `);
    const rendered = new Resvg(svg, {
      // A cor do SVG nao entra no atlas; somente a cobertura alpha e gravada.
      style: { color: '#ffffff' },
    }).render().asPng();
    const png = PNG.sync.read(rendered);
    if (png.width !== size || png.height !== size)
      throw new Error(`Dimensao inesperada em ${file}: ${png.width}x${png.height}, esperada ${size}x${size}`);
    const alpha = [];
    for (let i = 3; i < png.data.length; i += 4) alpha.push(png.data[i]);
    return alpha;
  });
  lines.push(`static const uint8_t baken_app_icons_${size}[${icons.length}][${size * size}] = {`);
  lines.push(...rows.map(row => `    {${row.join(',')}},`), '};', '');
}

lines.push(
  'static const CqBakenAppIconAtlas cq_baken_app_icon_atlases[] = {',
  ...sizes.map(size => `    {${size}, &baken_app_icons_${size}[0][0]},`),
  '};',
  `#define CQ_BAKEN_APP_ICON_ATLAS_COUNT ${sizes.length}`,
  ''
);

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, lines.join('\n'), 'ascii');
console.log(`[OK] ${icons.length} Ionicons filled -> ${output} (${sizes.join(', ')}px)`);

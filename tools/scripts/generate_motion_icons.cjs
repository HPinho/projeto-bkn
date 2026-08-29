#!/usr/bin/env node
/* Rasteriza os estados SVG selecionados dos pacotes Morphicons/Lottie. */
const fs = require('fs');
const path = require('path');
const { Resvg } = require(path.join(process.cwd(), 'build', 'tooling', 'resvg', 'node_modules', '@resvg', 'resvg-js'));
const { PNG } = require(path.join(process.cwd(), 'build', 'tooling', 'resvg', 'node_modules', 'pngjs'));

const root = process.cwd();
const source = path.join(root, 'build', 'tooling', 'baken-motion-src');
const output = path.join(root, 'kernel', 'include', 'baken_motion_icons_atlas.h');
const sizes = [24, 32, 48, 64];
const icons = [
  ['BAKEN_MOTION_PLAY', 'play-circle.svg'],
  ['BAKEN_MOTION_PAUSE', 'pause-circle.svg'],
  ['BAKEN_MOTION_SKIP_BACK', 'skip-back.svg'],
  ['BAKEN_MOTION_REFRESH', 'refresh.svg'],
  ['BAKEN_MOTION_SETTINGS', 'settings.svg'],
];

const lines = [
  '#pragma once', '#include <stdint.h>', '',
  '/* Generated from selected Morphicons/Lottie SVG states; MIT License. */',
  'typedef struct { uint8_t px; const uint8_t *alpha; } CqBakenMotionIconAtlas;',
  'enum BakenMotionIconId {',
  ...icons.map(([name], index) => `    ${name} = ${index},`),
  `    BAKEN_MOTION_ICON_COUNT = ${icons.length}`,
  '};', ''
];

for (const size of sizes) {
  const rows = icons.map(([, file]) => {
    const full = path.join(source, file);
    if (!fs.existsSync(full)) throw new Error(`Estado animado ausente: ${full}`);
    let svg = fs.readFileSync(full, 'utf8');
    if (/<svg[^>]*\bwidth="[0-9.]+"/.test(svg))
      svg = svg.replace(/width="[0-9.]+"/, `width="${size}"`);
    else
      svg = svg.replace('<svg ', `<svg width="${size}" `);
    if (/<svg[^>]*\bheight="[0-9.]+"/.test(svg))
      svg = svg.replace(/height="[0-9.]+"/, `height="${size}"`);
    else
      svg = svg.replace('<svg ', `<svg height="${size}" `);
    const png = PNG.sync.read(new Resvg(svg, { style: { color: '#ffffff' } }).render().asPng());
    if (png.width !== size || png.height !== size)
      throw new Error(`Dimensao inesperada em ${file}: ${png.width}x${png.height}`);
    const alpha = [];
    for (let i = 3; i < png.data.length; i += 4) alpha.push(png.data[i]);
    return alpha;
  });
  lines.push(`static const uint8_t baken_motion_icons_${size}[${icons.length}][${size * size}] = {`);
  lines.push(...rows.map(row => `    {${row.join(',')}},`), '};', '');
}

lines.push('static const CqBakenMotionIconAtlas cq_baken_motion_icon_atlases[] = {',
  ...sizes.map(size => `    {${size}, &baken_motion_icons_${size}[0][0]},`),
  '};', `#define CQ_BAKEN_MOTION_ICON_ATLAS_COUNT ${sizes.length}`, '');
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, lines.join('\n'), 'ascii');
console.log(`[OK] ${icons.length} estados Morphicons -> ${output} (${sizes.join(', ')}px)`);

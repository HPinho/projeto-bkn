#!/usr/bin/env node
/* Generates selected Ionicons filled alpha atlases for the EFI image. */
const fs = require('fs');
const path = require('path');
const { Resvg } = require(path.join(process.cwd(), 'build', 'tooling', 'resvg', 'node_modules', '@resvg', 'resvg-js'));
const { PNG } = require(path.join(process.cwd(), 'build', 'tooling', 'resvg', 'node_modules', 'pngjs'));
const root = process.cwd(), source = path.join(root, 'assets', 'icons', 'ionicons.designerpack');
const output = path.join(root, 'kernel', 'include', 'material_icons_atlas.h');
// Compatibilidade: os identificadores MATERIAL_* seguem estaveis, mas os
// pixels agora pertencem ao conjunto Ionicons escolhido para todo o sistema.
const sizes = [24, 32, 48, 64, 96];
const icons = [
  ['MATERIAL_BATTERY_FULL', 'battery-full.svg'], ['MATERIAL_CALENDAR_MONTH', 'calendar.svg'],
  ['MATERIAL_CAMERA_ALT', 'camera.svg'], ['MATERIAL_CLOSE', 'close.svg'], ['MATERIAL_CLOUD', 'cloud.svg'],
  ['MATERIAL_CROP_SQUARE', 'crop.svg'], ['MATERIAL_DESCRIPTION', 'document-text.svg'], ['MATERIAL_EDIT_NOTE', 'create.svg'],
  ['MATERIAL_FOLDER', 'folder.svg'], ['MATERIAL_FOLDER_OPEN', 'folder-open.svg'], ['MATERIAL_IMAGE', 'images.svg'],
  ['MATERIAL_MINIMIZE', 'remove.svg'], ['MATERIAL_MUSIC_NOTE', 'musical-note.svg'], ['MATERIAL_NOTIFICATIONS', 'notifications.svg'],
  ['MATERIAL_PALETTE', 'color-palette.svg'], ['MATERIAL_PAUSE', 'pause.svg'], ['MATERIAL_PERSON', 'person.svg'],
  ['MATERIAL_PLAY_ARROW', 'play.svg'], ['MATERIAL_PUBLIC', 'globe.svg'], ['MATERIAL_SEARCH', 'search.svg'],
  ['MATERIAL_SETTINGS', 'settings.svg'], ['MATERIAL_STOREFRONT', 'storefront.svg'], ['MATERIAL_SUNNY', 'sunny.svg'],
  ['MATERIAL_TERMINAL', 'terminal.svg'], ['MATERIAL_VIEW_IN_AR', 'cube.svg'], ['MATERIAL_VOLUME_UP', 'volume-high.svg'],
  ['MATERIAL_WIFI', 'wifi.svg'], ['MATERIAL_BATTERY_HALF', 'battery-half.svg'],
];
for (const [, name] of icons) if (!fs.existsSync(path.join(source, name))) throw new Error(`Ionicons asset ausente: ${name}`);
const lines = ['#pragma once', '#include <stdint.h>', '',
  '/* Compatibility names; generated from Ionicons filled SVGs, MIT License. */',
  'typedef struct { uint8_t px; const uint8_t *alpha; } CqMaterialIconAtlas;',
  'enum MaterialIconId {', ...icons.map(([name], i) => `    ${name} = ${i},`), `    MATERIAL_ICON_COUNT = ${icons.length}`, '};', ''];
for (const size of sizes) {
  const rows = icons.map(([, name]) => {
    const original = fs.readFileSync(path.join(source, name), 'utf8');
    const svg = original.replace(/width="[0-9.]+"/, `width="${size}"`).replace(/height="[0-9.]+"/, `height="${size}"`);
    const png = PNG.sync.read(new Resvg(svg, { fitTo: { mode: 'width', value: size } }).render().asPng());
    if (png.width !== size || png.height !== size) throw new Error(`Unexpected size: ${name}`);
    const alpha = []; for (let i = 3; i < png.data.length; i += 4) alpha.push(png.data[i]); return alpha;
  });
  lines.push(`static const uint8_t material_icons_${size}[${icons.length}][${size * size}] = {`);
  lines.push(...rows.map(row => `    {${row.join(',')}},`), '};', '');
}
lines.push('static const CqMaterialIconAtlas cq_material_icon_atlases[] = {', ...sizes.map(s => `    {${s}, &material_icons_${s}[0][0]},`), '};', `#define CQ_MATERIAL_ICON_ATLAS_COUNT ${sizes.length}`, '');
fs.mkdirSync(path.dirname(output), { recursive: true }); fs.writeFileSync(output, lines.join('\n'), 'ascii');
console.log(`[OK] ${icons.length} Ionicons filled -> ${output} (${sizes.join(', ')}px)`);

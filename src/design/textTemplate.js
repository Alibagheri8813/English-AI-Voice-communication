import fs from 'fs';
import path from 'path';
import slugify from 'slugify';
import { getPaths } from '../config.js';

export function createTextDesignAssets(phrase) {
	const slug = slugify(phrase, { lower: true, strict: true });
	const { ASSETS_DIR } = getPaths();
	const outDir = path.join(ASSETS_DIR, 'designs', slug);
	if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

	const svgContent = generateSVG(phrase);
	const svgPath = path.join(outDir, `${slug}.svg`);
	fs.writeFileSync(svgPath, svgContent, 'utf-8');

	return { slug, outDir, svgPath };
}

function generateSVG(phrase) {
	const sanitized = phrase.replace(/</g, '&lt;').replace(/>/g, '&gt;');
	return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="4500" height="5400" viewBox="0 0 4500 5400">
  <rect width="100%" height="100%" fill="#111111"/>
  <text x="50%" y="50%" fill="#ffffff" font-family="Arial, Helvetica, sans-serif" font-size="300" font-weight="700" text-anchor="middle" dominant-baseline="middle">
    ${sanitized}
  </text>
</svg>`;
}


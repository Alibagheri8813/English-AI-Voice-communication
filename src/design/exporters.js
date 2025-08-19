import fs from 'fs';
import path from 'path';
import { Resvg } from '@resvg/resvg-js';

export async function ensurePngExport(svgPath) {
	const svgContent = fs.readFileSync(svgPath, 'utf-8');
	const resvg = new Resvg(svgContent, {
		fitTo: { mode: 'width', value: 4500 },
		background: 'rgba(0,0,0,0)',
	});
	const pngData = resvg.render().asPng();
	const outPath = path.join(path.dirname(svgPath), `${path.basename(svgPath, '.svg')}.png`);
	fs.writeFileSync(outPath, pngData);
	return outPath;
}


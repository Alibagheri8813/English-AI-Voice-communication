import express from 'express';
import path from 'path';
import fs from 'fs';
import { ensureProjectDirsExist, getPaths, getEnv } from '../config.js';

ensureProjectDirsExist();
const app = express();
app.use(express.json());

const { ASSETS_DIR } = getPaths();

app.get('/', (_req, res) => {
	res.type('html').send(`
    <html>
      <head><title>Zero-cost MVP Store</title></head>
      <body style="font-family: sans-serif; padding: 24px;">
        <h1>Zero-cost MVP Store</h1>
        <p>Generated designs will appear below.</p>
        <ul>
          ${listDesigns()
				.map(
					(d) => `<li><a href="/designs/${d}/">${d}</a> - <a href="/designs/${d}/${d}.svg">SVG</a></li>`
				)
				.join('')}
        </ul>
      </body>
    </html>
  `);
});

app.get('/designs/:slug/', (req, res) => {
	const dir = path.join(ASSETS_DIR, 'designs', req.params.slug);
	if (!fs.existsSync(dir)) return res.status(404).send('Not found');
	const files = fs.readdirSync(dir);
	res.type('html').send(`
    <html>
      <body style="font-family: sans-serif; padding: 24px;">
        <h2>${req.params.slug}</h2>
        <div>
          ${files
				.map((f) => `<div><a href="/designs/${req.params.slug}/${f}">${f}</a></div>`)
				.join('')}
        </div>
      </body>
    </html>
  `);
});

app.get('/designs/:slug/:file', (req, res) => {
	const filePath = path.join(ASSETS_DIR, 'designs', req.params.slug, req.params.file);
	if (!fs.existsSync(filePath)) return res.status(404).send('Not found');
	res.sendFile(filePath);
});

const { port } = getEnv();
app.listen(port, () => {
	console.log(`Storefront running on http://localhost:${port}`);
});

function listDesigns() {
	const dir = path.join(ASSETS_DIR, 'designs');
	if (!fs.existsSync(dir)) return [];
	return fs
		.readdirSync(dir, { withFileTypes: true })
		.filter((d) => d.isDirectory())
		.map((d) => d.name)
		.sort();
}


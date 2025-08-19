import express from 'express';
import path from 'path';
import fs from 'fs';
import Stripe from 'stripe';
import { ensureProjectDirsExist, getPaths, getEnv } from '../config.js';
import crypto from 'crypto';
import { findCreatorByTwitch, upsertCreator, loadCreators } from '../db/filedb.js';

ensureProjectDirsExist();
const app = express();
app.use(express.json());

const { ASSETS_DIR } = getPaths();
const env = getEnv();
const stripe = env.stripeSecretKey ? new Stripe(env.stripeSecretKey, { apiVersion: '2024-06-20' }) : null;

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
					(d) => `<li><a href="/designs/${d}/">${d}</a> - <a href="/designs/${d}/${d}.svg">SVG</a> - <a href="/buy/${d}">Buy digital pack ($4.99)</a></li>`
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

// Minimal checkout for digital downloads using Stripe Checkout
app.get('/buy/:slug', async (req, res) => {
	try {
		if (!stripe) return res.status(500).send('Stripe not configured');
		const slug = req.params.slug;
		const creatorTwitch = String(req.query.creator || '').trim();
		const unitAmount = 499;
		const payload = {
			mode: 'payment',
			line_items: [
				{
					price_data: {
						currency: 'usd',
						unit_amount: unitAmount,
						product_data: {
							name: `Digital Pack: ${slug}`,
							description: 'SVG + PNG export + wallpaper',
						},
					},
					quantity: 1,
				},
			],
			success_url: `${env.siteUrl}/success?slug=${encodeURIComponent(slug)}&session_id={CHECKOUT_SESSION_ID}`,
			cancel_url: `${env.siteUrl}/designs/${encodeURIComponent(slug)}/`,
			metadata: { slug, creator_twitch: creatorTwitch },
		};
		if (creatorTwitch) {
			const creator = findCreatorByTwitch(creatorTwitch);
			if (creator && creator.stripeConnectId) {
				const platformFee = Math.round((unitAmount * (env.platformPercent || 30)) / 100);
				payload.payment_intent_data = {
					transfer_data: { destination: creator.stripeConnectId },
					application_fee_amount: platformFee,
				};
			}
		}
		const session = await stripe.checkout.sessions.create(payload);
		res.redirect(303, session.url);
	} catch (err) {
		console.error(err);
		res.status(500).send('Checkout error');
	}
});

app.get('/success', async (req, res) => {
	const slug = String(req.query.slug || '');
	const token = createDownloadToken(slug);
	res.type('html').send(`
	<html>
	  <body style="font-family: sans-serif; padding: 24px;">
		<h1>Thanks!</h1>
		<p>Your download for <b>${slug}</b> is below. Link expires in 7 days.</p>
		<ul>
		  ${listDesignFiles(slug)
				.map((f) => `<li><a href="/download/${slug}/${f}?t=${token}">${f}</a></li>`)
				.join('')}
		</ul>
	  </body>
	</html>`);
});

// Stripe webhook (dev: skip signature verification)
app.post('/webhooks/stripe', express.raw({ type: 'application/json' }), (req, res) => {
	try {
		if (!stripe) return res.status(200).send('ok');
		const event = JSON.parse(req.body.toString('utf-8'));
		if (event.type === 'checkout.session.completed') {
			const session = event.data.object;
			console.log('Stripe checkout completed', session.id);
		}
		res.status(200).send('ok');
	} catch (err) {
		console.error('Webhook error', err);
		res.status(400).send('invalid');
	}
});

// Creator onboarding with Stripe Connect Express
app.get('/onboard/:twitch', async (req, res) => {
	try {
		if (!stripe) return res.status(500).send('Stripe not configured');
		const twitch = String(req.params.twitch);
		const account = await stripe.accounts.create({ type: 'express' });
		upsertCreator({ twitch, stripeConnectId: account.id });
		const link = await stripe.accountLinks.create({
			account: account.id,
			refresh_url: `${env.siteUrl}/onboard/refresh?twitch=${encodeURIComponent(twitch)}`,
			return_url: `${env.siteUrl}/onboard/return?twitch=${encodeURIComponent(twitch)}&account=${encodeURIComponent(account.id)}`,
			type: 'account_onboarding',
		});
		res.redirect(303, link.url);
	} catch (err) {
		console.error(err);
		res.status(500).send('Onboarding error');
	}
});

app.get('/onboard/return', (req, res) => {
	const twitch = String(req.query.twitch || '');
	const account = String(req.query.account || '');
	res.type('html').send(`
	<html><body style="font-family: sans-serif; padding: 24px;">
	<h2>Onboarding complete</h2>
	<p>Twitch: ${twitch}</p>
	<p>Stripe Account: ${account}</p>
	<p>You can now sell with rev-share using ?creator=${twitch} on /buy links.</p>
	</body></html>`);
});

app.get('/admin/creators', (_req, res) => {
	res.json(loadCreators());
});

export function startStorefront() {
	const { port } = getEnv();
	app.listen(port, () => {
		console.log(`Storefront running on http://localhost:${port}`);
	});
}

function listDesigns() {
	const dir = path.join(ASSETS_DIR, 'designs');
	if (!fs.existsSync(dir)) return [];
	return fs
		.readdirSync(dir, { withFileTypes: true })
		.filter((d) => d.isDirectory())
		.map((d) => d.name)
		.sort();
}

function listDesignFiles(slug) {
	const dir = path.join(ASSETS_DIR, 'designs', slug);
	if (!fs.existsSync(dir)) return [];
	return fs.readdirSync(dir).filter((f) => f.toLowerCase().endsWith('.svg'));
}

app.get('/download/:slug/:file', (req, res) => {
	const { slug, file } = req.params;
	const token = String(req.query.t || '');
	if (!verifyDownloadToken(slug, token)) return res.status(403).send('Expired or invalid');
	const filePath = path.join(ASSETS_DIR, 'designs', slug, file);
	if (!fs.existsSync(filePath)) return res.status(404).send('Not found');
	res.sendFile(filePath);
});

function createDownloadToken(slug) {
	const expires = Math.floor(Date.now() / 1000) + 7 * 24 * 3600;
	const payload = `${slug}.${expires}`;
	const sig = crypto
		.createHmac('sha256', env.downloadSecret)
		.update(payload)
		.digest('hex')
		.slice(0, 16);
	return `${payload}.${sig}`;
}

function verifyDownloadToken(slug, token) {
	const parts = String(token).split('.');
	if (parts.length !== 3) return false;
	const [slugPart, expStr, sig] = parts;
	if (slugPart !== slug) return false;
	const expires = Number(expStr);
	if (!Number.isFinite(expires) || expires < Math.floor(Date.now() / 1000)) return false;
	const payload = `${slug}.${expires}`;
	const expected = crypto
		.createHmac('sha256', env.downloadSecret)
		.update(payload)
		.digest('hex')
		.slice(0, 16);
	return expected === sig;
}
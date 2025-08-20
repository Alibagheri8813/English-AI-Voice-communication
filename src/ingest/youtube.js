import https from 'https';
import { parseStringPromise } from 'xml2js';
import dayjs from 'dayjs';

// Poll channel uploads via RSS (no API key required)
// https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID

export async function fetchChannelUploads(channelId) {
	const rssUrl = `https://www.youtube.com/feeds/videos.xml?channel_id=${encodeURIComponent(channelId)}`;
	const xml = await fetchText(rssUrl);
	const json = await parseStringPromise(xml, { explicitArray: false });
	const entries = json?.feed?.entry ? (Array.isArray(json.feed.entry) ? json.feed.entry : [json.feed.entry]) : [];
	return entries.map((e) => ({
		videoId: e['yt:videoId'],
		title: e.title,
		publishedAt: e.published,
		updatedAt: e.updated,
		link: e.link?.href,
	}));
}

export function filterNewVideosSince(entries, isoTime) {
	if (!isoTime) return entries;
	return entries.filter((e) => dayjs(e.publishedAt).isAfter(dayjs(isoTime)));
}

const DEFAULT_TIMEOUT_MS = 10000;
const DEFAULT_RETRIES = 3;

async function fetchText(url, options = {}) {
	const { retries = DEFAULT_RETRIES, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
	let lastError = null;
	for (let attempt = 1; attempt <= retries; attempt++) {
		try {
			return await requestOnce(url, timeoutMs);
		} catch (err) {
			lastError = err;
			if (attempt === retries) break;
			const backoffMs = Math.min(2000, 250 * attempt + Math.floor(Math.random() * 150));
			await delay(backoffMs);
		}
	}
	throw lastError || new Error('Unknown network error');
}

function requestOnce(url, timeoutMs) {
	return new Promise((resolve, reject) => {
		const req = https.get(
			url,
			{
				headers: {
					'User-Agent': 'Mozilla/5.0 (Node.js; +https://github.com) resvg-mvp',
					Accept: 'application/xml,text/xml;q=0.9,*/*;q=0.8',
				},
			},
			(res) => {
				if (res.statusCode && res.statusCode >= 400) {
					res.resume();
					return reject(new Error(`HTTP ${res.statusCode}`));
				}
				let data = '';
				res.on('data', (chunk) => (data += chunk));
				res.on('end', () => resolve(data));
				res.on('error', reject);
			}
		);
		req.on('error', reject);
		req.setTimeout(timeoutMs, () => {
			req.destroy(new Error('Request timeout'));
		});
	});
}

function delay(ms) {
	return new Promise((r) => setTimeout(r, ms));
}


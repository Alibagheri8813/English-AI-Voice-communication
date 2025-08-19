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

async function fetchText(url) {
	return new Promise((resolve, reject) => {
		https
			.get(url, (res) => {
				let data = '';
				res.on('data', (chunk) => (data += chunk));
				res.on('end', () => resolve(data));
			})
			.on('error', reject);
	});
}


import fs from 'fs';
import path from 'path';
import dayjs from 'dayjs';
import { getPaths } from '../config.js';
import { fetchChannelUploads, filterNewVideosSince } from '../ingest/youtube.js';
import { getYoutubeTranscript } from '../transcript/youtube.js';
import { extractTopPhrasesFromTranscriptItems } from '../nlp/phraseDetection.js';
import { createTextDesignAssets } from '../design/textTemplate.js';
import { ensurePngExport } from '../design/exporters.js';

export async function runIngestYoutubeJob(channelIds) {
	const { DATA_DIR } = getPaths();
	const statePath = path.join(DATA_DIR, 'youtube-state.json');
	const state = readJson(statePath, { channels: {} });

	for (const channelId of channelIds) {
		const lastChecked = state.channels[channelId]?.lastChecked;
		const entries = await fetchChannelUploads(channelId);
		const newVideos = filterNewVideosSince(entries, lastChecked);

		for (const video of newVideos) {
			const transcript = await getYoutubeTranscript(video.videoId);
			let phrases = [];
			if (transcript.length > 0) {
				phrases = extractTopPhrasesFromTranscriptItems(transcript, { maxPhrases: 3 });
			} else if (video.title) {
				phrases = [{ phrase: video.title }];
			}
			for (const p of phrases) {
				const assets = createTextDesignAssets(p.phrase);
				try { await ensurePngExport(assets.svgPath); } catch {}
			}
		}

		state.channels[channelId] = { lastChecked: dayjs().toISOString() };
	}

	writeJson(statePath, state);
}

function readJson(p, fallback) {
	try {
		return JSON.parse(fs.readFileSync(p, 'utf-8'));
	} catch {
		return fallback;
	}
}

function writeJson(p, data) {
	fs.mkdirSync(path.dirname(p), { recursive: true });
	fs.writeFileSync(p, JSON.stringify(data, null, 2));
}


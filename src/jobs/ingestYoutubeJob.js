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
		let entries = [];
		try {
			entries = await fetchChannelUploads(channelId);
		} catch (err) {
			console.error(`Failed to fetch uploads for channel ${channelId}:`, err?.message || err);
			continue;
		}
		const newVideos = filterNewVideosSince(entries, lastChecked);

		for (const video of newVideos) {
			let transcript = [];
			try {
				transcript = await getYoutubeTranscript(video.videoId);
			} catch (err) {
				transcript = [];
			}
			let phrases = [];
			if (transcript.length > 0) {
				phrases = extractTopPhrasesFromTranscriptItems(transcript, { maxPhrases: 3 });
			} else if (video.title) {
				phrases = [{ phrase: video.title }];
			}
			for (const p of phrases) {
				const assets = createTextDesignAssets(p.phrase);
				try {
					await ensurePngExport(assets.svgPath);
				} catch (err) {
					// Non-fatal export failure; continue other items
				}
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


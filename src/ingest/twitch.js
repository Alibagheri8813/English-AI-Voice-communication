import tmi from 'tmi.js';
import dayjs from 'dayjs';
import { createTextDesignAssets } from '../design/textTemplate.js';
import { ensurePngExport } from '../design/exporters.js';

// Simple Twitch chat watcher using anonymous connection (no token required)
// Heuristic heat scoring: message rate + unique senders + repeated ngrams

export function startTwitchWatcher(channels) {
	if (!Array.isArray(channels) || channels.length === 0) {
		console.log('No Twitch channels configured. Skipping Twitch watcher.');
		return Promise.resolve();
	}

	const client = new tmi.Client({
		options: { debug: false },
		connection: { secure: true, reconnect: true },
		channels: channels.map((c) => (c.startsWith('#') ? c : `#${c}`)),
	});

	const windowSeconds = 10;
	const messageWindow = [];
	const recentPhrases = new Map(); // phrase -> lastSeenTs

	client.on('message', (channel, userstate, message, self) => {
		if (self) return;
		const now = Date.now();
		messageWindow.push({ ts: now, user: userstate['display-name'] || userstate.username || 'anon', text: message });
		// Evict old
		while (messageWindow.length > 0 && now - messageWindow[0].ts > windowSeconds * 1000) {
			messageWindow.shift();
		}
		const heat = computeHeatScore(messageWindow);
		if (heat.score >= 100) {
			const phrases = extractRepeatedPhrases(messageWindow, 3);
			phrases.forEach((p) => {
				const last = recentPhrases.get(p);
				if (last && now - last < 5 * 60 * 1000) return; // cooldown 5 min per phrase
				recentPhrases.set(p, now);
				const assets = createTextDesignAssets(p);
				ensurePngExport(assets.svgPath).catch(() => {});
				console.log(`[${dayjs().format()}] Hot phrase detected on ${channel}:`, p);
			});
		}
	});

	client.on('connected', (_addr, _port) => {
		console.log('Twitch watcher connected');
	});
	client.on('disconnected', (reason) => {
		console.log('Twitch watcher disconnected:', reason);
	});

	return client.connect();
}

function computeHeatScore(windowMsgs) {
	const now = Date.now();
	const horizon = 10 * 1000;
	const recent = windowMsgs.filter((m) => now - m.ts <= horizon);
	const messagesPerSec = recent.length / 10;
	const uniqueUsers = new Set(recent.map((m) => m.user)).size;
	const ngramRepetition = extractRepeatedPhrases(recent, 1).length;
	const score = Math.round(messagesPerSec * 20 + uniqueUsers * 5 + ngramRepetition * 40);
	return { score, messagesPerSec, uniqueUsers, ngramRepetition };
}

function extractRepeatedPhrases(recent, max = 3) {
	const tokens = recent
		.map((m) => m.text.toLowerCase())
		.join(' ')
		.replace(/[^a-z0-9'\s]/g, ' ')
		.split(/\s+/)
		.filter(Boolean);
	const counts = new Map();
	for (let i = 0; i < tokens.length; i++) {
		for (let n = 2; n <= 4; n++) {
			if (i + n > tokens.length) break;
			const phrase = tokens.slice(i, i + n).join(' ');
			counts.set(phrase, (counts.get(phrase) || 0) + 1);
		}
	}
	return Array.from(counts.entries())
		.filter(([p, c]) => c >= 3 && p.length >= 6 && p.length <= 60)
		.sort((a, b) => b[1] - a[1])
		.slice(0, max)
		.map(([p]) => p);
}


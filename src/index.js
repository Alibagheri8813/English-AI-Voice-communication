import { ensureProjectDirsExist, readChannelsConfig } from './config.js';
import { runIngestYoutubeJob } from './jobs/ingestYoutubeJob.js';
import { startTwitchWatcher } from './ingest/twitch.js';
import { startStorefront } from './storefront/server.js';

async function main() {
	ensureProjectDirsExist();
	const { youtubeChannels, twitchChannels } = readChannelsConfig();
	if (youtubeChannels.length === 0) {
		console.log('No channels configured yet. Add channel IDs to config/channels.yaml');
	} else {
		await runIngestYoutubeJob(youtubeChannels);
		console.log('Ingested and generated designs from latest videos.');
	}

	// Start Twitch watcher and storefront concurrently for 24/7 operation
	if (twitchChannels.length > 0) {
		startTwitchWatcher(twitchChannels).catch((err) => console.error('Twitch watcher error', err));
	}
	startStorefront();
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});


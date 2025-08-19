import { ensureProjectDirsExist, readChannelsConfig } from './config.js';
import { runIngestYoutubeJob } from './jobs/ingestYoutubeJob.js';

async function main() {
	ensureProjectDirsExist();
	const { youtubeChannels } = readChannelsConfig();
	if (youtubeChannels.length === 0) {
		console.log('No channels configured yet. Add channel IDs to config/channels.yaml');
		return;
	}
	await runIngestYoutubeJob(youtubeChannels);
	console.log('Ingested and generated designs from latest videos.');
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});


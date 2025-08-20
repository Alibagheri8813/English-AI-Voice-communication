import { ensureProjectDirsExist, readChannelsConfig } from './config.js';
import { startTwitchWatcher } from './ingest/twitch.js';
import { startStorefront } from './storefront/server.js';

async function main() {
	ensureProjectDirsExist();
	const { twitchChannels } = readChannelsConfig();

	// Start Twitch watcher and storefront concurrently for 24/7 operation
	if (twitchChannels.length > 0) {
		startTwitchWatcher(twitchChannels);
	} else {
		console.log('No Twitch channels configured. Add usernames to config/channels.yaml under twitchChannels.');
	}
	startStorefront();
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
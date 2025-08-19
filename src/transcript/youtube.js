import { YoutubeTranscript } from 'youtube-transcript';

export async function getYoutubeTranscript(videoId) {
	try {
		const items = await YoutubeTranscript.fetchTranscript(videoId, { lang: 'en' });
		return items.map((it) => ({ text: it.text, start: it.offset, dur: it.duration }));
	} catch (err) {
		return [];
	}
}


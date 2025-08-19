import sw from 'stopword';

const minimalBannedWords = new Set([
	// keep small to avoid false positives; extend later
	'fuck',
	'shit',
	'bitch',
	'cunt',
	'nigger',
	'kike',
	'spic',
	'faggot',
	'whore',
]);

export function extractTopPhrasesFromTranscriptItems(items, options = {}) {
	const { maxPhrases = 3 } = options;
	const joined = items.map((i) => i.text).join(' ');
	const tokens = tokenize(joined);
	const candidateToCount = new Map();

	for (let i = 0; i < tokens.length; i++) {
		for (let n = 2; n <= 4; n++) {
			if (i + n > tokens.length) break;
			const gram = tokens.slice(i, i + n).join(' ');
			if (!isCandidateValid(gram)) continue;
			candidateToCount.set(gram, (candidateToCount.get(gram) || 0) + 1);
		}
	}

	const ranked = Array.from(candidateToCount.entries())
		.filter(([p]) => p.length >= 6 && p.length <= 60)
		.sort((a, b) => b[1] - a[1])
		.slice(0, 20)
		.map(([phrase, count]) => ({ phrase, score: count }));

	// Deduplicate overlapping phrases
	const final = [];
	ranked.forEach((r) => {
		if (final.some((f) => includesPhrase(f.phrase, r.phrase))) return;
		final.push(r);
	});

	return final.slice(0, maxPhrases);
}

function tokenize(text) {
	const lower = text.toLowerCase().replace(/[^a-z0-9'\s]/g, ' ');
	const split = lower.split(/\s+/).filter(Boolean);
	return sw.removeStopwords(split);
}

function isCandidateValid(phrase) {
	const stopLead = /^(?:the|and|you|that|this|with|from|have|they|what|when|where|how|why|but|not|for|are|was|were|has|had|can|could|should|would)\b/;
	if (stopLead.test(phrase)) return false;
	if (containsProfanity(phrase)) return false;
	return true;
}

function containsProfanity(phrase) {
	const words = phrase.toLowerCase().split(/\s+/);
	return words.some((w) => minimalBannedWords.has(w));
}

function includesPhrase(a, b) {
	return a.includes(b) || b.includes(a);
}
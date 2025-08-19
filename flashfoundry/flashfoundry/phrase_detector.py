from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import math
from collections import defaultdict
from rapidfuzz import fuzz

from .text_utils import tokenize, generate_ngrams, filter_ngrams, get_stopwords
from .youtube_utils import TranscriptLine


@dataclass
class PhraseHit:
	phrase: str
	start: float
	end: float
	score: float
	count: int


def _window_index(timestamp: float, window_seconds: int) -> int:
	return int(timestamp // window_seconds)


def detect_hot_phrases(
	transcript: List[TranscriptLine],
	window_seconds: int = 60,
	language: str = "en",
	n_min: int = 1,
	n_max: int = 3,
	min_count: int = 2,
) -> List[PhraseHit]:
	"""Detect hot phrases with novelty by time-window.

	Scoring combines:
	- frequency within a window
	- cross-window novelty (peaks vs history)
	- length bonus for 2–3 grams
	"""
	stop = get_stopwords(language)
	window_to_phrase_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
	phrase_global_counts: Dict[str, int] = defaultdict(int)
	phrase_first_seen: Dict[str, float] = {}

	for line in transcript:
		tokens = [t for t in tokenize(line.text) if t]
		if not tokens:
			continue
		ngrams = generate_ngrams(tokens, n_min=n_min, n_max=n_max)
		ngrams = filter_ngrams(ngrams, stop)
		widx = _window_index(line.start, window_seconds)
		for ng in ngrams:
			window_to_phrase_counts[widx][ng] += 1
			phrase_global_counts[ng] += 1
			if ng not in phrase_first_seen:
				phrase_first_seen[ng] = line.start

	# Compute novelty score per phrase per window
	phrase_hits: List[PhraseHit] = []
	for widx, counts in window_to_phrase_counts.items():
		for phrase, c in counts.items():
			if phrase_global_counts[phrase] < min_count:
				continue
			# Historical mean up to previous windows
			hist_counts = [window_to_phrase_counts[w].get(phrase, 0) for w in range(0, widx)]
			mean_hist = (sum(hist_counts) / len(hist_counts)) if hist_counts else 0.0
			# Novelty: current vs historical average
			novelty = c - mean_hist
			length_bonus = 1.0 + 0.2 * (len(phrase.split()) - 1)
			score = (c * 1.0 + novelty * 0.8) * length_bonus
			start_time = widx * window_seconds
			end_time = start_time + window_seconds
			phrase_hits.append(PhraseHit(phrase=phrase, start=start_time, end=end_time, score=score, count=c))

	# Combine hits by phrase keeping the max-score window
	best_by_phrase: Dict[str, PhraseHit] = {}
	for hit in phrase_hits:
		cur = best_by_phrase.get(hit.phrase)
		if cur is None or hit.score > cur.score:
			best_by_phrase[hit.phrase] = hit

	# Rank by score, then by earlier first-seen
	results = list(best_by_phrase.values())
	results.sort(key=lambda h: (-h.score, phrase_first_seen.get(h.phrase, math.inf)))

	# Merge near-duplicate phrases (spacing/punctuation variants)
	merged: List[PhraseHit] = []
	for hit in results:
		merged_into = False
		for i, m in enumerate(merged):
			if fuzz.token_set_ratio(hit.phrase, m.phrase) >= 90:
				keep = hit if hit.score > m.score else m
				other = m if keep is hit else hit
				combined = PhraseHit(
					phrase=keep.phrase,
					start=keep.start,
					end=keep.end,
					score=max(keep.score, other.score),
					count=keep.count + other.count,
				)
				merged[i] = combined
				merged_into = True
				break
		if not merged_into:
			merged.append(hit)

	return merged


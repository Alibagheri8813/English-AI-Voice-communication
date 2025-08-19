from __future__ import annotations

from dataclasses import dataclass
from typing import List

import math

from .youtube_utils import TranscriptLine
from .text_utils import tokenize


@dataclass
class Highlight:
	start: float
	end: float
	score: float
	reason: str


def detect_highlights(transcript: List[TranscriptLine], window_seconds: int = 30) -> List[Highlight]:
	"""Detect highlight-worthy segments using transcript dynamics.

	Heuristics (no paid models):
	- word rate spikes
	- exclamation/intensity marks
	- sentiment proxies: uppercase ratio, laugher tokens (lol, haha), emphasis
	"""
	if not transcript:
		return []

	# Build windows
	total_time = transcript[-1].start + transcript[-1].duration
	n_windows = max(1, int(math.ceil(total_time / window_seconds)))
	word_rates = [0.0] * n_windows
	exclaim_rates = [0.0] * n_windows
	upper_rates = [0.0] * n_windows
	laugh_rates = [0.0] * n_windows

	def widx(ts: float) -> int:
		return min(n_windows - 1, int(ts // window_seconds))

	for line in transcript:
		idx = widx(line.start)
		toks = tokenize(line.text)
		word_rates[idx] += len(toks) / max(1e-6, line.duration or 1.0)
		exclaim_rates[idx] += line.text.count("!")
		upper_chars = sum(1 for ch in line.text if ch.isalpha() and ch.isupper())
		alpha_chars = sum(1 for ch in line.text if ch.isalpha()) or 1
		upper_rates[idx] += upper_chars / alpha_chars
		laugh_rates[idx] += sum(1 for t in toks if t in {"lol", "lmao", "haha", "rofl", "omg"})

	def zscore(arr: List[float]) -> List[float]:
		mu = sum(arr) / len(arr)
		var = sum((x - mu) ** 2 for x in arr) / max(1, len(arr) - 1)
		sd = max(1e-6, math.sqrt(var))
		return [(x - mu) / sd for x in arr]

	wz = zscore(word_rates)
	exz = zscore(exclaim_rates)
	uz = zscore(upper_rates)
	lz = zscore(laugh_rates)

	scores = [0.5 * wz[i] + 0.2 * exz[i] + 0.2 * uz[i] + 0.1 * lz[i] for i in range(n_windows)]

	# Adaptive threshold: keep windows above max(0.8, 85th percentile)
	sorted_scores = sorted(scores)
	percentile_idx = max(0, int(0.85 * (len(sorted_scores) - 1)))
	p85 = sorted_scores[percentile_idx]
	thresh = max(0.8, p85)

	highlights: List[Highlight] = []
	for i, s in enumerate(scores):
		if s >= thresh:
			start = i * window_seconds
			end = min(total_time, start + window_seconds)
			reason = f"word-rate:{wz[i]:.2f}, exclaim:{exz[i]:.2f}, upper:{uz[i]:.2f}"
			highlights.append(Highlight(start=start, end=end, score=float(s), reason=reason))

	# sort by score desc
	highlights.sort(key=lambda h: -h.score)
	return highlights


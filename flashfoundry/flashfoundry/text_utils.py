from __future__ import annotations

import re
from typing import Iterable, List

try:
	from nltk.corpus import stopwords as nltk_stopwords
	from nltk import download as nltk_download
	excepted = False
except Exception:
	excepted = True
	nltk_stopwords = None  # type: ignore


DEFAULT_STOPWORDS = set(
	[
		"the",
		"a",
		"an",
		"and",
		"or",
		"but",
		"to",
		"of",
		"in",
		"on",
		"for",
		"with",
		"is",
		"it",
		"that",
		"this",
		"at",
		"as",
		"are",
		"be",
		"was",
		"were",
		"so",
		"if",
		"we",
		"you",
		"they",
		"i",
		"he",
		"she",
	]
)


def get_stopwords(language: str = "en") -> set:
	"""Return a stopword set. Tries NLTK; falls back to a small default set.

	Parameters
	----------
	language: str
		Language code for stopwords (default: 'en').
	"""
	global excepted
	if not excepted:
		try:
			nltk_download("stopwords", quiet=True)
			return set(nltk_stopwords.words(language))  # type: ignore
		except Exception:
			excepted = True
			# fall through
	return DEFAULT_STOPWORDS


TOKEN_RE = re.compile(r"[\w']+")


def normalize_text(text: str) -> str:
	text = text.lower()
	text = re.sub(r"\s+", " ", text)
	return text.strip()


def tokenize(text: str) -> List[str]:
	return TOKEN_RE.findall(normalize_text(text))


def generate_ngrams(tokens: Iterable[str], n_min: int = 1, n_max: int = 3) -> List[str]:
	tokens_list = list(tokens)
	ngrams: List[str] = []
	for n in range(n_min, n_max + 1):
		for i in range(len(tokens_list) - n + 1):
			ngrams.append(" ".join(tokens_list[i : i + n]))
	return ngrams


def filter_ngrams(ngrams: Iterable[str], stopwords_set: set) -> List[str]:
	filtered: List[str] = []
	for ng in ngrams:
		words = ng.split()
		if all(w not in stopwords_set for w in words):
			filtered.append(ng)
	return filtered


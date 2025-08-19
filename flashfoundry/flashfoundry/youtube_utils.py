from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Optional

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


YOUTUBE_ID_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{6,})")


@dataclass
class TranscriptLine:
	start: float
	duration: float
	text: str


def extract_video_id(url_or_id: str) -> str:
	match = YOUTUBE_ID_RE.search(url_or_id)
	if match:
		return match.group(1)
	return url_or_id


def load_cookies(path: str) -> Optional[dict]:
	"""Load cookies from Netscape cookies.txt, JSON dict, or raw Cookie header string.

	Returns a dict mapping cookie name to value, suitable for requests.
	"""
	if not path:
		return None
	try:
		with open(path, "r", encoding="utf-8") as f:
			content = f.read().strip()
		# Try JSON object
		try:
			obj = json.loads(content)
			if isinstance(obj, dict):
				return obj
		except Exception:
			pass
		# Netscape cookies.txt format
		if content.startswith("#") or "\t" in content:
			cookies: dict = {}
			for line in content.splitlines():
				line = line.strip()
				if not line or line.startswith("#"):
					continue
				parts = line.split("\t")
				if len(parts) >= 7:
					name = parts[5]
					value = parts[6]
					cookies[name] = value
			return cookies or None
		# Raw Cookie header string: name=value; name2=value2
		if "=" in content and ";" in content:
			cookies = {}
			for kv in content.split(";"):
				if "=" in kv:
					k, v = kv.split("=", 1)
					cookies[k.strip()] = v.strip()
			return cookies or None
		return None
	except Exception:
		return None


def fetch_transcript(video_id_or_url: str, languages: Optional[List[str]] = None, cookies: Optional[object] = None) -> List[TranscriptLine]:
	"""Fetch a transcript with robust fallbacks and optional cookies support.

	Order of attempts:
	1) Direct fetch for preferred languages
	2) Manual transcript via list_transcripts
	3) Auto-generated transcript via list_transcripts
	4) Translate any available transcript to English
	"""
	video_id = extract_video_id(video_id_or_url)
	preferred = languages or ["en", "en-US", "en-GB", "en-CA", "en-AU"]

	def _to_lines(items: List[dict]) -> List[TranscriptLine]:
		out: List[TranscriptLine] = []
		for item in items:
			out.append(TranscriptLine(start=float(item.get("start", 0.0)), duration=float(item.get("duration", 0.0)), text=item.get("text", "")))
		return out

	# 1) Direct fetch
	try:
		kwargs = {"languages": preferred}
		if cookies:
			kwargs["cookies"] = cookies
		try:
			transcript = YouTubeTranscriptApi.get_transcript(video_id, **kwargs)
		except TypeError:
			# Older youtube-transcript-api versions may not support cookies kwarg
			kwargs.pop("cookies", None)
			transcript = YouTubeTranscriptApi.get_transcript(video_id, **kwargs)
		return _to_lines(transcript)
	except (TranscriptsDisabled, NoTranscriptFound):
		pass
	except Exception:
		pass

	# 2) Fallbacks via listing
	try:
		kwargs2 = {}
		if cookies:
			kwargs2["cookies"] = cookies
		try:
			transcripts = YouTubeTranscriptApi.list_transcripts(video_id, **kwargs2)
		except TypeError:
			kwargs2.pop("cookies", None)
			transcripts = YouTubeTranscriptApi.list_transcripts(video_id, **kwargs2)
		# 2a) Manual transcript in preferred languages
		try:
			manual = transcripts.find_transcript(preferred)
			return _to_lines(manual.fetch())
		except NoTranscriptFound:
			pass
		# 2b) Auto-generated transcript in preferred languages
		try:
			generated = transcripts.find_generated_transcript(preferred)
			return _to_lines(generated.fetch())
		except NoTranscriptFound:
			pass
		# 2c) Translate first available transcript to English
		for tr in transcripts:
			try:
				translated = tr.translate("en").fetch()
				return _to_lines(translated)
			except Exception:
				continue
	except Exception:
		pass

	return []


def load_transcript_from_file(path: str) -> List[TranscriptLine]:
	"""Load transcript from JSON (.json), SubRip (.srt) or WebVTT (.vtt)."""
	path_lower = path.lower()
	if path_lower.endswith(".json"):
		with open(path, "r", encoding="utf-8") as f:
			data = json.load(f)
		lines: List[TranscriptLine] = []
		for it in data:
			lines.append(TranscriptLine(start=float(it.get("start", 0.0)), duration=float(it.get("duration", 0.0)), text=it.get("text", "")))
		return lines
	if path_lower.endswith(".srt"):
		return _parse_srt(path)
	if path_lower.endswith(".vtt"):
		return _parse_vtt(path)
	raise ValueError("Unsupported transcript format. Use .json, .srt, or .vtt")


def _hms_to_seconds(ts: str) -> float:
	parts = re.split(r"[:,.]", ts)
	parts = [int(p) for p in parts if p != ""]
	while len(parts) < 4:
		parts.append(0)
	h, m, s, ms = parts[:4]
	return h * 3600 + m * 60 + s + ms / 1000.0


def _parse_srt(path: str) -> List[TranscriptLine]:
	with open(path, "r", encoding="utf-8", errors="ignore") as f:
		content = f.read()
	blocks = re.split(r"\n\s*\n", content.strip())
	lines: List[TranscriptLine] = []
	for block in blocks:
		rows = [r for r in block.splitlines() if r.strip()]
		if len(rows) < 2:
			continue
		# rows[0] may be index
		m = re.search(r"(\d\d:\d\d:\d\d,\d+)\s*-->\s*(\d\d:\d\d:\d\d,\d+)", " ".join(rows))
		if not m:
			continue
		start = _hms_to_seconds(m.group(1).replace(",", ":"))
		end = _hms_to_seconds(m.group(2).replace(",", ":"))
		text = " ".join(r for r in rows[2:] if r and not r.strip().isdigit())
		lines.append(TranscriptLine(start=start, duration=max(0.0, end - start), text=text))
	return lines


def _parse_vtt(path: str) -> List[TranscriptLine]:
	with open(path, "r", encoding="utf-8", errors="ignore") as f:
		content = f.read()
	blocks = re.split(r"\n\n+", content.strip())
	lines: List[TranscriptLine] = []
	for block in blocks:
		m = re.search(r"(\d\d:\d\d:\d\d\.\d+)\s*-->\s*(\d\d:\d\d:\d\d\.\d+)", block)
		if not m:
			continue
		start = _hms_to_seconds(m.group(1).replace(".", ":"))
		end = _hms_to_seconds(m.group(2).replace(".", ":"))
		text_lines = [ln for ln in block.splitlines()[1:] if ln and not ln.strip().startswith("WEBVTT")]
		text = " ".join(text_lines)
		lines.append(TranscriptLine(start=start, duration=max(0.0, end - start), text=text))
	return lines

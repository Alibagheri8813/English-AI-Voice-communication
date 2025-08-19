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


def fetch_transcript(video_id_or_url: str, languages: Optional[List[str]] = None) -> List[TranscriptLine]:
	video_id = extract_video_id(video_id_or_url)
	languages = languages or ["en", "en-US", "en-GB", "auto"]
	try:
		transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
	except (TranscriptsDisabled, NoTranscriptFound):
		return []
	except Exception:
		return []
	lines: List[TranscriptLine] = []
	for item in transcript:
		lines.append(TranscriptLine(start=float(item.get("start", 0.0)), duration=float(item.get("duration", 0.0)), text=item.get("text", "")))
	return lines


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


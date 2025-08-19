from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict
from typing import Iterable, List

from .phrase_detector import PhraseHit
from .highlight_detector import Highlight
from .product_suggester import ProductIdea


def ensure_dir(path: str) -> None:
	os.makedirs(path, exist_ok=True)


def export_phrases_csv(path: str, phrases: Iterable[PhraseHit]) -> None:
	with open(path, "w", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)
		writer.writerow(["phrase", "start", "end", "score", "count"])
		for p in phrases:
			writer.writerow([p.phrase, f"{p.start:.2f}", f"{p.end:.2f}", f"{p.score:.4f}", p.count])


def export_highlights_csv(path: str, highlights: Iterable[Highlight]) -> None:
	with open(path, "w", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)
		writer.writerow(["start", "end", "score", "reason"])
		for h in highlights:
			writer.writerow([f"{h.start:.2f}", f"{h.end:.2f}", f"{h.score:.4f}", h.reason])


def export_products_csv(path: str, ideas: Iterable[ProductIdea]) -> None:
	with open(path, "w", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)
		writer.writerow(["phrase", "category", "style", "colors", "prompt"])
		for idea in ideas:
			writer.writerow([idea.phrase, idea.category, idea.style, idea.colors, idea.prompt])


def export_phrases_notion_csv(path: str, phrases: Iterable[PhraseHit], video_id: str) -> None:
	"""Export with Notion-friendly headers matching templates/notion_phrases.csv."""
	with open(path, "w", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)
		writer.writerow(["Phrase", "Video ID", "Start (s)", "End (s)", "Score", "Count", "Status", "Notes"])
		for p in phrases:
			writer.writerow([p.phrase, video_id, f"{p.start:.2f}", f"{p.end:.2f}", f"{p.score:.4f}", p.count, "Idea", ""]) 


def export_report_json(path: str, phrases: List[PhraseHit], highlights: List[Highlight], ideas: List[ProductIdea]) -> None:
	data = {
		"phrases": [asdict(p) for p in phrases],
		"highlights": [asdict(h) for h in highlights],
		"products": [asdict(i) for i in ideas],
	}
	with open(path, "w", encoding="utf-8") as f:
		json.dump(data, f, ensure_ascii=False, indent=2)


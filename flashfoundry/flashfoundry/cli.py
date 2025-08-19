from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from .youtube_utils import fetch_transcript, load_transcript_from_file, extract_video_id
from .phrase_detector import detect_hot_phrases
from .highlight_detector import detect_highlights
from .product_suggester import suggest_products
from .export_utils import (
	ensure_dir,
	export_phrases_csv,
	export_phrases_notion_csv,
	export_highlights_csv,
	export_products_csv,
	export_report_json,
)


app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def main(
	url: List[str] = typer.Option(..., "--url", help="YouTube video URL(s) or ID(s)", show_default=False),
	out: str = typer.Option("out", help="Output directory"),
	transcript_file: Optional[str] = typer.Option(None, help="Optional local transcript file (.json/.srt/.vtt)"),
	language: str = typer.Option("en", help="Stopword language code"),
	window_seconds: int = typer.Option(60, help="Window size for phrase detection"),
	top_k: int = typer.Option(30, help="Number of top phrases to export"),
):
	"""Analyze YouTube videos to extract hot phrases, highlights and product ideas."""
	for u in url:
		video_id = extract_video_id(u)
		console.rule(f"[bold]Analyzing {video_id}")
		if transcript_file:
			transcript = load_transcript_from_file(transcript_file)
		else:
			transcript = fetch_transcript(u)
		if not transcript:
			console.print(f"[red]No transcript available for {video_id}. Skipping.")
			continue

		phrases = detect_hot_phrases(transcript, window_seconds=window_seconds, language=language)
		highlights = detect_highlights(transcript, window_seconds=30)
		ideas = suggest_products(phrases, top_k=top_k)

		out_dir = os.path.join(out, video_id)
		ensure_dir(out_dir)
		export_phrases_csv(os.path.join(out_dir, "phrases.csv"), phrases[:top_k])
		export_highlights_csv(os.path.join(out_dir, "highlights.csv"), highlights)
		export_products_csv(os.path.join(out_dir, "products.csv"), ideas)
		export_report_json(os.path.join(out_dir, "report.json"), phrases[:top_k], highlights, ideas)
		export_phrases_notion_csv(os.path.join(out_dir, "phrases_notion.csv"), phrases[:top_k], video_id)

		# Pretty tables
		table = Table(title=f"Top {min(top_k, len(phrases))} Phrases — {video_id}")
		table.add_column("Phrase")
		table.add_column("Window")
		table.add_column("Score")
		table.add_column("Count")
		for p in phrases[:top_k]:
			table.add_row(p.phrase, f"{p.start:.0f}-{p.end:.0f}s", f"{p.score:.2f}", str(p.count))
		console.print(table)

		table2 = Table(title=f"Highlights — {video_id}")
		table2.add_column("Start")
		table2.add_column("End")
		table2.add_column("Score")
		table2.add_column("Reason")
		for h in highlights[:15]:
			table2.add_row(f"{h.start:.0f}s", f"{h.end:.0f}s", f"{h.score:.2f}", h.reason)
		console.print(table2)


if __name__ == "__main__":
	app()


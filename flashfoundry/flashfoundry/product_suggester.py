from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .phrase_detector import PhraseHit


@dataclass
class ProductIdea:
	phrase: str
	category: str  # t-shirt, hoodie, sticker, poster, digital-pack
	style: str  # typography, mascot, minimal, retro, graffiti
	colors: str
	prompt: str


DEFAULT_STYLES = [
	("t-shirt", "bold typography", "black/white + 1 accent", "High-contrast text composition with clean kerning and a strong accent color."),
	("hoodie", "mascot", "2-3 flat colors", "Cute mascot or emblem referencing the phrase without logos or likeness."),
	("sticker", "minimal", "white or transparent", "Minimal vector sticker with thick outline and drop shadow."),
	("poster", "retro", "duotone", "Retro poster with duotone palette and halftone texture."),
	("digital-pack", "overlay pack", "transparent PNGs", "Stream overlay pack: lower-thirds, badges, emotes inspired by the phrase."),
]


def suggest_products(phrases: List[PhraseHit], top_k: int = 15) -> List[ProductIdea]:
	ideas: List[ProductIdea] = []
	for i, hit in enumerate(phrases[:top_k]):
		style = DEFAULT_STYLES[i % len(DEFAULT_STYLES)]
		category, style_name, colors, guidance = style
		prompt = (
			f"Design for {category}: phrase '{hit.phrase}'. Style: {style_name}. Colors: {colors}. "
			f"Avoid copyrighted logos/likeness. Keep print-friendly vector shapes. {guidance}"
		)
		ideas.append(
			ProductIdea(
				phrase=hit.phrase,
				category=category,
				style=style_name,
				colors=colors,
				prompt=prompt,
			)
		)
	return ideas


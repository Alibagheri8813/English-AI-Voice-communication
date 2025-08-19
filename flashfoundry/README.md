## FlashFoundry Zero-Cost Toolkit

This repo gives you a high-performance, zero-cost workflow to detect hot phrases and highlight moments from YouTube videos, turn them into merch/digital product ideas, and export clean CSVs you can import into Notion or Google Sheets. No paid APIs, no monthly tools required.

### What you get
- CLI to analyze YouTube videos and extract:
  - Hot phrases with time windows (novelty- and sentiment-weighted)
  - Highlight segments (scene-level excitement from transcript dynamics)
  - Product ideas and design prompts per phrase
  - CSV/JSON exports for Notion/Sheets
- Import-ready CSV templates for Notion/Sheets (`templates/notion_*.csv`)
- Outreach scripts for DMs/emails (`templates/outreach_scripts.md`)
- One-page rev-share agreement (`legal/rev_share_agreement.md`)

### Quick start (Linux/macOS)
1) Python 3.10+ recommended. Install dependencies:
```
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2) Run the analyzer on a YouTube URL:
```
python -m flashfoundry.cli --url https://www.youtube.com/watch?v=VIDEO_ID --out out
```

3) Outputs
- `out/<video_id>/phrases.csv` — hot phrases with scores and timestamps
- `out/<video_id>/highlights.csv` — highlight segments with reasons
- `out/<video_id>/products.csv` — product suggestions and design prompts
- `out/<video_id>/report.json` — combined structured output

4) Import to Notion/Sheets
- Import `out/<video_id>/phrases_notion.csv` into your Notion "Phrases" database (or use `templates/notion_phrases.csv` to seed your workspace).
- Import `templates/notion_creators.csv` and `templates/notion_drops.csv` to set up your CRM.

### Features (free-only stack)
- Transcript fetch via `youtube-transcript-api` (no API key needed)
- Language-agnostic preprocessing with NLTK stopwords fallback
- N-gram mining (1–3 grams) + time-window novelty scoring
- VADER sentiment to favor positive/impactful phrases
- Highlight detection from transcript dynamics (word rate, exclamations, sentiment spikes)
- Deterministic and repeatable: no paid LLMs required

### Optional (power-ups, still free)
- If a video has no transcript, you can add your own SRT/VTT via `--transcript-file`.
- Offline speech-to-text is supported via Whisper if you choose to install it separately (see FAQ). This is optional and not required.

### CLI usage
```
python -m flashfoundry.cli \
  --url https://www.youtube.com/watch?v=VIDEO_ID \
  --out out \
  --top-k 30 \
  --window-seconds 60 \
  --language en
```

Key flags:
- `--url`: Single YouTube URL. Repeat the flag for multiple URLs.
- `--transcript-file`: Optional path to a local SRT/VTT/JSON transcript.
- `--top-k`: Number of top phrases to output (default 30).
- `--window-seconds`: Time window for novelty ex/score (default 60s).
- `--language`: Stopword set hint (default `en`).

### Project structure
```
flashfoundry/
  README.md
  requirements.txt
  flashfoundry/
    __init__.py
    cli.py
    youtube_utils.py
    phrase_detector.py
    highlight_detector.py
    product_suggester.py
    export_utils.py
    text_utils.py
  templates/
    notion_creators.csv
    notion_phrases.csv
    notion_drops.csv
    outreach_scripts.md
    design_prompt_examples.md
  legal/
    rev_share_agreement.md
```

### FAQ
- No transcript available? Use `--transcript-file` if you have an SRT/VTT. Offline speech-to-text (Whisper) is optional and not required for this toolkit.
- Does this scrape comments? No, to stay free and stable we rely on transcripts and timing signals. You can extend it later.
- Will this work in other languages? Yes, but stopword filtering works best when `--language` matches the video language.

### License
MIT. Use freely for commercial projects. No warranty.


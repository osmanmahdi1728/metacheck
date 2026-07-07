# MetaCheck

Pre-release metadata validator for music distribution. Upload a CSV of track
metadata and get a plain-language report of the errors that would cause DSPs
(Spotify, Apple Music, Boomplay, Audiomack, etc.) to reject a track or drop
royalties — plus an estimate of the royalties each gap puts at risk.

> **DistroKid gets your music on Spotify. MetaCheck makes sure you actually
> get paid for it — everywhere it plays.**

See **[docs/royalty-flow.md](docs/royalty-flow.md)** for the full explanation
of how royalties flow across borders (CMO → CMO → you) and exactly where the
chain breaks for ~95% of independent artists — the gap MetaCheck fixes.

## What it checks

- **Metadata rules** — ISRC format, contributor completeness, genre, explicit
  and AI flags, release-date lead time, language codes.
- **CMO registration** — cross-references the ISRC against collective royalty
  databases (SOCAN / ASCAP / MCSK / …) to confirm the work is actually
  registered for collection, not just that the field is filled. (Demo uses a
  local mock registry; swap in real APIs in `validator/cmo.py`.)
- **Royalty-at-risk estimate** — connects a broken/missing field to the money
  it costs, based on stream counts (real or projected) and blended per-stream
  rates. This is the layer DistroKid / TuneCore / LANDR don't have.
- **Plain-language rewrite** — optional GPT-4o-mini pass that turns error codes
  into artist-friendly guidance. Works without a key (falls back to built-in
  messages).

## Project structure

```
metacheck/
├── api/
│   └── index.py                # Vercel serverless entry (reuses app.py)
├── data/
│   ├── sample_tracks.csv       # demo CSV with intentional errors + streams
│   └── cmo_registry.csv        # mock CMO registration data (demo)
├── docs/
│   └── royalty-flow.md         # why MetaCheck exists: how royalties flow
├── validator/
│   ├── __init__.py
│   ├── rules.py                # the validation ruleset
│   ├── cmo.py                  # CMO registration lookup
│   ├── royalty.py              # royalty-at-risk estimator
│   ├── humanize.py             # optional GPT-4o-mini plain-language layer
│   └── pipeline.py             # shared processing used by CLI + web
├── templates/
│   ├── upload_form.html        # web upload page
│   └── report.html             # shared report template (web + CLI)
├── app.py                      # Flask web app (Step 2/3)
├── main.py                     # CLI: CSV -> report/output.html (Step 1)
├── vercel.json                 # Vercel deploy config (Step 3)
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

```bash
pip install -r requirements.txt
```

## Run the web app (recommended)

```bash
python app.py
```

Open http://localhost:5000, upload `data/sample_tracks.csv`, and the report
renders in your browser instantly. No API key needed.

## Run the CLI

```bash
python main.py                     # validates data/sample_tracks.csv
python main.py path/to/your.csv    # validate any CSV
```

It writes `report/output.html` and opens it in your browser.

To enable GPT-4o-mini plain-language rewrites in the CLI, copy `.env.example`
to `.env` and set `OPENAI_API_KEY`. Without a key it uses the built-in
(already readable) messages.

## CSV columns

Required:
`title, artist, isrc, composer, publisher, genre, release_date, explicit, ai_generated, language`

Optional:
`streams` — real or estimated stream count. Improves the royalty-at-risk
estimate. When omitted, a conservative first-year projection is used and the
figure is labeled "(projected)".

Release dates use `YYYY-MM-DD`. `explicit` and `ai_generated` must be
`true` or `false`.

## Deploy to Vercel

The app ships with `vercel.json` and `api/index.py` so it runs on Vercel's
Python runtime.

```bash
npm i -g vercel        # if you don't have it
vercel                 # preview deploy
vercel --prod          # production deploy
```

To enable the plain-language layer in production, add `OPENAI_API_KEY` in the
Vercel project's Environment Variables (never commit it).

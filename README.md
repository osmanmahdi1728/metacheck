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

## Three ways to enter a track

No spreadsheet required — the web app has three input tabs, all feeding the
same validation engine:

1. **CSV upload** — bulk-check a whole catalogue.
2. **Type it in** — a form for a single track; fill what you have, leave the
   rest blank, and MetaCheck flags the gaps.
3. **Search Spotify** — pull a real track's metadata by name. Spotify provides
   the ISRC, release date, and explicit flag — but *not* composer, publisher,
   or CMO registration, so those gaps show up live. (Requires free Spotify
   credentials; see below.)

### Real-data enrichment (MusicBrainz)

For the manual and Spotify paths, MetaCheck cross-references the track's ISRC
against **MusicBrainz** (the open music database, no API key needed) to pull
the real composer/work data. This powers the strongest insight: Spotify gives
the ISRC, MusicBrainz knows the composers — but if the distribution submission
left the composer blank, no CMO can match the royalties. The report shows a
callout naming the composers found in public databases. MetaCheck also reads
the work's **ISWC** (the international work code assigned at CMO/CISAC
registration) from MusicBrainz — its presence is real evidence the composition
is registered for collection.

### Real per-platform streams (Soundcharts, optional/paid)

By default the royalty estimate splits one stream figure across platforms by a
modeled market-share distribution. Set `SOUNDCHARTS_APP_ID` and
`SOUNDCHARTS_API_KEY` to replace that model with **real measured per-platform
stream counts by ISRC** — Soundcharts covers Spotify streams and Audiomack plays
(and other DSPs, including African ones), which Spotify's own API does not. When
configured, each platform is priced against its actual count and tagged `real`;
platforms with no public play count (e.g. Apple Music) are estimated from the
measured anchor by market share and tagged `est.`. Without the keys, MetaCheck
falls back to the model, so nothing breaks. Adapter lives in
`validator/soundcharts.py`.

## What it checks

- **Metadata rules** — ISRC format, contributor completeness, genre, explicit
  and AI flags, release-date lead time, language codes.
- **CMO registration** — confirms a work is actually registered for collection,
  not just that the field is filled. MetaCheck only makes a *positive* claim
  when it has real evidence: a hit in the CMO registry, or an ISWC from
  MusicBrainz. It never asserts "not registered" from absence of evidence
  (that produced false negatives on real hits) — instead it reports registration
  as unconfirmed. (Demo uses a local mock registry; swap in real CMO APIs in
  `validator/cmo.py`.)
- **Royalty-at-risk estimate** — connects a broken/missing field to the money
  it costs. Uses real measured per-platform streams when Soundcharts is
  configured (see above); otherwise splits the total (real or projected) across
  platforms by a modeled Afro-market distribution and prices each with
  per-platform per-stream mechanical rates. Override the split with real numbers
  via `estimate_risk(shares=...)` or `estimate_risk(platform_streams=...)`. This
  is the layer DistroKid / TuneCore / LANDR don't have.
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
│   ├── spotify.py              # Spotify track lookup (optional)
│   ├── musicbrainz.py          # real composer/work enrichment by ISRC
│   ├── soundcharts.py          # real per-platform streams by ISRC (optional/paid)
│   ├── humanize.py             # optional GPT-4o-mini plain-language layer
│   └── pipeline.py             # shared processing (CSV, manual, Spotify)
├── templates/
│   ├── upload_form.html        # CSV upload page
│   ├── manual_form.html        # single-track entry form
│   ├── spotify_search.html     # Spotify search + results
│   └── report.html             # shared report template (web + CLI)
├── tests/                      # pytest suite (rules, royalty, cmo, app, ...)
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

## Optional: enable Spotify search

1. Create a free app at
   [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard).
2. Copy its **Client ID** and **Client Secret** into `.env`:

   ```
   SPOTIFY_CLIENT_ID=...
   SPOTIFY_CLIENT_SECRET=...
   ```

3. Restart the app. The "Search Spotify" tab becomes active. Uses the Client
   Credentials flow (app-only, no user login).

## Running the tests

```bash
pip install -r requirements.txt
pytest
```

The suite covers the validation rules, royalty math, CMO lookup, the full
pipeline, the Spotify metadata mapping, and the Flask routes (47 tests).

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

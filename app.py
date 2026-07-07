"""MetaCheck web app (Step 2).

A local Flask app that wraps the metadata validator so users can upload a
CSV and see the validation report rendered inline in the browser.

How to run:
    pip install -r requirements.txt
    python app.py
    # Open http://localhost:5000 in your browser
    # Upload data/sample_tracks.csv
    # See the validation report rendered in the browser

On macOS, port 5000 is often taken by the AirPlay Receiver. If you see
"Address already in use", either disable AirPlay Receiver in System
Settings, or run on another port:
    PORT=5001 python app.py

Optionally reads OPENAI_API_KEY from .env to enable a "plain-language"
rewrite of errors via GPT-4o-mini. Without a key it still works fully using
the built-in messages. No database, no login. The file is processed in memory
and the report is returned immediately.
"""
import io
import os

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, render_template, request

from validator import musicbrainz, royalty, soundcharts, spotify
from validator.humanize import humanize_errors, is_available
from validator.pipeline import EXPECTED_COLUMNS, process_dataframe, process_records, summarize

load_dotenv()

# Flask needs absolute template/static paths so it works both locally and on
# serverless platforms (Vercel) where the working directory differs.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(_BASE_DIR, "templates"))

# 5 MB cap on uploads — plenty for a metadata CSV, guards against abuse.
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


@app.context_processor
def inject_rates():
    """Expose per-stream mechanical rates to the report's interactive tool."""
    return {
        "all_platform_rates": {**royalty.MECHANICAL_RATES, **royalty.EXTRA_MECHANICAL_RATES},
        "default_platforms": list(royalty.MECHANICAL_RATES),
    }


def _nav_context(**extra):
    """Shared template context: which optional integrations are configured."""
    ctx = {
        "ai_available": is_available(),
        "spotify_available": spotify.is_available(),
        "soundcharts_available": soundcharts.is_available(),
    }
    ctx.update(extra)
    return ctx


def _single_track_source():
    """Human-readable data-source label for single-track (enriched) reports."""
    parts = ["Spotify", "MusicBrainz"]
    if soundcharts.is_available():
        parts.append("Soundcharts")
    return " + ".join(parts)


def _humanizer_if_requested():
    """Return the GPT humanizer only if a key exists AND the user opted in."""
    if is_available() and request.form.get("plain_language") == "on":
        return humanize_errors
    return None


@app.route("/", methods=["GET"])
def index():
    return render_template("upload_form.html", **_nav_context())


@app.route("/validate", methods=["POST"])
def validate():
    uploaded = request.files.get("file")

    if uploaded is None or uploaded.filename == "":
        return render_template("upload_form.html", **_nav_context(error="Please choose a CSV file to upload.")), 400

    if not uploaded.filename.lower().endswith(".csv"):
        return render_template("upload_form.html", **_nav_context(error="That file isn't a CSV. Please upload a .csv file.")), 400

    try:
        raw = uploaded.read()
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except Exception:
        return render_template("upload_form.html", **_nav_context(error="We couldn't read that CSV. Check that it's a valid, comma-separated file.")), 400

    if df.empty:
        return render_template("upload_form.html", **_nav_context(error="That CSV has no rows to validate.")), 400

    results = process_dataframe(df, humanizer=_humanizer_if_requested())
    return render_template("report.html", results=results, **summarize(results))


@app.route("/manual", methods=["GET"])
def manual():
    return render_template("manual_form.html", **_nav_context(fields={}))


@app.route("/validate-manual", methods=["POST"])
def validate_manual():
    record = {col: request.form.get(col, "").strip() for col in EXPECTED_COLUMNS + ["streams"]}

    if not record.get("title") and not record.get("artist") and not record.get("isrc"):
        return render_template("manual_form.html", **_nav_context(fields=record, error="Enter at least a title, artist, or ISRC.")), 400

    results = process_records(
        [record],
        humanizer=_humanizer_if_requested(),
        enricher=musicbrainz.enrich_by_isrc,
        streams_fetcher=soundcharts.streams_by_isrc,
    )
    return render_template("report.html", results=results, source=_single_track_source(), **summarize(results))


@app.route("/spotify", methods=["GET", "POST"])
def spotify_search():
    if not spotify.is_available():
        return render_template("spotify_search.html", **_nav_context(configured=False))

    if request.method == "GET":
        return render_template("spotify_search.html", **_nav_context(configured=True))

    query = request.form.get("query", "").strip()
    if not query:
        return render_template("spotify_search.html", **_nav_context(configured=True, error="Type a song name or artist to search.")), 400

    try:
        tracks = spotify.search_tracks(query)
    except spotify.SpotifyError as exc:
        return render_template("spotify_search.html", **_nav_context(configured=True, query=query, error=str(exc))), 502

    return render_template("spotify_search.html", **_nav_context(configured=True, query=query, tracks=tracks))


@app.route("/spotify/validate", methods=["POST"])
def spotify_validate():
    track_id = request.form.get("track_id", "").strip()
    if not track_id:
        return render_template("spotify_search.html", **_nav_context(configured=True, error="No track selected.")), 400

    try:
        record = spotify.get_track_metadata(track_id)
    except spotify.SpotifyError as exc:
        return render_template("spotify_search.html", **_nav_context(configured=True, error=str(exc))), 502

    results = process_records(
        [record],
        humanizer=_humanizer_if_requested(),
        enricher=musicbrainz.enrich_by_isrc,
        streams_fetcher=soundcharts.streams_by_isrc,
    )
    return render_template("report.html", results=results, source=_single_track_source(), **summarize(results))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

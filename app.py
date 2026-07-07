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

from validator.humanize import humanize_errors, is_available
from validator.pipeline import process_dataframe, summarize

load_dotenv()

# Flask needs absolute template/static paths so it works both locally and on
# serverless platforms (Vercel) where the working directory differs.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(_BASE_DIR, "templates"))

# 5 MB cap on uploads — plenty for a metadata CSV, guards against abuse.
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


@app.route("/", methods=["GET"])
def index():
    return render_template("upload_form.html", ai_available=is_available())


@app.route("/validate", methods=["POST"])
def validate():
    uploaded = request.files.get("file")

    if uploaded is None or uploaded.filename == "":
        return render_template("upload_form.html", ai_available=is_available(), error="Please choose a CSV file to upload."), 400

    if not uploaded.filename.lower().endswith(".csv"):
        return render_template("upload_form.html", ai_available=is_available(), error="That file isn't a CSV. Please upload a .csv file."), 400

    try:
        raw = uploaded.read()
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except Exception:
        return render_template("upload_form.html", ai_available=is_available(), error="We couldn't read that CSV. Check that it's a valid, comma-separated file."), 400

    if df.empty:
        return render_template("upload_form.html", ai_available=is_available(), error="That CSV has no rows to validate."), 400

    # Use the GPT rewrite only if the key exists AND the user opted in.
    use_ai = is_available() and request.form.get("plain_language") == "on"
    humanizer = humanize_errors if use_ai else None

    results = process_dataframe(df, humanizer=humanizer)
    stats = summarize(results)
    return render_template("report.html", results=results, **stats)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

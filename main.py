"""MetaCheck CLI — validate a metadata CSV and write an HTML report.

Usage:
    pip install -r requirements.txt
    python main.py                     # uses data/sample_tracks.csv
    python main.py path/to/tracks.csv  # validate any CSV

Set OPENAI_API_KEY in .env to enable GPT-4o-mini plain-language rewrites.
Without a key, the raw (already human-readable) validator messages are used.
"""
import os
import sys
import webbrowser

import pandas as pd
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader

from validator.humanize import humanize_errors
from validator.pipeline import process_dataframe, summarize

load_dotenv()


def run_validation(csv_path="data/sample_tracks.csv"):
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    return process_dataframe(df, humanizer=humanize_errors)


def generate_report(results, output_path="report/output.html"):
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report.html")
    stats = summarize(results)
    html = template.render(results=results, **stats)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Report generated: {output_path}")
    return output_path


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_tracks.csv"
    results = run_validation(path)
    out = generate_report(results)
    webbrowser.open(f"file://{os.path.abspath(out)}")

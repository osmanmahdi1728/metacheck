"""Shared processing pipeline used by both the CLI (main.py) and web app (app.py).

Keeping this in one place guarantees the CSV upload path and the CLI path
produce identical results. Steps per track:
  1. Rule-based metadata validation (rules.py)
  2. CMO registration cross-check (cmo.py)
  3. Royalty-at-risk estimate (royalty.py)
  4. Optional plain-language rewrite (humanize.py)
"""
from .cmo import check_registration
from .rules import normalize_isrc, validate_track
from .royalty import estimate_risk, format_usd, parse_streams

EXPECTED_COLUMNS = [
    "title", "artist", "isrc", "composer", "publisher",
    "genre", "release_date", "explicit", "ai_generated", "language",
]

# Optional column that improves royalty estimates when present.
OPTIONAL_COLUMNS = ["streams"]

ISRC_VALID_CODES_TO_SKIP_CMO = {"ISRC_MISSING", "ISRC_INVALID_FORMAT"}


def process_dataframe(df, humanizer=None):
    """Run the full pipeline over a pandas DataFrame (CSV upload path)."""
    return process_records(df.to_dict("records"), humanizer=humanizer)


def process_records(records, humanizer=None, enricher=None, streams_fetcher=None):
    """Run the full validation + royalty pipeline over a list of dicts.

    This is the shared core for every input method (CSV upload, manual form,
    Spotify lookup) — they all reduce to a list of track dicts.

    Args:
        records: list of track metadata dicts.
        humanizer: optional callable(track_title, issues) -> issues that
            rewrites issue detail strings (e.g. via GPT-4o-mini). When None,
            raw validator messages are used.
        enricher: optional callable(isrc) -> dict with real metadata pulled
            from a public database (e.g. MusicBrainz). Used to surface data
            the submission is missing. Skipped for tracks without a usable
            ISRC. Best used on single-track paths (it makes network calls).
        streams_fetcher: optional callable(isrc) -> {platform: count} of REAL
            per-platform streams (e.g. Soundcharts). When it returns data, the
            royalty estimate uses those actual counts instead of the modeled
            market-share split. Returns None to fall back to the model.

    Returns:
        list of per-track result dicts consumed by the report template.
    """
    results = []
    for track in records:
        validation = validate_track(track)
        errors = list(validation["errors"])
        warnings = list(validation["warnings"])

        isrc = _clean(track.get("isrc"), "")
        composer = _clean(track.get("composer"), "")
        have_isrc_issue = any(i["code"] in ISRC_VALID_CODES_TO_SKIP_CMO for i in errors)

        # Real-data enrichment (MusicBrainz) — only with a usable ISRC. Attached
        # as its own field and shown as a distinct callout in the report.
        mb = None
        if enricher is not None and isrc and not have_isrc_issue:
            mb = enricher(normalize_isrc(isrc))

        # Registration status. We only make a POSITIVE claim when we have real
        # evidence: a hit in the (demo) CMO registry, or an ISWC from
        # MusicBrainz (the international work code assigned at CMO registration).
        # We never assert "not registered" — absence of evidence isn't proof,
        # and false negatives on real tracks destroy credibility.
        cmo_info = {"registered": None, "cmo": None, "registered_composer": None, "iswc": None, "source": None}
        if isrc and not have_isrc_issue:
            registry = check_registration(isrc)
            if registry["registered"]:
                cmo_info.update({
                    "registered": True,
                    "cmo": registry["cmo"],
                    "registered_composer": registry["registered_composer"],
                    "source": registry["cmo"],
                })
                if composer and registry["registered_composer"] and composer.lower() != registry["registered_composer"].lower():
                    warnings.append({
                        "field": "composer",
                        "code": "CMO_COMPOSER_MISMATCH",
                        "detail": f"The composer '{composer}' doesn't match the name on file at {registry['cmo']} ('{registry['registered_composer']}'). This can cause royalty splits to pay the wrong party.",
                    })
            elif mb and mb.get("iswcs"):
                cmo_info.update({
                    "registered": True,
                    "iswc": mb["iswcs"][0],
                    "source": "ISWC via MusicBrainz",
                })

        # Real per-platform streams (e.g. Soundcharts) — only with a usable ISRC.
        platform_streams = None
        if streams_fetcher is not None and isrc and not have_isrc_issue:
            platform_streams = streams_fetcher(normalize_isrc(isrc))

        all_issues = errors + warnings

        # Royalty-at-risk estimate (keys off issue codes, so run before humanizing).
        streams, projected = parse_streams(track.get("streams"))
        risk = estimate_risk([i["code"] for i in all_issues], streams, platform_streams=platform_streams)
        streams_measured = risk.get("measured", False)

        # Plain-language rewrite last (preserves codes).
        issues = humanizer(track.get("title", "Unknown"), all_issues) if humanizer else all_issues

        results.append({
            "title": _clean(track.get("title"), "Unknown"),
            "artist": _clean(track.get("artist"), "Unknown"),
            "isrc": _clean(track.get("isrc"), "N/A"),
            "status": validation["status"],
            "error_count": len(errors),
            "warning_count": len(warnings),
            "issues": issues,
            "cmo": cmo_info,
            "streams": risk["streams"],
            "streams_projected": projected and not streams_measured,
            "streams_measured": streams_measured,
            "royalty_at_risk": risk["amount"],
            "royalty_at_risk_display": format_usd(risk["amount"]),
            "royalty_breakdown": risk["breakdown"],
            "mb": mb,
        })
    return results


def summarize(results):
    """Return summary stats for the report header, including total $ at risk."""
    total_risk = round(sum(r["royalty_at_risk"] for r in results), 2)
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r["status"] == "PASS"),
        "failed": sum(1 for r in results if r["status"] == "FAIL"),
        "total_royalty_at_risk": total_risk,
        "total_royalty_at_risk_display": format_usd(total_risk),
    }


def _clean(value, fallback):
    if value is None:
        return fallback
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return fallback
    return text

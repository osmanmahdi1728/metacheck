"""Shared processing pipeline used by both the CLI (main.py) and web app (app.py).

Keeping this in one place guarantees the CSV upload path and the CLI path
produce identical results. Steps per track:
  1. Rule-based metadata validation (rules.py)
  2. CMO registration cross-check (cmo.py)
  3. Royalty-at-risk estimate (royalty.py)
  4. Optional plain-language rewrite (humanize.py)
"""
from .cmo import check_registration
from .rules import validate_track
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


def process_records(records, humanizer=None):
    """Run the full validation + royalty pipeline over a list of dicts.

    This is the shared core for every input method (CSV upload, manual form,
    Spotify lookup) — they all reduce to a list of track dicts.

    Args:
        records: list of track metadata dicts.
        humanizer: optional callable(track_title, issues) -> issues that
            rewrites issue detail strings (e.g. via GPT-4o-mini). When None,
            raw validator messages are used.

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

        # CMO registration cross-check — only meaningful for a well-formed ISRC.
        cmo_info = {"registered": None, "cmo": None, "registered_composer": None}
        have_isrc_issue = any(i["code"] in ISRC_VALID_CODES_TO_SKIP_CMO for i in errors)
        if isrc and not have_isrc_issue:
            cmo_info = check_registration(isrc)
            if not cmo_info["registered"]:
                warnings.append({
                    "field": "isrc",
                    "code": "CMO_UNREGISTERED",
                    "detail": "This ISRC isn't registered at any CMO (SOCAN, ASCAP, MCSK, etc.) in our records. Performance and mechanical royalties can't be collected until the work is registered.",
                })
            elif composer and cmo_info["registered_composer"] and composer.lower() != cmo_info["registered_composer"].lower():
                warnings.append({
                    "field": "composer",
                    "code": "CMO_COMPOSER_MISMATCH",
                    "detail": f"The composer '{composer}' doesn't match the name on file at {cmo_info['cmo']} ('{cmo_info['registered_composer']}'). This can cause royalty splits to pay the wrong party.",
                })

        all_issues = errors + warnings

        # Royalty-at-risk estimate (keys off issue codes, so run before humanizing).
        streams, projected = parse_streams(track.get("streams"))
        risk = estimate_risk([i["code"] for i in all_issues], streams)

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
            "streams": streams,
            "streams_projected": projected,
            "royalty_at_risk": risk["amount"],
            "royalty_at_risk_display": format_usd(risk["amount"]),
            "royalty_breakdown": risk["breakdown"],
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

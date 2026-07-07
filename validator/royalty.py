"""Estimate the royalties a metadata gap puts at risk.

This is the layer existing form-validators (DistroKid, TuneCore, LANDR) do
NOT have: connecting a missing/broken field to the money it actually costs.

The figures here are grounded in commonly-cited per-stream MECHANICAL royalty
rates by platform. They are transparent estimates for a pitch demo, not
guarantees — rates vary by territory, deal, and payout period. Update
MECHANICAL_RATES / DEFAULT_PROJECTED_STREAMS as you gather real data.
"""

# Real-world-ish per-stream MECHANICAL royalty rates (USD per stream), by
# platform. When a composer/publisher isn't registered, these are the
# royalties that go uncollected. Add/adjust platforms as needed.
MECHANICAL_RATES = {
    "Spotify": 0.000393,
    "Apple Music": 0.000456,
    "Audiomack": 0.00012,
}

# When a track row has no `streams` value, assume a modest first-year
# projection for an independent release so the estimate is still meaningful.
DEFAULT_PROJECTED_STREAMS = 100_000

# Issue codes that mean mechanical royalties can't be collected until fixed.
# A missing composer (or unregistered/mismatched work) blocks CMO registration;
# a missing publisher blocks the admin/collection relationship. To stop counting
# publisher-only gaps against a track, remove "PUBLISHER_MISSING" below.
MECHANICAL_RISK_CODES = {
    "COMPOSER_MISSING",
    "CMO_UNREGISTERED",
    "CMO_COMPOSER_MISMATCH",
    "PUBLISHER_MISSING",
}


def parse_streams(value):
    """Return (streams, is_projected).

    Accepts the optional `streams` CSV column. Falls back to a projection when
    the value is missing or unparseable.
    """
    if value is None:
        return DEFAULT_PROJECTED_STREAMS, True
    text = str(value).strip().replace(",", "")
    if text == "" or text.lower() == "nan":
        return DEFAULT_PROJECTED_STREAMS, True
    try:
        streams = int(float(text))
        if streams < 0:
            return DEFAULT_PROJECTED_STREAMS, True
        return streams, False
    except ValueError:
        return DEFAULT_PROJECTED_STREAMS, True


def estimate_risk(issue_codes, streams):
    """Estimate uncollected mechanical royalties for one track.

    Args:
        issue_codes: iterable of issue code strings found for the track.
        streams: integer stream count (real or projected).

    Returns:
        dict with total USD at risk and a per-platform breakdown. Returns
        amount 0.0 with an empty breakdown when nothing is at risk.
    """
    codes = set(issue_codes)
    if not (codes & MECHANICAL_RISK_CODES):
        return {"amount": 0.0, "streams": streams, "breakdown": [], "at_risk": False}

    breakdown = []
    total = 0.0
    for platform, rate in MECHANICAL_RATES.items():
        amount = round(streams * rate, 2)
        total += amount
        breakdown.append({
            "platform": platform,
            "amount": amount,
            "amount_display": format_usd(amount),
            "rate": rate,
        })

    return {
        "amount": round(total, 2),
        "streams": streams,
        "breakdown": breakdown,
        "at_risk": total > 0,
    }


def format_usd(amount):
    """Format a dollar amount like $4,200 (whole) or $329.46 (with cents)."""
    if amount == int(amount):
        return f"${int(amount):,}"
    return f"${amount:,.2f}"

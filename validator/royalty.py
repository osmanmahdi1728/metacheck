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

# How a track's TOTAL cross-platform streams are distributed across platforms.
# A single stream figure isn't "Spotify streams" — it's the track's plays, split
# across the services people actually use. These are modeled shares tilted for
# an Afro-market release (Audiomack is significant in Nigeria/Ghana). They are a
# defensible default, NOT live per-platform data: no free/official API exposes
# real per-platform play counts. Pass `shares=` to estimate_risk() to override
# with real per-artist numbers when you have them. Shares are normalized, so
# they don't need to sum to exactly 1.
PLATFORM_STREAM_SHARE = {
    "Spotify": 0.45,
    "Apple Music": 0.25,
    "Audiomack": 0.30,
}

# When a track row has no `streams` value, assume a modest first-year
# projection for an independent release so the estimate is still meaningful.
DEFAULT_PROJECTED_STREAMS = 100_000

# Issue codes that mean mechanical royalties can't be collected until fixed.
# A missing composer (or a work registered to the wrong writer) blocks CMO
# registration/matching; a missing publisher blocks the admin/collection
# relationship. We deliberately do NOT include a generic "unregistered" code:
# we can't prove a work is unregistered from public data, so risk is driven by
# concrete gaps in the submission itself. To stop counting publisher-only gaps
# against a track, remove "PUBLISHER_MISSING" below.
MECHANICAL_RISK_CODES = {
    "COMPOSER_MISSING",
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


def estimate_risk(issue_codes, streams, shares=None):
    """Estimate uncollected mechanical royalties for one track.

    The `streams` figure is treated as the track's TOTAL cross-platform plays
    and distributed across platforms by `shares` (a market-share split), so each
    platform is priced against its own realistic slice of the streams rather than
    the full count. Override `shares` with real per-artist numbers when available.

    Args:
        issue_codes: iterable of issue code strings found for the track.
        streams: integer TOTAL stream count (real or projected).
        shares: optional {platform: weight} override. Defaults to
            PLATFORM_STREAM_SHARE. Weights are normalized over the platforms we
            have rates for, so they need not sum to 1.

    Returns:
        dict with total USD at risk and a per-platform breakdown (each entry
        carries that platform's stream slice). Returns amount 0.0 with an empty
        breakdown when nothing is at risk.
    """
    codes = set(issue_codes)
    if not (codes & MECHANICAL_RISK_CODES):
        return {"amount": 0.0, "streams": streams, "breakdown": [], "at_risk": False}

    weights = shares or PLATFORM_STREAM_SHARE
    # Only distribute over platforms we can actually price.
    priced = {p: weights.get(p, 0.0) for p in MECHANICAL_RATES}
    total_weight = sum(priced.values()) or 1.0

    breakdown = []
    total = 0.0
    for platform, rate in MECHANICAL_RATES.items():
        share = priced[platform] / total_weight
        platform_streams = int(round(streams * share))
        amount = round(platform_streams * rate, 2)
        total += amount
        breakdown.append({
            "platform": platform,
            "streams": platform_streams,
            "streams_display": f"{platform_streams:,}",
            "share": round(share, 4),
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

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

# Additional platforms offered in the interactive "what-if" tool on the report
# page (client-side only). These are rough, commonly-cited per-stream mechanical
# estimates — adjust freely. They are NOT used by the server-side default
# estimate, which sticks to MECHANICAL_RATES above.
EXTRA_MECHANICAL_RATES = {
    "YouTube Music": 0.00008,
    "Amazon Music": 0.00040,
    "Deezer": 0.00035,
    "Tidal": 0.00050,
    "Boomplay": 0.00010,
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


def estimate_risk(issue_codes, streams, shares=None, platform_streams=None):
    """Estimate uncollected mechanical royalties for one track.

    Two modes, in priority order:

    1. Real per-platform data (`platform_streams`, e.g. from Soundcharts): each
       measured platform is priced against its ACTUAL stream/play count. For a
       platform we couldn't measure (e.g. Apple Music, which publishes no play
       counts), we estimate it from the largest measured platform using the
       market-share ratio, and flag it as estimated.
    2. Modeled split (default): `streams` is treated as the track's TOTAL
       cross-platform plays and distributed across platforms by `shares`.

    Args:
        issue_codes: iterable of issue code strings found for the track.
        streams: integer TOTAL stream count (real or projected). Used for the
            modeled split and as a fallback.
        shares: optional {platform: weight} override for the modeled split.
            Weights are normalized, so they need not sum to 1.
        platform_streams: optional {platform: count} of REAL measured streams.

    Returns:
        dict with total USD at risk, a per-platform breakdown (each entry flags
        `measured`), the effective total `streams`, and a `measured` bool.
        Returns amount 0.0 with an empty breakdown when nothing is at risk.
    """
    codes = set(issue_codes)
    if not (codes & MECHANICAL_RISK_CODES):
        return {"amount": 0.0, "streams": streams, "breakdown": [], "at_risk": False, "measured": False}

    weights = shares or PLATFORM_STREAM_SHARE
    priced = {p: weights.get(p, 0.0) for p in MECHANICAL_RATES}
    total_weight = sum(priced.values()) or 1.0

    measured = {
        p: int(v) for p, v in (platform_streams or {}).items()
        if p in MECHANICAL_RATES and isinstance(v, (int, float)) and v >= 0
    }

    per_platform, is_measured = _resolve_platform_streams(streams, priced, total_weight, measured)

    breakdown = []
    total_amount = 0.0
    total_streams = 0
    for platform, rate in MECHANICAL_RATES.items():
        count = per_platform[platform]
        amount = round(count * rate, 2)
        total_amount += amount
        total_streams += count
        breakdown.append({
            "platform": platform,
            "streams": count,
            "streams_display": f"{count:,}",
            "share": round(priced[platform] / total_weight, 4),
            "measured": is_measured[platform],
            "amount": amount,
            "amount_display": format_usd(amount),
            "rate": rate,
        })

    return {
        "amount": round(total_amount, 2),
        "streams": total_streams if measured else streams,
        "breakdown": breakdown,
        "at_risk": total_amount > 0,
        "measured": bool(measured),
    }


def _resolve_platform_streams(streams, priced, total_weight, measured):
    """Return ({platform: count}, {platform: measured_bool}) for all platforms.

    Uses real counts where measured; fills unmeasured platforms either from a
    measured anchor (share ratio) or, with no measured data, from the modeled
    split of the projected total.
    """
    per_platform, is_measured = {}, {}
    if measured:
        anchor = max(measured, key=lambda p: priced[p])
        anchor_share = priced[anchor] or (1.0 / len(priced))
        for platform in priced:
            if platform in measured:
                per_platform[platform] = measured[platform]
                is_measured[platform] = True
            else:
                ratio = (priced[platform] / anchor_share) if anchor_share else 0.0
                per_platform[platform] = int(round(measured[anchor] * ratio))
                is_measured[platform] = False
    else:
        for platform in priced:
            per_platform[platform] = int(round(streams * priced[platform] / total_weight))
            is_measured[platform] = False
    return per_platform, is_measured


def format_usd(amount):
    """Format a dollar amount like $4,200 (whole) or $329.46 (with cents)."""
    if amount == int(amount):
        return f"${int(amount):,}"
    return f"${amount:,.2f}"

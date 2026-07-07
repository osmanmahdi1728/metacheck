from validator.royalty import (
    DEFAULT_PROJECTED_STREAMS,
    MECHANICAL_RATES,
    PLATFORM_STREAM_SHARE,
    estimate_risk,
    format_usd,
    parse_streams,
)


def _expected_split_total(streams, shares=None):
    """Mirror estimate_risk's split math so tests aren't brittle to rate changes."""
    weights = shares or PLATFORM_STREAM_SHARE
    priced = {p: weights.get(p, 0.0) for p in MECHANICAL_RATES}
    total_weight = sum(priced.values()) or 1.0
    total = 0.0
    for platform, rate in MECHANICAL_RATES.items():
        platform_streams = int(round(streams * priced[platform] / total_weight))
        total += round(platform_streams * rate, 2)
    return round(total, 2)


def test_parse_real_streams():
    assert parse_streams("340000") == (340000, False)


def test_parse_streams_with_commas():
    assert parse_streams("1,000") == (1000, False)


def test_parse_missing_streams_projects():
    assert parse_streams("") == (DEFAULT_PROJECTED_STREAMS, True)
    assert parse_streams(None) == (DEFAULT_PROJECTED_STREAMS, True)
    assert parse_streams("nan") == (DEFAULT_PROJECTED_STREAMS, True)


def test_parse_garbage_streams_projects():
    assert parse_streams("lots") == (DEFAULT_PROJECTED_STREAMS, True)


def test_parse_negative_streams_projects():
    assert parse_streams("-5") == (DEFAULT_PROJECTED_STREAMS, True)


def test_no_risk_codes_means_zero():
    risk = estimate_risk(["GENRE_NOT_STANDARD", "LANGUAGE_MISSING"], 500000)
    assert risk["amount"] == 0.0
    assert risk["at_risk"] is False
    assert risk["breakdown"] == []


def test_composer_missing_triggers_all_platforms():
    streams = 340000
    risk = estimate_risk(["COMPOSER_MISSING"], streams)
    assert risk["at_risk"] is True
    assert len(risk["breakdown"]) == len(MECHANICAL_RATES)
    assert risk["amount"] == _expected_split_total(streams)


def test_streams_are_split_across_platforms_not_duplicated():
    streams = 100000
    risk = estimate_risk(["COMPOSER_MISSING"], streams)
    # Per-platform slices should sum to (about) the total, not 3x it.
    assert sum(line["streams"] for line in risk["breakdown"]) == streams
    # Each platform reflects its own share, so slices differ.
    slices = {line["platform"]: line["streams"] for line in risk["breakdown"]}
    assert slices["Spotify"] > slices["Apple Music"]


def test_shares_override_changes_distribution():
    streams = 100000
    even = {"Spotify": 1, "Apple Music": 1, "Audiomack": 1}
    risk = estimate_risk(["COMPOSER_MISSING"], streams, shares=even)
    slices = {line["platform"]: line["streams"] for line in risk["breakdown"]}
    assert slices["Spotify"] == slices["Apple Music"] == slices["Audiomack"]
    assert risk["amount"] == _expected_split_total(streams, shares=even)


def test_overlapping_publishing_codes_do_not_double_count():
    streams = 210000
    only_composer = estimate_risk(["COMPOSER_MISSING"], streams)["amount"]
    both = estimate_risk(["COMPOSER_MISSING", "PUBLISHER_MISSING"], streams)["amount"]
    assert only_composer == both


def test_measured_platform_streams_are_priced_directly():
    # Real Spotify + Audiomack counts; Apple has no data and is estimated.
    measured = {"Spotify": 1_000_000, "Audiomack": 400_000}
    risk = estimate_risk(["COMPOSER_MISSING"], 100000, platform_streams=measured)
    assert risk["measured"] is True
    by_platform = {b["platform"]: b for b in risk["breakdown"]}
    assert by_platform["Spotify"]["streams"] == 1_000_000
    assert by_platform["Spotify"]["measured"] is True
    assert by_platform["Audiomack"]["streams"] == 400_000
    assert by_platform["Audiomack"]["measured"] is True
    # Apple Music is filled from the anchor (Spotify) via share ratio, flagged.
    assert by_platform["Apple Music"]["measured"] is False
    assert by_platform["Apple Music"]["streams"] > 0
    # Reported total streams reflects the measured/derived per-platform sum.
    assert risk["streams"] == sum(b["streams"] for b in risk["breakdown"])


def test_no_risk_short_circuits_even_with_measured_streams():
    risk = estimate_risk(["GENRE_MISSING"], 100000, platform_streams={"Spotify": 999})
    assert risk["at_risk"] is False
    assert risk["measured"] is False


def test_format_usd_whole_vs_cents():
    assert format_usd(100) == "$100"
    assert format_usd(1700) == "$1,700"
    assert format_usd(329.46) == "$329.46"

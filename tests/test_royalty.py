from validator.royalty import (
    DEFAULT_PROJECTED_STREAMS,
    MECHANICAL_RATES,
    estimate_risk,
    format_usd,
    parse_streams,
)


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
    expected = round(sum(streams * r for r in MECHANICAL_RATES.values()), 2)
    assert risk["amount"] == expected


def test_overlapping_publishing_codes_do_not_double_count():
    streams = 210000
    only_composer = estimate_risk(["COMPOSER_MISSING"], streams)["amount"]
    both = estimate_risk(["COMPOSER_MISSING", "CMO_UNREGISTERED"], streams)["amount"]
    assert only_composer == both


def test_format_usd_whole_vs_cents():
    assert format_usd(100) == "$100"
    assert format_usd(1700) == "$1,700"
    assert format_usd(329.46) == "$329.46"

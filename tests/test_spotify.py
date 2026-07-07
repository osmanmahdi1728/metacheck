from validator import spotify

SAMPLE_TRACK = {
    "name": "Lost In Lagos",
    "artists": [{"name": "DJ Eko"}, {"name": "Amara Sy"}],
    "external_ids": {"isrc": "FRZ032400001"},
    "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
    "explicit": True,
    "popularity": 61,
    "album": {"name": "Lagos Nights", "release_date": "2024-06-25", "release_date_precision": "day"},
}


def test_map_track_fills_recording_fields():
    meta = spotify.map_track_to_metadata(SAMPLE_TRACK)
    assert meta["title"] == "Lost In Lagos"
    assert meta["artist"] == "DJ Eko, Amara Sy"
    assert meta["isrc"] == "FRZ032400001"
    assert meta["explicit"] == "true"
    assert meta["release_date"] == "2024-06-25"


def test_map_track_leaves_unavailable_fields_blank():
    meta = spotify.map_track_to_metadata(SAMPLE_TRACK)
    # These are the fields Spotify doesn't expose — the whole point of the demo.
    assert meta["composer"] == ""
    assert meta["publisher"] == ""
    assert meta["genre"] == ""
    assert meta["ai_generated"] == ""


def test_normalize_year_only_date():
    assert spotify._normalize_date("2024", "year") == "2024-01-01"


def test_normalize_month_date():
    assert spotify._normalize_date("2024-06", "month") == "2024-06-01"


def test_normalize_full_date_unchanged():
    assert spotify._normalize_date("2024-06-25", "day") == "2024-06-25"


def test_is_available_false_without_creds(monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    assert spotify.is_available() is False


def test_is_available_true_with_creds(monkeypatch):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "x")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "y")
    assert spotify.is_available() is True

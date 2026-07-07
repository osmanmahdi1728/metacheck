import validator.soundcharts as sc


def test_song_uuid_from_object_wrapper():
    assert sc._song_uuid({"object": {"uuid": "abc-123"}}) == "abc-123"


def test_song_uuid_from_flat_payload():
    assert sc._song_uuid({"uuid": "flat-9"}) == "flat-9"


def test_song_uuid_none_when_missing():
    assert sc._song_uuid(None) is None
    assert sc._song_uuid({}) is None
    assert sc._song_uuid({"object": {}}) is None


def test_latest_audience_takes_most_recent_value():
    payload = {"items": [
        {"date": "2026-01-01", "value": 100},
        {"date": "2026-03-01", "value": 500},
        {"date": "2026-02-01", "value": 300},
    ]}
    assert sc._latest_audience(payload) == 500


def test_latest_audience_handles_data_key_and_empty():
    assert sc._latest_audience({"data": [{"date": "2026-01-01", "value": 42}]}) == 42
    assert sc._latest_audience({"items": []}) is None
    assert sc._latest_audience(None) is None


def test_latest_audience_skips_null_values():
    payload = {"items": [{"date": "2026-04-01", "value": None}, {"date": "2026-01-01", "value": 7}]}
    assert sc._latest_audience(payload) == 7


def test_is_available_reflects_env(monkeypatch):
    monkeypatch.delenv("SOUNDCHARTS_APP_ID", raising=False)
    monkeypatch.delenv("SOUNDCHARTS_API_KEY", raising=False)
    assert sc.is_available() is False
    monkeypatch.setenv("SOUNDCHARTS_APP_ID", "id")
    monkeypatch.setenv("SOUNDCHARTS_API_KEY", "key")
    assert sc.is_available() is True


def test_streams_by_isrc_returns_none_when_unconfigured(monkeypatch):
    monkeypatch.delenv("SOUNDCHARTS_APP_ID", raising=False)
    monkeypatch.delenv("SOUNDCHARTS_API_KEY", raising=False)
    assert sc.streams_by_isrc("USRC12003059") is None

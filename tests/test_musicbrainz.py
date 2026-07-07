from validator import musicbrainz as mb

ISRC_PAYLOAD = {
    "isrc": "USRC12003059",
    "recordings": [
        {
            "id": "rec-123",
            "title": "Essence",
            "artist-credit": [{"name": "Wizkid"}, {"name": "Tems"}],
        }
    ],
}

RECORDING_PAYLOAD = {
    "id": "rec-123",
    "relations": [
        {"target-type": "work", "work": {"id": "work-abc"}},
        {"target-type": "artist", "artist": {"id": "a1", "name": "Some Producer"}},
    ],
}

WORK_PAYLOAD = {
    "title": "Essence",
    "iswcs": ["T-303.010.722-9"],
    "relations": [
        {"type": "composer", "artist": {"name": "Wizkid"}},
        {"type": "lyricist", "artist": {"name": "Tems"}},
        {"type": "publishing", "artist": {"name": "Some Publisher"}},
    ],
}


def test_first_recording_extracts_fields():
    rec = mb._first_recording(ISRC_PAYLOAD)
    assert rec["id"] == "rec-123"
    assert rec["title"] == "Essence"
    assert rec["artists"] == "Wizkid, Tems"


def test_first_recording_none_when_empty():
    assert mb._first_recording({"recordings": []}) is None
    assert mb._first_recording(None) is None


def test_work_ids_only_returns_work_targets():
    assert mb._work_ids(RECORDING_PAYLOAD) == ["work-abc"]


def test_work_ids_empty_when_none():
    assert mb._work_ids(None) == []


def test_composers_from_work_filters_writer_roles():
    names = mb._composers_from_work(WORK_PAYLOAD)
    assert "Wizkid" in names
    assert "Tems" in names
    # A publishing relation is not a writer credit.
    assert "Some Publisher" not in names


def test_iswcs_from_work_extracts_codes():
    assert mb._iswcs_from_work(WORK_PAYLOAD) == ["T-303.010.722-9"]


def test_iswcs_from_work_empty_when_missing():
    assert mb._iswcs_from_work({"title": "No Code"}) == []
    assert mb._iswcs_from_work(None) == []


def test_enrich_by_isrc_blank_returns_not_found():
    result = mb.enrich_by_isrc("")
    assert result["found"] is False
    assert result["composers"] == []

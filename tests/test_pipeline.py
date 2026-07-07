from validator.pipeline import process_records, summarize

VALID_REGISTERED = {
    "title": "Midnight Savanna", "artist": "SAFARIZMA", "isrc": "QZ-ES1-26-00001",
    "composer": "Osman Mahdi", "publisher": "Self", "genre": "Afro House",
    "release_date": "2099-12-01", "explicit": "false", "ai_generated": "false",
    "language": "en", "streams": "12000",
}

COMPOSER_MISSING_REGISTERED = {
    "title": "Lost In Lagos", "artist": "DJ Eko", "isrc": "FR-Z03-24-00001",
    "composer": "", "publisher": "Universal Africa", "genre": "Afrobeats",
    "release_date": "2099-12-25", "explicit": "true", "ai_generated": "false",
    "language": "en", "streams": "340000",
}

UNREGISTERED_NO_COMPOSER = {
    "title": "City Lights", "artist": "Unknown Artist", "isrc": "US-RC1-26-00412",
    "composer": "", "publisher": "", "genre": "Pop",
    "release_date": "2099-01-01", "explicit": "false", "ai_generated": "false",
    "language": "en", "streams": "210000",
}


def test_valid_registered_track_passes_with_no_risk():
    (r,) = process_records([VALID_REGISTERED])
    assert r["status"] == "PASS"
    assert r["royalty_at_risk"] == 0.0
    assert r["cmo"]["registered"] is True


def test_composer_missing_has_mechanical_risk():
    (r,) = process_records([COMPOSER_MISSING_REGISTERED])
    assert r["status"] == "FAIL"
    assert r["royalty_at_risk"] == 329.46
    assert len(r["royalty_breakdown"]) == 3


def test_unregistered_isrc_flagged_and_priced():
    (r,) = process_records([UNREGISTERED_NO_COMPOSER])
    assert r["status"] == "FAIL"
    assert r["cmo"]["registered"] is False
    assert r["royalty_at_risk"] == 203.49


def test_summary_totals():
    results = process_records([VALID_REGISTERED, COMPOSER_MISSING_REGISTERED, UNREGISTERED_NO_COMPOSER])
    stats = summarize(results)
    assert stats["total"] == 3
    assert stats["passed"] == 1
    assert stats["failed"] == 2
    assert stats["total_royalty_at_risk"] == 532.95


def test_enricher_attaches_public_db_data():
    def fake_enricher(isrc):
        return {"found": True, "recording_title": "Lost In Lagos", "artists": "DJ Eko",
                "composers": ["Jean Okafor"], "work_titles": ["Lost In Lagos"]}

    (r,) = process_records([COMPOSER_MISSING_REGISTERED], enricher=fake_enricher)
    assert r["mb"]["found"] is True
    assert r["mb"]["composers"] == ["Jean Okafor"]


def test_enricher_skipped_for_bad_isrc():
    calls = []

    def spy_enricher(isrc):
        calls.append(isrc)
        return {"found": False}

    bad = {**COMPOSER_MISSING_REGISTERED, "isrc": "BADISRC"}
    (r,) = process_records([bad], enricher=spy_enricher)
    assert calls == []  # never called when the ISRC is invalid
    assert r["mb"] is None


def test_humanizer_is_applied_and_preserves_codes():
    def fake_humanizer(title, issues):
        return [{**i, "detail": "friendly: " + i["detail"]} for i in issues]

    (r,) = process_records([COMPOSER_MISSING_REGISTERED], humanizer=fake_humanizer)
    assert all(i["detail"].startswith("friendly: ") for i in r["issues"])
    # Codes preserved so royalty math still worked.
    assert r["royalty_at_risk"] == 329.46

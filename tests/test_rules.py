from validator.rules import is_valid_isrc, normalize_isrc, validate_track


def codes(result):
    return {i["code"] for i in result["errors"] + result["warnings"]}


def test_isrc_valid_with_and_without_hyphens():
    # Same ISRC, two formats — both must be accepted.
    assert is_valid_isrc("US-RC1-20-03059") is True
    assert is_valid_isrc("USRC12003059") is True  # Spotify's un-hyphenated form


def test_isrc_invalid_rejected():
    assert is_valid_isrc("BADISRC") is False
    assert is_valid_isrc("US-RC1-20-0305") is False  # too short


def test_normalize_isrc_strips_separators():
    assert normalize_isrc("us-rc1-20-03059") == "USRC12003059"


def test_unhyphenated_isrc_passes_validation():
    row = {**BASE_VALID, "isrc": "USRC12003059"}
    assert "ISRC_INVALID_FORMAT" not in codes(validate_track(row))


BASE_VALID = {
    "title": "Midnight Savanna",
    "artist": "SAFARIZMA",
    "isrc": "QZ-ES1-26-00001",
    "composer": "Osman Mahdi",
    "publisher": "Self",
    "genre": "Afro House",
    "release_date": "2099-12-31",
    "explicit": "false",
    "ai_generated": "false",
    "language": "en",
}


def test_fully_valid_track_passes():
    result = validate_track(BASE_VALID)
    assert result["status"] == "PASS"
    assert result["errors"] == []


def test_missing_title():
    row = {**BASE_VALID, "title": ""}
    assert "TITLE_MISSING" in codes(validate_track(row))


def test_missing_artist():
    row = {**BASE_VALID, "artist": ""}
    assert "ARTIST_MISSING" in codes(validate_track(row))


def test_missing_isrc():
    row = {**BASE_VALID, "isrc": ""}
    assert "ISRC_MISSING" in codes(validate_track(row))


def test_invalid_isrc_format():
    row = {**BASE_VALID, "isrc": "BADISRC"}
    assert "ISRC_INVALID_FORMAT" in codes(validate_track(row))


def test_missing_composer():
    row = {**BASE_VALID, "composer": ""}
    assert "COMPOSER_MISSING" in codes(validate_track(row))


def test_missing_publisher_is_warning_not_fail():
    row = {**BASE_VALID, "publisher": ""}
    result = validate_track(row)
    assert result["status"] == "PASS"
    assert "PUBLISHER_MISSING" in codes(result)


def test_release_date_in_past_is_allowed():
    # MetaCheck validates already-released catalog too, so a past date is fine.
    row = {**BASE_VALID, "release_date": "2000-01-01"}
    result = validate_track(row)
    assert "RELEASE_DATE_PAST" not in codes(result)
    assert result["status"] == "PASS"


def test_release_date_bad_format():
    row = {**BASE_VALID, "release_date": "31/12/2099"}
    assert "RELEASE_DATE_FORMAT" in codes(validate_track(row))


def test_missing_explicit_flag():
    row = {**BASE_VALID, "explicit": ""}
    assert "EXPLICIT_FLAG_MISSING" in codes(validate_track(row))


def test_missing_ai_flag():
    row = {**BASE_VALID, "ai_generated": ""}
    assert "AI_FLAG_MISSING" in codes(validate_track(row))


def test_nonstandard_genre_is_warning():
    row = {**BASE_VALID, "genre": "Experimental Noise"}
    result = validate_track(row)
    assert result["status"] == "PASS"
    assert "GENRE_NOT_STANDARD" in codes(result)


def test_feat_in_artist_field_warns():
    row = {**BASE_VALID, "artist": "SAFARIZMA feat. DJ Eko"}
    assert "ARTIST_FEAT_IN_NAME" in codes(validate_track(row))


def test_pandas_nan_string_treated_as_missing():
    # pandas can surface empty cells as the string "nan".
    row = {**BASE_VALID, "composer": "nan"}
    assert "COMPOSER_MISSING" in codes(validate_track(row))

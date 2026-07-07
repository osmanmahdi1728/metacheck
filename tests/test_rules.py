from validator.rules import validate_track


def codes(result):
    return {i["code"] for i in result["errors"] + result["warnings"]}


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


def test_release_date_in_past():
    row = {**BASE_VALID, "release_date": "2000-01-01"}
    assert "RELEASE_DATE_PAST" in codes(validate_track(row))


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

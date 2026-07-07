from validator.cmo import check_registration


def test_registered_isrc_found():
    result = check_registration("QZ-ES1-26-00001")
    assert result["registered"] is True
    assert result["cmo"] == "SOCAN"
    assert result["registered_composer"] == "Osman Mahdi"


def test_registered_isrc_case_insensitive():
    assert check_registration("qz-es1-26-00001")["registered"] is True


def test_unregistered_isrc():
    result = check_registration("US-RC1-26-00412")
    assert result["registered"] is False
    assert result["cmo"] is None


def test_blank_isrc_not_registered():
    assert check_registration("")["registered"] is False

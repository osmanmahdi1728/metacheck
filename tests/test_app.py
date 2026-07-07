import io

import pytest

from app import app as flask_app

SAMPLE_CSV = (
    "title,artist,isrc,composer,publisher,genre,release_date,explicit,ai_generated,language,streams\n"
    "Lost In Lagos,DJ Eko,FR-Z03-24-00001,,Universal Africa,Afrobeats,2099-12-25,true,false,en,340000\n"
)


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_home_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"CSV upload" in resp.data


def test_manual_page(client):
    resp = client.get("/manual")
    assert resp.status_code == 200
    assert b"Type in a track" in resp.data


def test_spotify_page_shows_setup_when_unconfigured(client, monkeypatch):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    resp = client.get("/spotify")
    assert resp.status_code == 200
    assert b"developer app" in resp.data


def test_validate_csv_renders_report(client):
    data = {"file": (io.BytesIO(SAMPLE_CSV.encode()), "tracks.csv")}
    resp = client.post("/validate", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert b"Royalties at Risk" in resp.data
    assert b"Lost In Lagos" in resp.data


def test_validate_rejects_missing_file(client):
    resp = client.post("/validate", data={}, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_validate_rejects_non_csv(client):
    data = {"file": (io.BytesIO(b"hello"), "notes.txt")}
    resp = client.post("/validate", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_manual_validation_renders_report(client):
    resp = client.post("/validate-manual", data={
        "title": "Lost In Lagos", "artist": "DJ Eko", "isrc": "FR-Z03-24-00001",
        "composer": "", "publisher": "Universal", "genre": "Afrobeats",
        "release_date": "2099-12-25", "explicit": "true", "ai_generated": "false",
        "language": "en", "streams": "340000",
    })
    assert resp.status_code == 200
    assert b"Royalties at Risk" in resp.data


def test_manual_validation_requires_some_input(client):
    resp = client.post("/validate-manual", data={})
    assert resp.status_code == 400

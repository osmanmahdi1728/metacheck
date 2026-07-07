"""Spotify Web API lookup — search a real track and pull its metadata.

Uses the Client Credentials flow (app-only auth, no user login), so all it
needs is SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET from a free Spotify
developer app.

The pitch-relevant point: Spotify's API returns *recording* metadata (title,
artist, ISRC, release date, explicit) but NOT composer, publisher, or CMO
registration — exactly the fields MetaCheck flags. So a real track pulled from
Spotify will surface those gaps live.
"""
import base64
import os
import time

import requests

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"
TIMEOUT = 10

_token_cache = {"access_token": None, "expires_at": 0}


class SpotifyError(Exception):
    """Raised for any Spotify lookup failure, with a user-friendly message."""


def is_available():
    """True if Spotify credentials are configured."""
    return bool(os.getenv("SPOTIFY_CLIENT_ID")) and bool(os.getenv("SPOTIFY_CLIENT_SECRET"))


def _get_token():
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"]:
        return _token_cache["access_token"]

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SpotifyError("Spotify credentials are not configured.")

    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            headers={"Authorization": f"Basic {auth}"},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SpotifyError(f"Couldn't reach Spotify: {exc}") from exc

    if resp.status_code != 200:
        raise SpotifyError("Spotify auth failed. Double-check your client ID and secret.")

    payload = resp.json()
    _token_cache["access_token"] = payload["access_token"]
    # Refresh a minute early to avoid edge-of-expiry failures.
    _token_cache["expires_at"] = now + payload.get("expires_in", 3600) - 60
    return _token_cache["access_token"]


def _auth_headers():
    return {"Authorization": f"Bearer {_get_token()}"}


def search_tracks(query, limit=5):
    """Search Spotify for tracks matching a free-text query.

    Returns a list of lightweight dicts for the results page.
    """
    if not query or not query.strip():
        return []
    try:
        resp = requests.get(
            f"{API_BASE}/search",
            params={"q": query.strip(), "type": "track", "limit": limit},
            headers=_auth_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SpotifyError(f"Couldn't reach Spotify: {exc}") from exc

    if resp.status_code != 200:
        raise SpotifyError("Spotify search failed. Try again in a moment.")

    items = resp.json().get("tracks", {}).get("items", [])
    return [_summarize(item) for item in items]


def get_track_metadata(track_id):
    """Fetch one track by ID and map it to MetaCheck's metadata schema."""
    try:
        resp = requests.get(
            f"{API_BASE}/tracks/{track_id}",
            headers=_auth_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise SpotifyError(f"Couldn't reach Spotify: {exc}") from exc

    if resp.status_code == 404:
        raise SpotifyError("That Spotify track couldn't be found.")
    if resp.status_code != 200:
        raise SpotifyError("Spotify lookup failed. Try again in a moment.")

    return map_track_to_metadata(resp.json())


def _summarize(item):
    """Lightweight result for the search results list."""
    return {
        "id": item.get("id"),
        "name": item.get("name", "Unknown"),
        "artists": ", ".join(a["name"] for a in item.get("artists", [])) or "Unknown",
        "album": item.get("album", {}).get("name", ""),
        "isrc": item.get("external_ids", {}).get("isrc", ""),
        "url": item.get("external_urls", {}).get("spotify", ""),
    }


def map_track_to_metadata(track):
    """Map a Spotify track object to MetaCheck's CSV/record schema.

    Only fields Spotify reliably exposes are filled. composer, publisher,
    genre, ai_generated and language are intentionally left blank — Spotify
    doesn't provide them, and MetaCheck flagging them is the whole point.
    """
    album = track.get("album", {})
    return {
        "title": track.get("name", ""),
        "artist": ", ".join(a["name"] for a in track.get("artists", [])),
        "isrc": track.get("external_ids", {}).get("isrc", ""),
        "composer": "",
        "publisher": "",
        "genre": "",
        "release_date": _normalize_date(album.get("release_date", ""), album.get("release_date_precision", "")),
        "explicit": "true" if track.get("explicit") else "false",
        "ai_generated": "",
        "language": "",
        "streams": "",
        "_spotify_url": track.get("external_urls", {}).get("spotify", ""),
        "_spotify_popularity": track.get("popularity"),
    }


def _normalize_date(value, precision):
    """Spotify dates can be YYYY, YYYY-MM, or YYYY-MM-DD. Pad to a full date so
    the validator's format check reflects the artist's submission, not
    Spotify's date precision."""
    if not value:
        return ""
    if precision == "year" or len(value) == 4:
        return f"{value}-01-01"
    if precision == "month" or len(value) == 7:
        return f"{value}-01"
    return value

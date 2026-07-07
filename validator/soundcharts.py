"""Soundcharts enrichment — real per-platform stream counts by ISRC.

Optional PAID integration. Soundcharts is the analytics API that (unlike
Spotify's own API) exposes per-platform play/stream counts AND covers African
DSPs — Audiomack plays, Boomplay — alongside the global ones. When
SOUNDCHARTS_APP_ID and SOUNDCHARTS_API_KEY are set, MetaCheck replaces its
modeled market-share split with these real numbers; without them it falls back
to the model, so the app still works with nothing configured.

Flow: ISRC -> song UUID (/api/v2.25/song/by-isrc/{isrc})
           -> latest audience per platform (/api/v2/song/{uuid}/audience/{code})

Docs: https://developers.soundcharts.com

Honest scope: Soundcharts measures Spotify streams and Audiomack plays (both
relevant here). It does NOT expose Apple Music play counts (Apple doesn't
publish them), so Apple stays modeled rather than faked — see royalty.py.
"""
import os

import requests

DEFAULT_API_BASE = "https://customer.api.soundcharts.com"
TIMEOUT = 10

# MetaCheck platform name -> Soundcharts platform code. Only platforms for which
# Soundcharts actually returns a stream/play count are listed. Apple Music is
# intentionally omitted (no real per-platform play count is available anywhere).
PLATFORM_CODES = {
    "Spotify": "spotify",
    "Audiomack": "audiomack",
}


class SoundchartsError(Exception):
    """Raised on a Soundcharts request failure."""


def is_available():
    """True if Soundcharts credentials are configured."""
    return bool(os.getenv("SOUNDCHARTS_APP_ID")) and bool(os.getenv("SOUNDCHARTS_API_KEY"))


def streams_by_isrc(isrc):
    """Return {MetaCheck platform: latest stream/play count} for an ISRC.

    Returns None when unavailable, misconfigured, or the song isn't found, so
    the caller can fall back to the modeled split. Never raises into the
    pipeline — enrichment must not break validation.
    """
    clean = (isrc or "").strip().upper()
    if not clean or not is_available():
        return None
    try:
        song = _get(f"/api/v2.25/song/by-isrc/{clean}")
        uuid = _song_uuid(song)
        if not uuid:
            return None
        counts = {}
        for platform, code in PLATFORM_CODES.items():
            value = _latest_audience(_get(f"/api/v2/song/{uuid}/audience/{code}"))
            if value is not None:
                counts[platform] = value
        return counts or None
    except SoundchartsError:
        return None


def _base():
    return os.getenv("SOUNDCHARTS_API_BASE", DEFAULT_API_BASE).rstrip("/")


def _headers():
    return {
        "x-app-id": os.getenv("SOUNDCHARTS_APP_ID", ""),
        "x-api-key": os.getenv("SOUNDCHARTS_API_KEY", ""),
        "Accept": "application/json",
    }


def _get(path, params=None):
    try:
        resp = requests.get(f"{_base()}{path}", params=params or {}, headers=_headers(), timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise SoundchartsError(str(exc)) from exc
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise SoundchartsError(f"Soundcharts returned HTTP {resp.status_code}")
    return resp.json()


# --- Pure parsing helpers (unit-testable without network) ---

def _song_uuid(song_payload):
    """Extract the Soundcharts song UUID from a by-isrc response."""
    if not isinstance(song_payload, dict):
        return None
    obj = song_payload.get("object") or song_payload.get("data") or song_payload
    if isinstance(obj, dict):
        return obj.get("uuid")
    return None


def _latest_audience(audience_payload):
    """Extract the most recent audience value from an audience response.

    Soundcharts returns a collection of {date, value} plot points; we take the
    value at the latest date. Returns None on any missing/empty payload.
    """
    if not isinstance(audience_payload, dict):
        return None
    items = audience_payload.get("items") or audience_payload.get("data") or []
    latest = None
    for it in items:
        if not isinstance(it, dict):
            continue
        value = it.get("value")
        if value is None:
            continue
        date = it.get("date", "")
        if latest is None or date >= latest[0]:
            latest = (date, value)
    if latest is None:
        return None
    try:
        return int(latest[1])
    except (TypeError, ValueError):
        return None

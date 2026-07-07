"""MusicBrainz enrichment — look up real composer/work data by ISRC.

MusicBrainz is the open, free music encyclopedia. Given an ISRC (which we get
from Spotify or the user), it can often tell us the underlying composition and
its writers/composers — data Spotify's API does NOT expose.

This powers the strongest demo line: "Spotify gives the ISRC; MusicBrainz knows
the composer; but the distribution submission left it blank — so no CMO can
match the royalties to the artist."

Chain: ISRC -> recording -> work (the composition) -> writer/composer artists.

No API key required. MusicBrainz asks callers to send a descriptive User-Agent
and stay at ~1 request/second, both of which we honour.
"""
import time

import requests

API_BASE = "https://musicbrainz.org/ws/2"
USER_AGENT = "MetaCheck/0.1 (https://github.com/osmanmahdi1728/metacheck)"
TIMEOUT = 10
# MusicBrainz rate limit is ~1 req/sec; stay just under to be safe.
RATE_DELAY = 1.1

# Relationship types on a work that credit the songwriter side.
WRITER_RELATION_TYPES = {"composer", "writer", "lyricist", "songwriter"}


class MusicBrainzError(Exception):
    """Raised on a MusicBrainz request failure."""


def _get(path, params):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    query = {"fmt": "json"}
    query.update(params)
    try:
        resp = requests.get(f"{API_BASE}/{path}", params=query, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise MusicBrainzError(str(exc)) from exc
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise MusicBrainzError(f"MusicBrainz returned HTTP {resp.status_code}")
    return resp.json()


def enrich_by_isrc(isrc):
    """Look up composer/work data for an ISRC.

    Returns a dict:
      {found, recording_title, artists, composers: [...], work_titles: [...]}
    Always returns a dict; `found` is False on any miss or error (never raises
    into the caller, so enrichment can't break validation).
    """
    empty = {"found": False, "recording_title": None, "artists": None, "composers": [], "work_titles": []}
    clean = (isrc or "").strip().upper()
    if not clean:
        return empty

    try:
        isrc_payload = _get(f"isrc/{clean}", {"inc": "artist-credits"})
        recording = _first_recording(isrc_payload)
        if recording is None:
            return empty

        composers, work_titles = [], []
        time.sleep(RATE_DELAY)
        rec_payload = _get(f"recording/{recording['id']}", {"inc": "work-rels"})
        for work_id in _work_ids(rec_payload):
            time.sleep(RATE_DELAY)
            work_payload = _get(f"work/{work_id}", {"inc": "artist-rels"})
            if work_payload and work_payload.get("title"):
                work_titles.append(work_payload["title"])
            for name in _composers_from_work(work_payload):
                if name not in composers:
                    composers.append(name)

        return {
            "found": True,
            "recording_title": recording["title"],
            "artists": recording["artists"],
            "composers": composers,
            "work_titles": work_titles,
        }
    except MusicBrainzError:
        return {**empty, "error": "MusicBrainz lookup failed"}


# --- Pure parsing helpers (unit-testable without network) ---

def _first_recording(isrc_payload):
    """Extract the first recording (id, title, artists) from an ISRC payload."""
    if not isrc_payload:
        return None
    recordings = isrc_payload.get("recordings") or []
    if not recordings:
        return None
    rec = recordings[0]
    artists = ", ".join(
        ac.get("name", "")
        for ac in rec.get("artist-credit", [])
        if isinstance(ac, dict) and ac.get("name")
    )
    return {"id": rec.get("id"), "title": rec.get("title"), "artists": artists or None}


def _work_ids(recording_payload):
    """Return work IDs linked to a recording (performance relationships)."""
    if not recording_payload:
        return []
    ids = []
    for rel in recording_payload.get("relations", []):
        if rel.get("target-type") == "work" and rel.get("work", {}).get("id"):
            ids.append(rel["work"]["id"])
    return ids


def _composers_from_work(work_payload):
    """Return writer/composer names credited on a work."""
    if not work_payload:
        return []
    names = []
    for rel in work_payload.get("relations", []):
        if rel.get("type", "").lower() in WRITER_RELATION_TYPES:
            name = rel.get("artist", {}).get("name")
            if name:
                names.append(name)
    return names

import re
from datetime import datetime, date

VALID_GENRES = [
    "Afro House", "Amapiano", "Afrobeats", "Afropop", "Highlife",
    "Pop", "Hip-Hop", "R&B", "Electronic", "Dance", "World",
    "Jazz", "Classical", "Rock", "Gospel", "Reggae",
]

VALID_LANGUAGES = ["en", "fr", "pt", "sw", "yo", "ha", "am", "ar", "es"]

# Codes that represent hard errors (as opposed to warnings). Used by the
# report template to style each issue card correctly.
ERROR_CODES = {
    "TITLE_MISSING",
    "TITLE_TOO_LONG",
    "ARTIST_MISSING",
    "ISRC_MISSING",
    "ISRC_INVALID_FORMAT",
    "COMPOSER_MISSING",
    "GENRE_MISSING",
    "RELEASE_DATE_MISSING",
    "RELEASE_DATE_PAST",
    "RELEASE_DATE_FORMAT",
    "EXPLICIT_FLAG_MISSING",
    "AI_FLAG_MISSING",
}


def validate_track(row):
    errors = []
    warnings = []

    # Title
    if not row.get("title") or str(row["title"]).strip() == "":
        errors.append({"field": "title", "code": "TITLE_MISSING", "detail": "Track title is missing."})
    elif len(str(row["title"])) > 255:
        errors.append({"field": "title", "code": "TITLE_TOO_LONG", "detail": "Title exceeds 255 characters."})

    # Artist
    artist = str(row.get("artist", "")).strip()
    if not artist or artist.lower() == "nan":
        errors.append({"field": "artist", "code": "ARTIST_MISSING", "detail": "Artist name is missing."})
    elif "feat." in artist.lower() or "ft." in artist.lower():
        warnings.append({"field": "artist", "code": "ARTIST_FEAT_IN_NAME", "detail": "Featuring artist detected in main artist field. Spotify and Apple Music require this in the title field instead."})

    # ISRC
    isrc = str(row.get("isrc", "")).strip()
    isrc_pattern = re.compile(r'^[A-Z]{2}-[A-Z0-9]{3}-\d{2}-\d{5}$')
    if not isrc or isrc.lower() == "nan":
        errors.append({"field": "isrc", "code": "ISRC_MISSING", "detail": "ISRC code is missing. This is required for royalty tracking on all platforms."})
    elif not isrc_pattern.match(isrc):
        errors.append({"field": "isrc", "code": "ISRC_INVALID_FORMAT", "detail": f"ISRC '{isrc}' does not match the required format (e.g. QZ-ES1-26-00001)."})

    # Composer
    composer = str(row.get("composer", "")).strip()
    if not composer or composer.lower() == "nan":
        errors.append({"field": "composer", "code": "COMPOSER_MISSING", "detail": "Composer/songwriter field is empty. This is required for mechanical royalty registration at CMOs like SOCAN, ASCAP, and MCSK."})

    # Publisher
    publisher = str(row.get("publisher", "")).strip()
    if not publisher or publisher.lower() == "nan":
        warnings.append({"field": "publisher", "code": "PUBLISHER_MISSING", "detail": "No publisher listed. If you self-publish, enter your name or your publishing entity. Missing publisher info can delay sync licensing opportunities."})

    # Genre
    genre = str(row.get("genre", "")).strip()
    if not genre or genre.lower() == "nan":
        errors.append({"field": "genre", "code": "GENRE_MISSING", "detail": "Genre is missing. This is required for DSP categorization and playlist placement."})
    elif genre not in VALID_GENRES:
        warnings.append({"field": "genre", "code": "GENRE_NOT_STANDARD", "detail": f"'{genre}' is not in the standard DSP genre list. This may cause miscategorization on Spotify and Apple Music."})

    # Release date
    release_date_str = str(row.get("release_date", "")).strip()
    if not release_date_str or release_date_str.lower() == "nan":
        errors.append({"field": "release_date", "code": "RELEASE_DATE_MISSING", "detail": "Release date is missing."})
    else:
        try:
            release_date = datetime.strptime(release_date_str, "%Y-%m-%d").date()
            today = date.today()
            if release_date <= today:
                errors.append({"field": "release_date", "code": "RELEASE_DATE_PAST", "detail": f"Release date {release_date_str} is in the past or today. Most DSPs require at least 2 business days lead time."})
        except ValueError:
            errors.append({"field": "release_date", "code": "RELEASE_DATE_FORMAT", "detail": f"Release date '{release_date_str}' is not in YYYY-MM-DD format."})

    # Explicit flag
    explicit = str(row.get("explicit", "")).strip().lower()
    if explicit not in ["true", "false"]:
        errors.append({"field": "explicit", "code": "EXPLICIT_FLAG_MISSING", "detail": "Explicit content flag must be set to true or false. Missing flag can cause Spotify and Apple Music to reject the submission."})

    # AI-generated flag
    ai_flag = str(row.get("ai_generated", "")).strip().lower()
    if ai_flag not in ["true", "false"]:
        errors.append({"field": "ai_generated", "code": "AI_FLAG_MISSING", "detail": "AI-generated content flag is required by Spotify, Apple Music, and TikTok as of 2024. Omitting this can trigger a distribution hold."})

    # Language
    language = str(row.get("language", "")).strip().lower()
    if not language or language == "nan":
        warnings.append({"field": "language", "code": "LANGUAGE_MISSING", "detail": "Language field is missing. This affects playlist eligibility and regional recommendation algorithms."})
    elif language not in VALID_LANGUAGES:
        warnings.append({"field": "language", "code": "LANGUAGE_NOT_STANDARD", "detail": f"'{language}' is not a recognized ISO 639-1 language code."})

    status = "PASS" if not errors else "FAIL"
    return {"status": status, "errors": errors, "warnings": warnings}

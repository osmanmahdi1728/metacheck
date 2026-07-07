"""Optional GPT-4o-mini layer that rewrites validator messages in plain,
friendly language for non-technical artists.

Shared by the CLI (main.py) and the web app (app.py). If no OPENAI_API_KEY is
configured, or the API call fails, it transparently falls back to the built-in
(already readable) messages — so the product always works offline.
"""
import json
import os

_client = None
_client_loaded = False


def is_available():
    """True if an OpenAI key is configured (so callers can show a toggle)."""
    key = os.getenv("OPENAI_API_KEY")
    return bool(key) and key != "your_key_here"


def _get_client():
    global _client, _client_loaded
    if _client_loaded:
        return _client
    _client_loaded = True
    if not is_available():
        _client = None
        return None
    try:
        from openai import OpenAI

        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    except Exception:
        _client = None
    return _client


def humanize_errors(track_title, issues):
    """Rewrite each issue's `detail` in plain language, preserving field/code.

    Preserving `code` matters: downstream royalty estimation keys off codes.
    Falls back to the original issues on any failure.
    """
    if not issues:
        return []

    client = _get_client()
    if client is None:
        return issues

    issues_text = json.dumps({"issues": issues}, indent=2)
    prompt = f"""
You are a music distribution assistant helping an independent artist fix their metadata before release.

Track: "{track_title}"

The following validation issues were found:
{issues_text}

For each issue, rewrite the "detail" field in plain, friendly language that a non-technical artist can understand and act on.
Keep each message under 2 sentences. Do NOT change the "field" or "code" values.
Return a JSON object with an "issues" array using the same structure but updated "detail" fields only.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        rewritten = result.get("issues", issues)
        # Guard: keep original codes/fields if the model dropped them.
        if len(rewritten) == len(issues):
            for original, new in zip(issues, rewritten):
                new.setdefault("field", original.get("field"))
                new.setdefault("code", original.get("code"))
            return rewritten
        return issues
    except Exception:
        return issues

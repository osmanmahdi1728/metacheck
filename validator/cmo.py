"""CMO (Collective Management Organization) registration check.

Cross-references a track's ISRC against collective royalty databases
(SOCAN, ASCAP, MCSK, SACEM, PRS, ...) to confirm the work is actually
registered for royalty collection — not just that the ISRC field is filled.

DEMO NOTE: public CMO lookup APIs are inconsistent (and mostly non-existent
for African CMOs like MCSK), so for the demo this reads a local mock registry
CSV (data/cmo_registry.csv). Swap `_load_registry` for real API calls when
partnerships/APIs are available. The rest of the pipeline is unchanged.
"""
import csv
import os

from .rules import normalize_isrc

_REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cmo_registry.csv")

_registry_cache = None


def _load_registry():
    """Load {isrc: {cmo, work_title, registered_composer}} from the mock CSV.

    Keys are normalized (hyphens stripped) so lookups match regardless of ISRC
    formatting.
    """
    global _registry_cache
    if _registry_cache is not None:
        return _registry_cache

    registry = {}
    if os.path.exists(_REGISTRY_PATH):
        with open(_REGISTRY_PATH, newline="") as f:
            for row in csv.DictReader(f):
                isrc = normalize_isrc(row.get("isrc"))
                if isrc:
                    registry[isrc] = {
                        "cmo": (row.get("cmo") or "").strip(),
                        "work_title": (row.get("work_title") or "").strip(),
                        "registered_composer": (row.get("registered_composer") or "").strip(),
                    }
    _registry_cache = registry
    return registry


def check_registration(isrc):
    """Look up an ISRC in the CMO registry.

    Returns:
        dict: {registered: bool, cmo: str|None, registered_composer: str|None}
    """
    registry = _load_registry()
    record = registry.get(normalize_isrc(isrc))
    if record:
        return {
            "registered": True,
            "cmo": record["cmo"],
            "registered_composer": record["registered_composer"],
        }
    return {"registered": False, "cmo": None, "registered_composer": None}

"""Portuguese-to-English translations and normalization helpers."""

from __future__ import annotations

import re
import unicodedata

from .config import ACTIVITY_MAP, CROP_MAP, STATE_MAP


def normalize_crop(raw: str) -> str | None:
    """Translate a Portuguese crop name to its English key.

    Handles whitespace variants and ordinal suffixes.
    Returns *None* if the crop is not recognized.
    """
    cleaned = " ".join(raw.strip().split())  # collapse whitespace
    if cleaned in CROP_MAP:
        return CROP_MAP[cleaned]

    # Try stripping accents for fuzzy match
    nfkd = unicodedata.normalize("NFKD", cleaned)
    ascii_cleaned = "".join(c for c in nfkd if not unicodedata.combining(c))
    for pt_name, en_name in CROP_MAP.items():
        nfkd_pt = unicodedata.normalize("NFKD", pt_name)
        ascii_pt = "".join(c for c in nfkd_pt if not unicodedata.combining(c))
        if ascii_cleaned.lower() == ascii_pt.lower():
            return en_name

    return None


def normalize_activity(raw: str) -> str | None:
    """Translate an activity string like 'Colheita *' to 'harvest'.

    Strips trailing asterisks and whitespace.
    """
    cleaned = re.sub(r"[\s*]+$", "", raw.strip())
    if cleaned in ACTIVITY_MAP:
        return ACTIVITY_MAP[cleaned]

    # Case-insensitive fallback
    for pt_name, en_name in ACTIVITY_MAP.items():
        if cleaned.lower() == pt_name.lower():
            return en_name

    return None


def normalize_state(raw: str) -> str | None:
    """Return the ISO 3166-2:BR code for a state name.

    Returns *None* if not recognized.
    """
    cleaned = raw.strip()
    if cleaned in STATE_MAP:
        return STATE_MAP[cleaned]

    # Try collapsing multiple spaces
    collapsed = " ".join(cleaned.split())
    if collapsed in STATE_MAP:
        return STATE_MAP[collapsed]

    # Case-insensitive + accent-insensitive fallback
    def _ascii_lower(s: str) -> str:
        nfkd = unicodedata.normalize("NFKD", s)
        return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

    target = _ascii_lower(cleaned)
    for pt_name, code in STATE_MAP.items():
        if _ascii_lower(pt_name) == target:
            return code

    return None


def state_code_to_name(code: str) -> str:
    """Return the canonical English state name for a 2-letter code."""
    from .config import STATE_CODE_TO_NAME

    return STATE_CODE_TO_NAME.get(code.upper(), code)

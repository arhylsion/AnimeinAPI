from __future__ import annotations

import re
import unicodedata

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_EPISODE_SLUG_RE = re.compile(r"^(.+)-episode-([a-z0-9]+)$")


def slugify(text: str) -> str:
    """Sanitize an arbitrary title into a clean ASCII kebab-case slug."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return _NON_ALNUM_RE.sub("-", ascii_text).strip("-")


def is_numeric_id(value: str) -> bool:
    """Return True if the identifier is a non-empty numeric ID string."""
    s = value.strip()
    return bool(s) and s.isdigit()


def make_episode_slug(
    anime_slug: str,
    episode_index: str,
    disambiguator: str | None = None,
) -> str:
    """Format a flat episode slug as '{anime_slug}-episode-{index}'."""
    clean_index = slugify(str(episode_index)) or str(episode_index).strip()
    base = f"{anime_slug}-episode-{clean_index}"
    if disambiguator:
        clean_dis = slugify(str(disambiguator)) or str(disambiguator).strip()
        if clean_dis:
            return f"{base}-{clean_dis}"
    return base


def parse_episode_slug(slug: str) -> tuple[str, str] | None:
    """Extract (anime_slug, episode_index) from '{anime_slug}-episode-{index}'."""
    normalized = slug.strip().lower()
    match = _EPISODE_SLUG_RE.match(normalized)
    if not match:
        return None
    return match.group(1), match.group(2)

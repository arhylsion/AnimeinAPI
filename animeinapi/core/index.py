from __future__ import annotations

from .slug import make_episode_slug, slugify


class SlugIndex:
    """Bidirectional in-memory index mapping sanitized character slugs to numeric IDs."""

    def __init__(self) -> None:
        self._anime_slug_to_id: dict[str, str] = {}
        self._anime_id_to_slug: dict[str, str] = {}
        self._ep_slug_to_id: dict[str, str] = {}
        self._ep_id_to_slug: dict[str, str] = {}
        self._anime_ep_index_to_id: dict[tuple[str, str], str] = {}

    def register_anime(self, anime_id: str, title: str, year: str | None = None) -> str:
        """Register an anime and return its unique sanitized slug."""
        aid = str(anime_id).strip()
        existing = self._anime_id_to_slug.get(aid)
        if existing:
            return existing

        base = slugify(title) or aid
        candidate = base

        owner = self._anime_slug_to_id.get(candidate)
        if owner is not None and owner != aid:
            clean_year = slugify(str(year)) if year else ""
            if clean_year:
                year_candidate = f"{base}-{clean_year}"
                year_owner = self._anime_slug_to_id.get(year_candidate)
                if year_owner is None or year_owner == aid:
                    candidate = year_candidate
                else:
                    candidate = f"{base}-{aid}"
            else:
                candidate = f"{base}-{aid}"

        self._anime_slug_to_id[candidate] = aid
        self._anime_id_to_slug[aid] = candidate

        # Only register the synthetic '{base}-{id}' alias if it does not shadow an existing key
        alias_with_id = f"{base}-{aid}"
        if alias_with_id not in self._anime_slug_to_id:
            self._anime_slug_to_id[alias_with_id] = aid
        return candidate

    def register_episode(
        self,
        episode_id: str,
        episode_index: str | int | None,
        anime_id: str | None = None,
        anime_slug: str | None = None,
    ) -> str | None:
        """Register an episode and return its unique flat slug if anime slug is known."""
        eid = str(episode_id).strip()
        if episode_index is None:
            return None
        if not isinstance(episode_index, str):
            episode_index = str(episode_index)
        raw_episode_index = episode_index.strip()
        idx_norm = slugify(raw_episode_index) or raw_episode_index
        aid = str(anime_id).strip() if anime_id else None

        if aid and idx_norm:
            self._anime_ep_index_to_id[(aid, idx_norm)] = eid
            self._anime_ep_index_to_id[(aid, raw_episode_index)] = eid

        existing = self._ep_id_to_slug.get(eid)
        if existing:
            return existing

        resolved_anime_slug = anime_slug or (self._anime_id_to_slug.get(aid) if aid else None)
        if not resolved_anime_slug or not idx_norm:
            return None

        ep_slug = make_episode_slug(resolved_anime_slug, idx_norm)
        ep_owner = self._ep_slug_to_id.get(ep_slug)
        if ep_owner is not None and ep_owner != eid:
            # Disambiguate episode slug collision with episode ID
            ep_slug = f"{ep_slug}-{eid}"

        self._ep_slug_to_id[ep_slug] = eid
        self._ep_id_to_slug[eid] = ep_slug
        return ep_slug

    def get_anime_id(self, slug: str) -> str | None:
        key = slugify(slug)
        return self._anime_slug_to_id.get(key)

    def get_anime_slug(self, anime_id: str) -> str | None:
        return self._anime_id_to_slug.get(str(anime_id).strip())

    def get_episode_id(self, slug: str) -> str | None:
        key = slugify(slug)
        return self._ep_slug_to_id.get(key)

    def get_episode_slug(self, episode_id: str) -> str | None:
        return self._ep_id_to_slug.get(str(episode_id).strip())

    def get_episode_id_by_index(self, anime_id: str, episode_index: str) -> str | None:
        aid = str(anime_id).strip()
        raw_idx = str(episode_index).strip()
        norm_idx = slugify(raw_idx) or raw_idx
        return self._anime_ep_index_to_id.get((aid, raw_idx)) or self._anime_ep_index_to_id.get(
            (aid, norm_idx)
        )

    @property
    def anime_count(self) -> int:
        return len(self._anime_id_to_slug)

    @property
    def episode_count(self) -> int:
        return len(self._ep_id_to_slug)

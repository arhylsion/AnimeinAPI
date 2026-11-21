from __future__ import annotations

from pydantic import BaseModel, Field

from .anime import AnimeSummary, Slider


class Genre(BaseModel):
    id: str
    name: str
    image: str | None = None
    group: str | None = None


class HomeData(BaseModel):
    slider: list[Slider] = Field(default_factory=list)
    hot: list[AnimeSummary] = Field(default_factory=list)
    new: list[AnimeSummary] = Field(default_factory=list)
    today: list[AnimeSummary] = Field(default_factory=list)
    popular: list[AnimeSummary] = Field(default_factory=list)
    waiting: list[AnimeSummary] = Field(default_factory=list)
    random: list[AnimeSummary] = Field(default_factory=list)
    trailer: list[AnimeSummary] = Field(default_factory=list)
    setup_fyp_flag: str | None = None
    setup_fyp_name: str | None = None


class CatalogStats(BaseModel):
    total_anime: int = Field(..., description="Total anime titles in the catalog")
    total_episodes: str = Field(..., description="Estimated total available episodes")
    total_genres: int = Field(..., description="Total genre and theme categories")
    last_updated: str = Field(..., description="Timestamp of last statistics check (WIB)")

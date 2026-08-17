from datetime import date, time

from pydantic import BaseModel

from app.schemas.common import ContentTypeAPI


class EpisodeOut(BaseModel):
    id: int
    season_number: int
    episode_number: int
    title: str | None
    overview: str | None
    air_date: date | None
    air_time: time | None
    watched: bool = False

    model_config = {"from_attributes": True}


class SeasonOut(BaseModel):
    id: int
    season_number: int
    episode_count: int | None
    air_date: date | None
    episodes: list[EpisodeOut] = []
    fully_watched: bool = False

    model_config = {"from_attributes": True}


class ProviderOut(BaseModel):
    name: str
    logo_path: str | None
    offer_type: str
    country_code: str

    model_config = {"from_attributes": True}


class ShowDetailOut(BaseModel):
    id: int
    content_type: ContentTypeAPI = ContentTypeAPI.SHOW
    tmdb_id: int | None
    tvmaze_id: int | None
    title: str
    original_title: str | None
    first_air_date: date | None
    airing_status: str
    overview: str | None
    poster_path: str | None
    backdrop_path: str | None
    vote_average: float | None
    genres: list[str] = []
    seasons: list[SeasonOut] = []
    providers: list[ProviderOut] = []
    user_status: str | None = None

    model_config = {"from_attributes": True}


class MovieDetailOut(BaseModel):
    id: int
    content_type: ContentTypeAPI = ContentTypeAPI.MOVIE
    tmdb_id: int | None
    title: str
    original_title: str | None
    release_date: date | None
    runtime_minutes: int | None
    overview: str | None
    poster_path: str | None
    backdrop_path: str | None
    vote_average: float | None
    genres: list[str] = []
    providers: list[ProviderOut] = []
    user_status: str | None = None

    model_config = {"from_attributes": True}


class SetStatusRequest(BaseModel):
    status: str
    personal_rating: float | None = None
    notes: str | None = None

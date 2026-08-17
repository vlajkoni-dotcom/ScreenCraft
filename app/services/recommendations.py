from collections import Counter
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.show import Show
from app.models.user_content import UserContent
from app.schemas.common import ContentTypeAPI
from app.services.tmdb import tmdb_client

POSITIVE_STATUSES = ["watching", "watchlist", "watched"]


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").year
    except ValueError:
        return None


async def _build_genre_profile(db: AsyncSession) -> Counter:
    """Frekvencija zanrova iz serija koje pratis/gledas/imas na listi - osnova ukusa."""
    result = await db.execute(
        select(UserContent.content_id).where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.status.in_(POSITIVE_STATUSES),
        )
    )
    show_ids = [row[0] for row in result.all()]
    if not show_ids:
        return Counter()

    result = await db.execute(
        select(Show).where(Show.id.in_(show_ids)).options(selectinload(Show.genres))
    )
    shows = result.scalars().all()

    profile: Counter = Counter()
    for show in shows:
        for genre in show.genres:
            if genre.tmdb_genre_id:
                profile[genre.tmdb_genre_id] += 1
    return profile


async def _get_seed_shows(db: AsyncSession, limit: int = 3) -> list[Show]:
    """Nekoliko 'seed' serija (najnovije azurirane u watching/watched) za TMDB recommendations."""
    result = await db.execute(
        select(UserContent)
        .where(
            UserContent.content_type == ContentTypeAPI.SHOW.value,
            UserContent.status.in_(["watching", "watched"]),
        )
        .order_by(UserContent.updated_at.desc())
        .limit(limit)
    )
    user_items = result.scalars().all()
    show_ids = [uc.content_id for uc in user_items]
    if not show_ids:
        return []
    result = await db.execute(select(Show).where(Show.id.in_(show_ids)))
    return list(result.scalars().all())


def _genre_match_score(candidate_genre_ids: list[int], profile: Counter) -> float:
    if not profile or not candidate_genre_ids:
        return 50.0
    overlap_weight = sum(profile.get(gid, 0) for gid in candidate_genre_ids)
    max_single = max(profile.values())
    return round(min(100, (overlap_weight / max_single) * 100), 1)


def _newness_score(first_air_date: str | None) -> float:
    year = _year_from_date(first_air_date)
    if year is None:
        return 40.0
    current_year = date.today().year
    age = current_year - year
    if age <= 0:
        return 100.0
    if age >= 6:
        return 20.0
    return round(100 - age * 13.3, 1)


async def get_recommendations(db: AsyncSession, limit: int = 10) -> list[dict]:
    """
    Vladimir Score - preporuke bazirane na kombinaciji: similarity (TMDB
    recommendations za tvoje serije), genre match (tvoj zanrovski profil),
    rating, popularnost, newness, i dostupnost u Srbiji.
    """
    seed_shows = await _get_seed_shows(db)
    if not seed_shows:
        return []

    profile = await _build_genre_profile(db)

    result = await db.execute(
        select(UserContent.content_id).where(UserContent.content_type == ContentTypeAPI.SHOW.value)
    )
    known_local_ids = [row[0] for row in result.all()]
    known_tmdb_ids: set[int] = set()
    if known_local_ids:
        result = await db.execute(select(Show.tmdb_id).where(Show.id.in_(known_local_ids)))
        known_tmdb_ids = {row[0] for row in result.all() if row[0]}

    candidates: dict[int, dict] = {}
    similarity_hits: Counter = Counter()
    for seed in seed_shows:
        if not seed.tmdb_id:
            continue
        recs = await tmdb_client.get_tv_recommendations(seed.tmdb_id)
        for r in recs:
            tmdb_id = r.get("id")
            if not tmdb_id or tmdb_id in known_tmdb_ids:
                continue
            candidates[tmdb_id] = r
            similarity_hits[tmdb_id] += 1

    if not candidates:
        return []

    max_hits = max(similarity_hits.values()) if similarity_hits else 1
    settings = get_settings()

    scored = []
    for tmdb_id, r in candidates.items():
        similarity = round((similarity_hits[tmdb_id] / max_hits) * 100, 1)
        genre_match = _genre_match_score(r.get("genre_ids", []), profile)
        rating = round((r.get("vote_average") or 0) * 10, 1)
        popularity = round(min(100, (r.get("popularity") or 0) / 3), 1)
        newness = _newness_score(r.get("first_air_date"))

        breakdown = {
            "similarity": similarity,
            "genre_match": genre_match,
            "rating": rating,
            "popularity": popularity,
            "newness": newness,
        }
        weighted = (
            similarity * 0.30
            + genre_match * 0.25
            + rating * 0.15
            + popularity * 0.10
            + newness * 0.10
            + 50 * 0.10
        )
        scored.append((weighted, tmdb_id, r, breakdown))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_candidates = scored[: limit * 2]

    out = []
    for weighted, tmdb_id, r, breakdown in top_candidates:
        if len(out) >= limit:
            break
        providers = await tmdb_client.get_tv_watch_providers(tmdb_id)
        available_rs = settings.default_region in providers
        breakdown["availability_serbia"] = 100.0 if available_rs else 0.0

        final_score = round(
            breakdown["similarity"] * 0.30
            + breakdown["genre_match"] * 0.25
            + breakdown["rating"] * 0.15
            + breakdown["popularity"] * 0.10
            + breakdown["newness"] * 0.10
            + breakdown["availability_serbia"] * 0.10,
            1,
        )

        out.append({
            "tmdb_id": tmdb_id,
            "title": r.get("name", ""),
            "poster_path": r.get("poster_path"),
            "overview": r.get("overview"),
            "year": _year_from_date(r.get("first_air_date")),
            "vladimir_score": final_score,
            "score_breakdown": breakdown,
            "available_in_serbia": available_rs,
        })

    out.sort(key=lambda x: x["vladimir_score"], reverse=True)
    return out

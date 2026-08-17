from datetime import datetime

from rapidfuzz import fuzz

from app.schemas.common import ContentTypeAPI
from app.schemas.search import IdentificationResult, SearchCandidate
from app.services.tmdb import tmdb_client

# Ako je top TMDB kandidat >= ovog praga slicnosti naziva, i nema drugog
# kandidata blizu njega, smatramo identifikaciju pouzdanom.
AUTO_MATCH_SCORE_THRESHOLD = 90
# Minimalna razlika (u poenima slicnosti) izmedju #1 i #2 kandidata da bismo
# bili sigurni da ne mesamo dva slicna naslova (npr. "The Killing" vs "Killing Eve").
AUTO_MATCH_MARGIN = 15


def _year_from_date(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").year
    except ValueError:
        return None


def _tmdb_tv_to_candidate(item: dict) -> SearchCandidate:
    return SearchCandidate(
        content_type=ContentTypeAPI.SHOW,
        tmdb_id=item.get("id"),
        title=item.get("name", ""),
        original_title=item.get("original_name"),
        year=_year_from_date(item.get("first_air_date")),
        overview=item.get("overview"),
        poster_path=item.get("poster_path"),
        vote_average=item.get("vote_average"),
        popularity=item.get("popularity"),
    )


def _tmdb_movie_to_candidate(item: dict) -> SearchCandidate:
    return SearchCandidate(
        content_type=ContentTypeAPI.MOVIE,
        tmdb_id=item.get("id"),
        title=item.get("title", ""),
        original_title=item.get("original_title"),
        year=_year_from_date(item.get("release_date")),
        overview=item.get("overview"),
        poster_path=item.get("poster_path"),
        vote_average=item.get("vote_average"),
        popularity=item.get("popularity"),
    )


async def identify_title(
    query_title: str, content_type: ContentTypeAPI = ContentTypeAPI.SHOW
) -> IdentificationResult:
    """
    Pokusava da pronadje tacan TMDB unos za dat, potencijalno nepouzdan naziv.

    Pravilo (iz specifikacije): NIKADA ne binduj automatski osim ako smo
    stvarno sigurni. Ako je nejasno, vracamo kandidate i trazimo potvrdu od
    korisnika - ne pogadjamo i ne izmisljamo.
    """
    if content_type == ContentTypeAPI.SHOW:
        raw_results = await tmdb_client.search_tv(query_title)
        candidates = [_tmdb_tv_to_candidate(r) for r in raw_results[:5]]
    else:
        raw_results = await tmdb_client.search_movie(query_title)
        candidates = [_tmdb_movie_to_candidate(r) for r in raw_results[:5]]

    if not candidates:
        return IdentificationResult(
            query_title=query_title,
            confident=False,
            candidates=[],
            message="Could not confidently identify this title. Nema rezultata u TMDB pretrazi.",
        )

    query_norm = query_title.strip().lower()
    scored = []
    for c in candidates:
        score = fuzz.token_sort_ratio(query_norm, (c.title or "").lower())
        if c.original_title:
            score = max(score, fuzz.token_sort_ratio(query_norm, c.original_title.lower()))
        # Egzaktan poklapanje naziva (case-insensitive) je jak signal koji fuzzy
        # ratio ume da potceni kod kratkih naslova sličnih drugom kandidatu
        # (npr. "Reacher" vs "Preacher") - zato ga eksplicitno forsiramo na 100.
        if query_norm == (c.title or "").lower() or (
            c.original_title and query_norm == c.original_title.lower()
        ):
            score = 100
        c.confidence = round(score, 1)
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    ranked_candidates = [c for _, c in scored]

    top_score = scored[0][0]
    second_score = scored[1][0] if len(scored) > 1 else 0

    is_exact_match = top_score == 100
    is_confident = is_exact_match or (
        top_score >= AUTO_MATCH_SCORE_THRESHOLD
        and (top_score - second_score) >= AUTO_MATCH_MARGIN
    )

    if is_confident:
        return IdentificationResult(
            query_title=query_title,
            confident=True,
            matched=ranked_candidates[0],
            candidates=ranked_candidates,
        )

    return IdentificationResult(
        query_title=query_title,
        confident=False,
        candidates=ranked_candidates,
        message=(
            "Could not confidently identify this title. "
            "Vise kandidata je slicno - potrebna je rucna potvrda."
        ),
    )


async def identify_title_any_type(query_title: str) -> IdentificationResult:
    """
    Za slucajeve kad ne znamo unapred da li je naslov serija ili film
    (npr. inicijalna WATCHED lista) - pokusa oba tipa i vrati bolji rezultat.
    """
    show_result = await identify_title(query_title, ContentTypeAPI.SHOW)
    if show_result.confident:
        return show_result

    movie_result = await identify_title(query_title, ContentTypeAPI.MOVIE)
    if movie_result.confident:
        return movie_result

    combined = show_result.candidates + movie_result.candidates
    combined.sort(key=lambda c: c.confidence or 0, reverse=True)
    return IdentificationResult(
        query_title=query_title,
        confident=False,
        candidates=combined[:6],
        message="Could not confidently identify this title.",
    )

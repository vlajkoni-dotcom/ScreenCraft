from pydantic import BaseModel

from app.schemas.common import ContentTypeAPI


class SearchCandidate(BaseModel):
    """
    Jedan kandidat vraćen iz TMDB/TVmaze pretrage - koristi se i za direktnu
    pretragu (SEARCH stranica) i za identifikaciju nepreciznih naziva
    (services/matching.py).
    """

    content_type: ContentTypeAPI
    tmdb_id: int | None = None
    tvmaze_id: int | None = None

    title: str
    original_title: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_path: str | None = None

    vote_average: float | None = None
    popularity: float | None = None

    # 0-100, koliko smo sigurni da je ovo tačan naslov (koristi matching.py)
    confidence: float | None = None

    already_in_library: bool = False
    current_status: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchCandidate]


class IdentificationResult(BaseModel):
    """
    Rezultat pokušaja da se nepouzdan naziv (npr. iz početne test liste)
    automatski identifikuje. Ako je 'confident' False, NIKAD ne bindujemo
    automatski - korisnik mora da potvrdi jednog od 'candidates'.
    """

    query_title: str
    confident: bool
    matched: SearchCandidate | None = None
    candidates: list[SearchCandidate] = []
    message: str | None = None

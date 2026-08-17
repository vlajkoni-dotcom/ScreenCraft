import pytest

from app.schemas.common import ContentTypeAPI
from app.services import matching


@pytest.mark.asyncio
async def test_confident_exact_match(monkeypatch):
    async def fake_search_tv(query, year=None):
        return [
            {"id": 1, "name": "Reacher", "original_name": "Reacher",
             "first_air_date": "2022-02-04", "overview": "...", "poster_path": None,
             "vote_average": 8.1, "popularity": 500},
            {"id": 2, "name": "Preacher", "original_name": "Preacher",
             "first_air_date": "2016-05-22", "overview": "...", "poster_path": None,
             "vote_average": 7.9, "popularity": 100},
        ]

    monkeypatch.setattr(matching.tmdb_client, "search_tv", fake_search_tv)

    result = await matching.identify_title("Reacher", ContentTypeAPI.SHOW)

    assert result.confident is True
    assert result.matched is not None
    assert result.matched.title == "Reacher"


@pytest.mark.asyncio
async def test_ambiguous_does_not_auto_match(monkeypatch):
    async def fake_search_tv(query, year=None):
        # Dva vrlo slična naslova - sistem NE SME da pogodi
        return [
            {"id": 1, "name": "The Killing", "original_name": "The Killing",
             "first_air_date": "2011-04-03", "overview": "...", "poster_path": None,
             "vote_average": 7.9, "popularity": 200},
            {"id": 2, "name": "Killing Eve", "original_name": "Killing Eve",
             "first_air_date": "2018-04-08", "overview": "...", "poster_path": None,
             "vote_average": 8.2, "popularity": 300},
        ]

    monkeypatch.setattr(matching.tmdb_client, "search_tv", fake_search_tv)

    result = await matching.identify_title("Killing", ContentTypeAPI.SHOW)

    assert result.confident is False
    assert result.matched is None
    assert len(result.candidates) == 2
    assert result.message is not None


@pytest.mark.asyncio
async def test_no_results_returns_not_confident_message(monkeypatch):
    async def fake_search_tv(query, year=None):
        return []

    monkeypatch.setattr(matching.tmdb_client, "search_tv", fake_search_tv)

    result = await matching.identify_title("Nepostojeci Naslov Xyzabc", ContentTypeAPI.SHOW)

    assert result.confident is False
    assert result.candidates == []
    assert "Could not confidently identify" in result.message

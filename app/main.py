from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import calendar as calendar_api
from app.api import content, discovery, library, search, settings as settings_api
from app.api import recommendations as recommendations_api
from app.database.db import init_db
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_db()
    yield


app = FastAPI(title="TV Show & Movie Tracker", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(search.router)
app.include_router(content.router)
app.include_router(library.router)
app.include_router(settings_api.router)
app.include_router(discovery.router)
app.include_router(calendar_api.router)
app.include_router(recommendations_api.router)


# ---------- Pages (server-rendered shell, data loaded via fetch in the browser) ----------

@app.get("/")
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "active": "dashboard"})


@app.get("/today")
async def today_page(request: Request):
    return templates.TemplateResponse("today.html", {"request": request, "active": "today"})


@app.get("/calendar")
async def calendar_page(request: Request):
    return templates.TemplateResponse("calendar.html", {"request": request, "active": "calendar"})


@app.get("/watching")
async def watching_page(request: Request):
    return templates.TemplateResponse("watching.html", {"request": request, "active": "watching"})


@app.get("/shows/{tmdb_id}")
async def show_detail_page(request: Request, tmdb_id: int):
    return templates.TemplateResponse(
        "show_detail.html", {"request": request, "active": "watching", "tmdb_id": tmdb_id}
    )


@app.get("/new-series")
async def new_series_page(request: Request):
    return templates.TemplateResponse("new_series.html", {"request": request, "active": "new-series"})


@app.get("/watchlist")
async def watchlist_page(request: Request):
    return templates.TemplateResponse(
        "library_list.html",
        {"request": request, "active": "watchlist", "page_title": "Watchlist", "status": "watchlist"},
    )


@app.get("/watched")
async def watched_page(request: Request):
    return templates.TemplateResponse(
        "library_list.html",
        {"request": request, "active": "watched", "page_title": "Watched", "status": "watched"},
    )


@app.get("/search-page")
async def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request, "active": "search"})


@app.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "active": "settings"})


@app.get("/health")
async def health():
    return {"status": "ok"}

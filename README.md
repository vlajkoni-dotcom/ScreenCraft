# 🎬 ScreenCraft — v1.0

Personal TV Show & Movie Tracker

A self-hosted, lightweight web app for tracking what you watch, discovering
new shows and movies, and knowing exactly when the next episode drops — with
a built-in recommendation engine and Serbia-focused streaming availability.

> ⚠️ **Note**: This app uses The Movie Database (TMDB) and TVmaze APIs.
> You'll need your own free TMDB API key to run it — see Installation below.

---

## ✨ Features

### Core Functionality
- ✅ Track TV shows and movies separately (or together) — `Watching`, `Watchlist`, `Watched`, `Dropped`, `Paused`, `Not Interested`
- ✅ Automatic episode & season sync from TVmaze (air dates, air times)
- ✅ Mark individual episodes — or a whole season at once — as watched
- ✅ Monthly calendar: your episodes, season finales, new seasons, new premieres
- ✅ Discovery: new TV shows and new movies (streaming/Blu-ray only, not old catalog), filterable by date range, genre, and platform
- ✅ "Vladimir Score" recommendation engine — similarity, genre match, rating, popularity, newness, and Serbia availability, all combined into one score
- ✅ Streaming availability lookup (Netflix, HBO Max, Prime Video, Disney+, and more), prioritized for Serbia 🇷🇸

### User Experience
- 🎨 Clean, dark, streaming-service-inspired interface
- 📅 Visual calendar with color-coded event types
- 🏷️ Fuzzy title matching for search — never guesses when a title is ambiguous
- 📊 Per-show progress tracking (X / Y episodes watched)

### Technical
- 🧵 Fully async backend (FastAPI + SQLAlchemy async + httpx)
- 🔄 Retry with exponential backoff on flaky API calls
- 🗃️ Local SQLite database — no external services required beyond TMDB/TVmaze
- 🔒 Your API key stays in your own `.env` file, never committed to the repo

---

## 📦 Installation

### Prerequisites
- Python 3.11+
- A free [TMDB](https://www.themoviedb.org/) account and API key

### Setup

**1. Clone the repository**
```bash
git clone https://github.com/vlajkoni-dotcom/ScreenCraft.git
cd ScreenCraft
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**3. Get your TMDB API key**
- Go to https://www.themoviedb.org/ → create a free account
- Settings → API → request an API key (choose "Developer", fill the short form)
- Approval is usually instant or within a few hours

**4. Configure your environment**
```bash
cp .env.example .env
```
Open `.env` and paste your TMDB key into `TMDB_API_KEY`.

**5. Run the app**
```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

---

## 🚀 Usage

### Adding shows/movies
1. Go to **Search**, type a title
2. Filter by **TV Shows** / **Movies** using the tabs
3. Click **Watching**, **Watchlist**, **Watched**, or **Not Interested** on any result

### Tracking episodes
1. Open a show from **Watching** or **Search**
2. Check off individual episodes, or use **"Mark whole season as watched"**
3. A green ✓ badge appears once a season is fully watched

### Discovering something new
- **New TV Shows & Movies** page: new seasons (yours and suggestions), fresh premieres, and genuinely-new movie releases — filterable by date window, genre, and platform
- **Dashboard → Recommended For You**: personalized picks scored 0–100 (Vladimir Score) based on your taste profile

### Calendar
- Color-coded dots per day: your episodes, season finales, new seasons, new series
- Click any day for full details

---

## 🗂️ Project Structure
ScreenCraft/
├── app/
│ ├── main.py # FastAPI entrypoint, page routes
│ ├── config.py # Settings (.env loader)
│ ├── database/
│ │ └── db.py # Async SQLAlchemy engine, table creation
│ ├── models/ # SQLAlchemy ORM models (shows, movies, episodes, user_content...)
│ ├── schemas/ # Pydantic request/response models
│ ├── services/
│ │ ├── tmdb.py # TMDB API client
│ │ ├── tvmaze.py # TVmaze API client
│ │ ├── matching.py # Fuzzy title identification (never guesses)
│ │ ├── library.py # Show/movie creation, episode sync
│ │ ├── dashboard.py # Watching progress, Today, Next Episodes
│ │ ├── discovery.py # New TV shows / movies / seasons discovery
│ │ ├── calendar.py # Monthly calendar event aggregation
│ │ └── recommendations.py # Vladimir Score recommendation engine
│ ├── api/ # FastAPI routers (one per feature area)
│ ├── templates/ # Jinja2 HTML templates
│ └── static/ # CSS + vanilla JS
├── tests/ # pytest test suite
├── requirements.txt
├── .env.example # Copy to .env and add your own TMDB key
└── .gitignore # Excludes .env and local database

---

## 🧠 How It Works

### Architecture
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite
- **Frontend**: Jinja2 templates + vanilla JavaScript (no framework, no build step)
- **Data sources**: TMDB (metadata, genres, recommendations, streaming availability) + TVmaze (episode air dates/times — primary schedule source)

### Data integrity rules
- Never invents dates, episodes, ratings, or streaming availability
- When a title can't be confidently identified, shows candidates instead of guessing
- TVmaze is the source of truth for air dates/times; TMDB is the source of truth for metadata
- New-movie discovery checks each film's *actual* digital/Blu-ray release date (not just an announced future date) before showing it

---

## 🛠️ Troubleshooting

**App won't start**
- Confirm Python 3.11+ is installed: `python --version`
- Confirm all dependencies installed: `pip install -r requirements.txt`

**"TMDB API key not configured" warning in the terminal**
- Make sure you copied `.env.example` to `.env` (not just edited the example)
- Confirm `TMDB_API_KEY=` has your actual key, no extra spaces/quotes

**Episodes missing for a show**
- Open the show page and click **"Refresh episodes"** — this manually retries the TVmaze sync

**Discovery/Recommended sections show a network error**
- Usually means the TMDB key is missing, invalid, or TMDB is temporarily down — check the terminal for the exact error

---

## 🔮 Roadmap Ideas

- Notification center (new episode today/tomorrow, new season on watchlist)
- Export/backup your library (JSON download)
- Debounced live search
- Multi-user hosting (PostgreSQL + auth + per-user API keys) — see notes below

### Turning this into a multi-user hosted app

The current setup (SQLite, no login) is intentionally simple for single-user
local use. Making it a real hosted multi-user app (e.g. on Vercel) would need:
1. PostgreSQL instead of SQLite (Neon/Supabase free tier)
2. An auth layer (email/password or magic link) + `user_id` on user-specific tables
3. Encrypted per-user TMDB API key storage
4. A Cron job for background sync instead of an always-on process

This is a meaningful rework, not a small tweak — worth doing only if there's real demand beyond personal/friends use.

---

## 📄 License

MIT License — Copyright © 2026 Vladimir Jevtić

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal in the
software without restriction, subject to standard MIT terms.

## ⚠️ Disclaimer

This is a personal tracking tool. It does not stream, download, or host any
copyrighted video/audio content — it only reads public metadata (titles,
schedules, streaming availability) from TMDB and TVmaze.

## 🙏 Credits

- [TMDB](https://www.themoviedb.org/) — metadata, genres, recommendations, streaming availability (data licensed from JustWatch)
- [TVmaze](https://www.tvmaze.com/) — episode air dates and schedules
- [FastAPI](https://fastapi.tiangolo.com/) — backend framework

---

Created by **Vladimir Jevtić** © 2026
Version: 1.0.0

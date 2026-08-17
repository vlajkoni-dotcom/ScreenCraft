# TV Show & Movie Tracker

Personalni tracker za TV serije i filmove: šta gledaš, šta ti je na listi,
kad izlazi sledeća epizoda, otkrivanje novih naslova, i gde je sve dostupno
u Srbiji.

Sekcije: Dashboard, Today, Calendar, Watching, New TV Shows & Movies,
Watchlist, Watched, Search, Settings.

## Pokretanje (za sebe, lokalno)

```bash
git clone <url-tvog-repo-a>
cd series-tracker
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Otvori `.env` i upiši svoj TMDB API ključ (besplatan, vidi ispod).

```bash
uvicorn app.main:app --reload
```

Otvori `http://127.0.0.1:8000`.

## Kako drugi ljudi mogu da koriste ovo (GitHub setup)

Aplikacija je napravljena tako da svako ko je pokrene koristi **svoj**
TMDB API ključ i **svoju** lokalnu bazu - nema deljenja podataka između
korisnika, svako ima potpuno odvojenu instalaciju. To znači:

1. **Ništa osetljivo nije u repo-u.** `.env` fajl (gde ide tvoj pravi ključ)
   je u `.gitignore` - nikad se ne commit-uje. `.env.example` sadrži samo
   placeholder tekst, bezbedan je za GitHub.
2. **Baza podataka takođe nije u repo-u.** Folder `data/` (SQLite fajl) je
   u `.gitignore` - svaki korisnik dobija svoju praznu bazu pri prvom
   pokretanju (kreira se sama, vidi `app/database/db.py::init_db`).

### Koraci da neko drugi ovo pokrene sa GitHub-a

1. Idi na https://www.themoviedb.org/, napravi nalog (besplatno)
2. Settings → API → zatraži API ključ (bira se "Developer", popuni kratak
   formular - odobrava se odmah ili za par sati)
3. Isprati "Pokretanje" korake iznad, sa svojim ključem u `.env`

### Ako želiš da to bude "objavi na GitHub" umesto samo "meni na disku"

```bash
cd series-tracker
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <url-tvog-praznog-repo-a-na-githubu>
git push -u origin main
```

Pre ovoga, samo proveri da `.env` NIJE u listi fajlova koje `git add .`
hvata (proveri sa `git status` - ne sme se pojaviti `.env`, samo
`.env.example`). `.gitignore` je već podešen da ga automatski isključi.

Svako ko klonira repo posle ovoga prati "Kako drugi ljudi..." korake iznad
i ima potpuno istu aplikaciju, sa svojim ključem i svojom bazom.

## Šta trenutno radi

- **Dashboard** - Next Episodes, Today preview, New TV Shows preview, Recommended For You (Vladimir Score)
- **Today** - Danas/Sutra/Prekosutra tabela za serije koje pratiš
- **Calendar** - mesečni kalendar: tvoje epizode, finala sezona (svih serija u bazi), nove sezone, nove serije
- **Watching** - progres po seriji, klik vodi na punu listu sezona/epizoda sa čekiranjem (pojedinačno ili cela sezona odjednom)
- **New TV Shows & Movies** - nove sezone (tvoje i preporuke), discovery novih serija i filmova sa filterima (period, žanr, platforma)
- **Watchlist / Watched** - liste po statusu
- **Search** - TMDB pretraga (serije + filmovi), tabovi za filtriranje, dugmad za status
- **Settings** - region, timezone, status TMDB ključa

Statusi: `watching → watched`, `watching → dropped/paused`, bilo koje →
`watchlist`, i poseban `not_interested` (eksplicitno odbijena preporuka).

## Arhitektura (kratko)

- **Backend**: FastAPI + SQLAlchemy (async) + SQLite
- **Frontend**: Jinja2 šabloni + vanilla JS (fetch pozivi ka `/api/...`), bez frontend frameworka
- **TMDB** - metadata, žanrovi, preporuke, streaming dostupnost (`/watch/providers`, licencirano od JustWatch-a)
- **TVmaze** - schedule (air_date/air_time) za serije - primarni izvor za raspored, TMDB primaran za metadata
- Svi servisi su u `app/services/` - odvojeni od API sloja (`app/api/`), što olakšava buduće promene (npr. multi-user, drugi provajder podataka)

## Ako ikad poželiš da ovo bude prava multi-user web aplikacija

Trenutna arhitektura (SQLite, bez logina) je namerno jednostavna za jednog
korisnika. Za pravi multi-user hosting (npr. Vercel) trebalo bi:

1. PostgreSQL umesto SQLite (Neon/Supabase - besplatan tier)
2. Auth sloj (email/password ili magic link) + `user_id` na `user_content`/`watched_episodes`
3. Enkriptovan TMDB ključ po korisniku u Settings
4. Vercel Cron Job umesto internog schedulera za pozadinski sync

Ovo je veća izmena, ne mala nadogradnja - javi ako to postane prioritet.

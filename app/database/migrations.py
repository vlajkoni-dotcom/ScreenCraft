"""
V1 koristi Base.metadata.create_all() u db.init_db() umesto pravih migracija
(vidi app/database/db.py) - dovoljno je za jednog korisnika i SQLite.

Kada pređemo na PostgreSQL ili nam bude potrebno menjanje šeme bez gubitka
podataka, ovde uvodimo Alembic:

    pip install alembic
    alembic init app/database/alembic
    alembic revision --autogenerate -m "opis izmene"
    alembic upgrade head

Ovaj fajl je namerno ostavljen kao mesto gde će živeti Alembic env.py
konfiguracija i helper funkcije, da ne bismo morali da reorganizujemo
strukturu projekta kada dođe taj trenutak.
"""

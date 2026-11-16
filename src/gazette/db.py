"""Acces PostgreSQL : creation idempotente du schema (sources, articles_bruts)."""

import os

import psycopg

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    slug               TEXT PRIMARY KEY,
    nom                TEXT NOT NULL,
    type               TEXT NOT NULL,
    url                TEXT NOT NULL,
    actif              BOOLEAN NOT NULL DEFAULT TRUE,
    statut             TEXT NOT NULL DEFAULT 'inconnu'
                       CHECK (statut IN ('ok', 'degrade', 'panne', 'inconnu')),
    derniere_collecte  TIMESTAMPTZ,
    dernier_succes     TIMESTAMPTZ,
    code_http          INTEGER,
    nb_articles        INTEGER,
    erreur             TEXT,
    echecs_consecutifs INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS articles_bruts (
    id               BIGSERIAL PRIMARY KEY,
    source_slug      TEXT NOT NULL REFERENCES sources (slug),
    titre            TEXT NOT NULL,
    extrait          TEXT NOT NULL DEFAULT '',
    lien             TEXT NOT NULL,
    date_publication TIMESTAMPTZ,
    collecte_le      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_slug, lien)
);

CREATE INDEX IF NOT EXISTS idx_articles_bruts_date
    ON articles_bruts (date_publication);
"""


def connexion(url: str | None = None) -> psycopg.Connection:
    """Ouvre une connexion (DATABASE_URL, jamais de mot de passe en dur)."""
    return psycopg.connect(url or os.environ["DATABASE_URL"], connect_timeout=5)


def initialiser_schema(conn: psycopg.Connection) -> None:
    """Cree les tables si elles n'existent pas (peut etre relance sans risque)."""
    conn.execute(SCHEMA)
    conn.commit()


if __name__ == "__main__":
    with connexion() as conn:
        initialiser_schema(conn)
    print("schema ok")
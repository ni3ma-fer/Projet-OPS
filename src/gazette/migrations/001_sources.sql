-- 001 : catalogue et etat de chaque source (table `sources`).
-- Le brut reste en fichiers JSON Lines ; cette table dit l'etat de chaque source.
CREATE TABLE sources (
    slug               TEXT PRIMARY KEY,
    nom                TEXT NOT NULL UNIQUE,
    type               TEXT NOT NULL CHECK (type IN ('PQN', 'PQR')),
    url_flux           TEXT NOT NULL,
    actif              BOOLEAN NOT NULL DEFAULT TRUE,
    statut             TEXT NOT NULL DEFAULT 'inconnu'
                       CHECK (statut IN ('inconnu', 'ok', 'degrade', 'panne', 'sommeil')),
    derniere_tentative TIMESTAMPTZ,
    derniere_reussite  TIMESTAMPTZ,
    echecs_consecutifs INTEGER NOT NULL DEFAULT 0 CHECK (echecs_consecutifs >= 0),
    code_http          INTEGER,
    erreur             TEXT,
    etag               TEXT,
    last_modified      TEXT
);

COMMENT ON TABLE sources IS 'Catalogue des sources et etat de la derniere collecte';
COMMENT ON COLUMN sources.statut IS 'ok | degrade | panne | sommeil (3 echecs de suite) | inconnu';
COMMENT ON COLUMN sources.etag IS 'En-tete ETag de la derniere reponse, renvoye en If-None-Match';
COMMENT ON COLUMN sources.last_modified IS 'En-tete Last-Modified, renvoye en If-Modified-Since';

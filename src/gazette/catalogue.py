"""Catalogue des sources : synchronise sources.csv vers la table `sources`.

    python -m gazette.catalogue
"""

from __future__ import annotations

from gazette.db import connexion
from gazette.sources import lire_sources

# Met a jour l'identite de la source, jamais son etat (statut, echecs, etag...).
UPSERT = """
INSERT INTO sources (slug, nom, type, url_flux, actif)
VALUES (%(slug)s, %(nom)s, %(type)s, %(url_flux)s, %(actif)s)
ON CONFLICT (slug) DO UPDATE
SET nom = EXCLUDED.nom,
    type = EXCLUDED.type,
    url_flux = EXCLUDED.url_flux,
    actif = EXCLUDED.actif
"""


def vers_ligne(source: dict) -> dict:
    """Ligne du CSV -> colonnes de la table `sources`."""
    return {
        "slug": source["slug"],
        "nom": source["nom"],
        "type": source["type"],
        "url_flux": source["url"],
        "actif": source["actif"] == "oui",
    }


def synchroniser(conn, sources: list[dict]) -> int:
    """Insere ou met a jour chaque source. Renvoie leur nombre."""
    lignes = [vers_ligne(s) for s in sources]
    with conn.cursor() as cur:
        cur.executemany(UPSERT, lignes)
    conn.commit()
    return len(lignes)


def main() -> None:
    sources = lire_sources(seulement_actives=False)
    with connexion() as conn:
        nombre = synchroniser(conn, sources)
    print(f"{nombre} sources synchronisees")


if __name__ == "__main__":
    main()
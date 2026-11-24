"""Catalogue des sources dans PostgreSQL : synchro depuis sources.csv, lecture, etat.

    python -m gazette.catalogue      # synchronise sources.csv -> table `sources`
"""

from __future__ import annotations

from datetime import datetime

from gazette.db import connexion
from gazette.sources import Resultat, lire_sources

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

# Etat apres un passage. Les validateurs (etag, last_modified) sont remplaces apres un 200,
# conserves apres un 304 sans en-tete, et jamais touches apres une erreur.
MAJ_PASSAGE = """
UPDATE sources SET
    statut = %(statut)s::text,
    derniere_tentative = %(maintenant)s,
    derniere_reussite = CASE WHEN %(reussite)s THEN %(maintenant)s ELSE derniere_reussite END,
    echecs_consecutifs = CASE WHEN %(statut)s::text = 'panne'
                              THEN echecs_consecutifs + 1 ELSE 0 END,
    code_http = %(code_http)s,
    erreur = %(erreur)s,
    etag = CASE WHEN %(remplacer)s THEN %(etag)s::text
                ELSE COALESCE(%(etag)s::text, etag) END,
    last_modified = CASE WHEN %(remplacer)s THEN %(last_modified)s::text
                         ELSE COALESCE(%(last_modified)s::text, last_modified) END
WHERE slug = %(slug)s
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


def charger_sources(conn) -> list[dict]:
    """Sources actives, avec les validateurs memorises. Meme forme que lire_sources()."""
    lignes = conn.execute(
        "SELECT slug, nom, url_flux, etag, last_modified FROM sources WHERE actif ORDER BY slug"
    ).fetchall()
    return [
        {"slug": slug, "nom": nom, "url": url, "etag": etag, "last_modified": modifie}
        for slug, nom, url, etag, modifie in lignes
    ]


def parametres_passage(
    resultat: Resultat, statut: str, erreur: str | None, maintenant: datetime
) -> dict:
    """Parametres de MAJ_PASSAGE (fonction pure, testable sans base)."""
    succes = resultat.code_http in (200, 304) and not resultat.erreur
    return {
        "slug": resultat.slug,
        "statut": statut,
        "maintenant": maintenant,
        "reussite": statut == "ok",
        "code_http": resultat.code_http,
        "erreur": erreur,
        "remplacer": succes and resultat.code_http == 200,
        "etag": resultat.etag if succes else None,
        "last_modified": resultat.last_modified if succes else None,
    }


def enregistrer_passage(
    conn, resultat: Resultat, statut: str, erreur: str | None, maintenant: datetime
) -> None:
    """Ecrit l'etat de la source dans la table apres une collecte."""
    conn.execute(MAJ_PASSAGE, parametres_passage(resultat, statut, erreur, maintenant))


def main() -> None:
    sources = lire_sources(seulement_actives=False)
    with connexion() as conn:
        nombre = synchroniser(conn, sources)
    print(f"{nombre} sources synchronisees")


if __name__ == "__main__":
    main()
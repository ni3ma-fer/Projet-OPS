"""Journaux structures : une ligne JSON par source et par passage, puis un resume."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

from gazette.sources import Resultat


def ligne_source(resultat: Resultat, bilan: dict) -> dict:
    """Une ligne de journal pour une source : recus, ecrits, ignores, duree."""
    recus, ecrits = bilan["lus"], bilan["nouveaux"]
    return {
        "evenement": "source_collectee",
        "source": resultat.slug,
        "statut": bilan["statut"],
        "code_http": resultat.code_http,
        "tentatives": resultat.tentatives,
        "recus": recus,
        "ecrits": ecrits,
        "ignores": recus - ecrits,
        "duree_s": resultat.duree_s,
        "erreur": bilan["erreur"],
    }


def resume_passage(bilans: list[dict]) -> dict:
    """Compteurs d'un passage complet."""
    recus = sum(b["lus"] for b in bilans)
    ecrits = sum(b["nouveaux"] for b in bilans)
    return {
        "evenement": "passage_termine",
        "sources": len(bilans),
        "par_statut": dict(Counter(b["statut"] for b in bilans)),
        "recus": recus,
        "ecrits": ecrits,
        "ignores": recus - ecrits,
    }


def journaliser(ligne: dict) -> None:
    """Ecrit la ligne en JSON, horodatee, sur la sortie standard (lue par Airflow et Docker)."""
    horodatage = datetime.now(timezone.utc).isoformat()
    print(json.dumps({"horodatage": horodatage, **ligne}), flush=True)
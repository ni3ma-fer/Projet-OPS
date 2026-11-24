"""DAG toutes les 30 min : une tache de collecte par source (dynamic task mapping).

L'etat de chaque source (statut, echecs, ETag...) vit dans la table `sources`.
Chaque tache ecrit une ligne de journal JSON ; `finaliser` ecrit le resume du passage.
"""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG, task

from gazette.catalogue import charger_sources, enregistrer_passage, synchroniser
from gazette.db import connexion
from gazette.journal import journaliser, ligne_source, resume_passage
from gazette.migrations import appliquer
from gazette.sources import collecter_source, lire_sources
from gazette.stockage import (
    dossier_etat,
    ecrire_rapport,
    purger_anciens,
    racine_brut,
    traiter_resultat,
)

with DAG(
    dag_id="collecte_sources",
    schedule="*/30 * * * *",
    start_date=datetime(2026, 11, 16),
    catchup=False,
    max_active_runs=1,
    tags=["gazette"],
):

    @task
    def lister_sources() -> list[dict]:
        """Migrations, synchro de sources.csv, puis sources a collecter avec leur ETag."""
        with connexion(autocommit=True) as conn:
            appliquer(conn)
            synchroniser(conn, lire_sources(seulement_actives=False))
            return charger_sources(conn)

    @task
    def collecter(source: dict) -> dict:
        # Une source en panne n'echoue pas la tache : son etat est enregistre.
        resultat = collecter_source(source)
        maintenant = datetime.now(timezone.utc)
        bilan = traiter_resultat(resultat, racine_brut(), dossier_etat(), maintenant)
        with connexion(autocommit=True) as conn:
            enregistrer_passage(conn, resultat, bilan["statut"], bilan["erreur"], maintenant)
        journaliser(ligne_source(resultat, bilan))
        return bilan

    @task
    def finaliser(bilans) -> None:
        bilans = list(bilans)  # les valeurs d'une tache mappee arrivent en proxy paresseux
        ecrire_rapport(dossier_etat(), lire_sources(seulement_actives=False))
        purges = purger_anciens(racine_brut(), datetime.now(timezone.utc))
        journaliser({**resume_passage(bilans), "dossiers_purges": purges})

    finaliser(collecter.expand(source=lister_sources()))
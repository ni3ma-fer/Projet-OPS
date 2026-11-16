"""DAG horaire : une tache de collecte par source (dynamic task mapping)."""

from __future__ import annotations

from datetime import datetime, timezone

from airflow.sdk import DAG, task

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
    schedule="@hourly",
    start_date=datetime(2026, 11, 16),
    catchup=False,
    max_active_runs=1,
    tags=["gazette"],
):

    @task
    def lister_sources() -> list[dict]:
        return [{k: s[k] for k in ("slug", "nom", "url")} for s in lire_sources()]

    @task
    def collecter(source: dict) -> dict:
        # Une source en panne n'echoue pas la tache : son etat est enregistre.
        resultat = collecter_source(source)
        bilan = traiter_resultat(resultat, racine_brut(), dossier_etat())
        print(bilan)
        return bilan

    @task
    def finaliser(bilans) -> None:
        bilans = list(bilans)  # les valeurs d'une tache mappee arrivent en proxy paresseux
        ecrire_rapport(dossier_etat(), lire_sources(seulement_actives=False))
        purges = purger_anciens(racine_brut(), datetime.now(timezone.utc))
        print(f"{len(bilans)} sources traitees, {purges} dossier(s) purge(s)")

    finaliser(collecter.expand(source=lister_sources()))
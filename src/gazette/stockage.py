"""Stockage en fichiers : articles bruts en JSON Lines (moins de 24 h, sans doublons)
et etat de chaque source en JSON, avec un rapport CSV."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gazette.sources import Resultat, collecter_source, lire_sources

COLONNES_ETAT = [
    "slug", "nom", "actif", "statut", "code_http", "nb_articles",
    "derniere_collecte", "dernier_succes", "echecs_consecutifs", "erreur",
]


def racine_brut() -> Path:
    """Dossier du brut : <RAW_DATA_DIR>/articles_bruts (data/raw par defaut)."""
    return Path(os.getenv("RAW_DATA_DIR", "data/raw")) / "articles_bruts"


def dossier_etat() -> Path:
    """Dossier de l'etat des sources (STATE_DIR, data/etat par defaut)."""
    return Path(os.getenv("STATE_DIR", "data/etat"))


# ---- Brut ----
def filtrer_recents(items: list[dict], maintenant: datetime, heures: int = 24) -> list[dict]:
    """Garde les articles de moins de `heures` h. Sans date : ecarte."""
    limite = maintenant - timedelta(hours=heures)
    return [
        item
        for item in items
        if item.get("publie_le")
        and datetime.fromisoformat(item["publie_le"]) >= limite
    ]


def identifiant(slug: str, lien: str) -> str:
    """Identifiant stable : le meme article d'une source donne toujours le meme id."""
    return hashlib.sha256(f"{slug}\n{lien}".encode()).hexdigest()[:16]


def construire_ligne(item: dict, slug: str, maintenant: datetime) -> dict:
    """Ligne du brut, dans l'ordre des champs de l'enonce."""
    return {
        "id": identifiant(slug, item["lien"]),
        "source": item["source"],
        "lien": item["lien"],
        "titre": item["titre"],
        "resume": item["resume"],
        "publie_le": item["publie_le"],
        "recupere_le": maintenant.isoformat(),
        "rubrique": item["rubrique"],
        "payload": item["payload"],
    }


def liens_connus(racine: Path, slug: str) -> set[str]:
    """Liens deja stockes pour cette source (tous les jours encore presents)."""
    liens: set[str] = set()
    for fichier in racine.glob(f"dt=*/{slug}.jsonl"):
        with fichier.open(encoding="utf-8") as f:
            liens.update(json.loads(ligne)["lien"] for ligne in f if ligne.strip())
    return liens


def enregistrer_articles(racine: Path, slug: str, items: list[dict], maintenant: datetime) -> int:
    """Ajoute les nouveaux articles au fichier du jour. Renvoie leur nombre."""
    connus = liens_connus(racine, slug)
    nouveaux = []
    for item in items:
        if item["lien"] in connus:
            continue
        connus.add(item["lien"])
        nouveaux.append(construire_ligne(item, slug, maintenant))
    if nouveaux:
        fichier = racine / f"dt={maintenant:%Y-%m-%d}" / f"{slug}.jsonl"
        fichier.parent.mkdir(parents=True, exist_ok=True)
        with fichier.open("a", encoding="utf-8") as f:
            for ligne in nouveaux:
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    return len(nouveaux)


def purger_anciens(racine: Path, maintenant: datetime, heures: int = 48) -> int:
    """Supprime les dossiers dt=... commences il y a plus de `heures` h (purge 48 h)."""
    limite = maintenant - timedelta(hours=heures)
    supprimes = 0
    for dossier in racine.glob("dt=*"):
        debut = datetime.strptime(dossier.name[3:], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if debut < limite:
            shutil.rmtree(dossier)
            supprimes += 1
    return supprimes


# ---- Etat des sources ----
def lire_etat(dossier: Path, slug: str) -> dict:
    fichier = dossier / f"{slug}.json"
    if not fichier.exists():
        return {}
    return json.loads(fichier.read_text(encoding="utf-8"))


def mettre_a_jour_etat(
    dossier: Path,
    slug: str,
    statut: str,
    code_http: int | None,
    nb_articles: int,
    erreur: str | None,
    maintenant: datetime,
) -> dict:
    precedent = lire_etat(dossier, slug)
    echecs = (precedent.get("echecs_consecutifs", 0) + 1) if statut == "panne" else 0
    etat = {
        "slug": slug,
        "statut": statut,
        "code_http": code_http,
        "nb_articles": nb_articles,
        "erreur": erreur,
        "derniere_collecte": maintenant.isoformat(),
        "dernier_succes": (
            maintenant.isoformat() if statut == "ok" else precedent.get("dernier_succes")
        ),
        "echecs_consecutifs": echecs,
    }
    dossier.mkdir(parents=True, exist_ok=True)
    temporaire = dossier / f"{slug}.json.tmp"
    temporaire.write_text(json.dumps(etat, ensure_ascii=False, indent=2), encoding="utf-8")
    temporaire.replace(dossier / f"{slug}.json")  # ecriture atomique
    return etat


def ecrire_rapport(dossier: Path, sources: list[dict], chemin: Path | None = None) -> Path:
    """Assemble l'etat de chaque source dans un CSV : la table des sources."""
    chemin = chemin or dossier / "etat_sources.csv"
    dossier.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=COLONNES_ETAT)
        ecrivain.writeheader()
        for s in sources:
            etat = lire_etat(dossier, s["slug"])
            ligne = {col: etat.get(col, "") for col in COLONNES_ETAT}
            ligne.update(
                slug=s["slug"],
                nom=s["nom"],
                actif=s["actif"],
                statut=etat.get("statut", "inconnu"),
                erreur=etat.get("erreur") or "",
            )
            ecrivain.writerow(ligne)
    return chemin


# ---- Une source de bout en bout ----
def traiter_resultat(
    resultat: Resultat,
    racine: Path,
    dossier: Path,
    maintenant: datetime | None = None,
) -> dict:
    """Filtre, stocke dans le brut et met a jour l'etat de la source. Renvoie un bilan."""
    maintenant = maintenant or datetime.now(timezone.utc)
    recents = filtrer_recents(resultat.items, maintenant)
    statut, erreur = resultat.statut, resultat.erreur
    if statut == "ok" and not recents and not resultat.non_modifie:
        statut, erreur = "degrade", "aucun article de moins de 24 h"
    nouveaux = enregistrer_articles(racine, resultat.slug, recents, maintenant)
    mettre_a_jour_etat(
        dossier, resultat.slug, statut, resultat.code_http, len(resultat.items), erreur, maintenant
    )
    return {
        "slug": resultat.slug,
        "statut": statut,
        "lus": len(resultat.items),
        "recents": len(recents),
        "nouveaux": nouveaux,
        "erreur": erreur,
    }


def main() -> None:
    sources = lire_sources(seulement_actives=False)
    racine, dossier = racine_brut(), dossier_etat()
    for source in sources:
        if source["actif"] != "oui":
            continue
        b = traiter_resultat(collecter_source(source), racine, dossier)
        print(
            f"{b['slug']:32} {b['statut']:8} lus={b['lus']:>3} "
            f"recents={b['recents']:>3} nouveaux={b['nouveaux']:>3}"
        )
    print(f"rapport : {ecrire_rapport(dossier, sources)}")
    print(f"{purger_anciens(racine, datetime.now(timezone.utc))} dossier(s) purge(s)")


if __name__ == "__main__":
    main()
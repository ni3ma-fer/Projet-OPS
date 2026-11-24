"""Lecture de sources.csv et collecte d'une source avec rapport d'etat."""

from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from gazette.collect import fetch_conditionnel, parse


def evaluer_statut(code_http: int | None, nb_articles: int, erreur: str | None) -> str:
    """panne = rien de lisible ; degrade = flux joignable mais vide ; ok sinon.

    304 (rien de neuf depuis la derniere collecte) est un succes.
    """
    if erreur or code_http not in (200, 304):
        return "panne"
    if code_http == 200 and nb_articles == 0:
        return "degrade"
    return "ok"


@dataclass
class Resultat:
    slug: str
    code_http: int | None = None
    items: list[dict] = field(default_factory=list)
    erreur: str | None = None
    duree_s: float = 0.0
    etag: str | None = None
    last_modified: str | None = None

    @property
    def non_modifie(self) -> bool:
        return self.code_http == 304

    @property
    def statut(self) -> str:
        return evaluer_statut(self.code_http, len(self.items), self.erreur)


def collecter_source(source: dict, timeout: float = 15.0) -> Resultat:
    """Collecte une source. Ne leve jamais d'exception : l'echec est dans le resultat.

    Si `source` contient `etag` / `last_modified` (memorises a la collecte precedente),
    ils sont renvoyes au serveur pour eviter de retelecharger un flux inchange.
    """
    resultat = Resultat(slug=source["slug"])
    debut = time.monotonic()
    try:
        reponse = fetch_conditionnel(
            source["url"], timeout, source.get("etag"), source.get("last_modified")
        )
        resultat.code_http = reponse.code
        resultat.etag = reponse.etag
        resultat.last_modified = reponse.last_modified
        if reponse.code == 200:
            resultat.items = parse(reponse.contenu, source["nom"])
        elif reponse.code != 304:
            resultat.erreur = f"HTTP {reponse.code}"
    except Exception as exc:  # noqa: BLE001
        resultat.erreur = f"{type(exc).__name__}: {exc}"
    resultat.duree_s = round(time.monotonic() - debut, 2)
    return resultat


def lire_sources(chemin: Path | None = None, seulement_actives: bool = True) -> list[dict]:
    chemin = chemin or Path(os.getenv("SOURCES_CSV", "sources.csv"))
    with chemin.open(encoding="utf-8", newline="") as f:
        sources = list(csv.DictReader(f))
    if seulement_actives:
        sources = [s for s in sources if s["actif"] == "oui"]
    return sources


def main() -> None:
    sources = lire_sources()
    print(f"{len(sources)} sources actives")
    for source in sources:
        r = collecter_source(source)
        print(
            f"{r.slug:32} {r.code_http or '-':>4} {len(r.items):>4} art. "
            f"{r.statut:8} {r.duree_s:>5}s  {r.erreur or ''}"
        )


if __name__ == "__main__":
    main()